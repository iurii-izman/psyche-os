"""Adapters — concrete implementations of application ports.

Each adapter wraps an infrastructure concern:
- OS key store (Windows DPAPI)
- Filesystem (safe path containment with sibling rejection)
- Clock (deterministic UTC)
- Secrets (TTY-based, never from argv/env/logs)
"""

from __future__ import annotations

import datetime
import os
from pathlib import Path
import sys
from typing import Any

FILESYSTEM_MUTATION_DEFERRED = True

from psyche_os.crypto.envelope import (
    OSKeyWrapError,
    OSKeyWrapper,
    SensitiveBytes,
    TTYSecretSource,
)
from psyche_os.domain.ids import VaultId

# ---------------------------------------------------------------------------
# OS key store adapter
# ---------------------------------------------------------------------------


class OSKeyStoreAdapter:
    """Adapter for OS-level key protection (Windows DPAPI)."""

    def __init__(self) -> None:
        self._wrapper = OSKeyWrapper()

    @property
    def available(self) -> bool:
        return self._wrapper.available

    def protect_vmk(self, vmk: SensitiveBytes, vault_id: VaultId) -> bytes:
        """Wrap VMK for OS-protected storage."""
        description = f"PSYCHE OS vault master key: {vault_id}"
        return self._wrapper.protect(vmk.raw, description)

    def unprotect_vmk(self, wrapped: bytes) -> SensitiveBytes:
        """Unwrap VMK from OS-protected storage."""
        key_bytes = self._wrapper.unprotect(wrapped)
        return SensitiveBytes(key_bytes)

    def rewrap_vmk(
        self,
        vmk: SensitiveBytes,
        old_wrapped: bytes,
        vault_id: VaultId,
    ) -> bytes:
        """Unwrap old, then re-wrap under current user."""
        unwrapped = self.unprotect_vmk(old_wrapped)
        if unwrapped.raw != vmk.raw:
            raise OSKeyWrapError("VMK mismatch during rewrap")
        return self.protect_vmk(vmk, vault_id)


# ---------------------------------------------------------------------------
# F09: Windows handle-bound Win32 primitives
# ---------------------------------------------------------------------------

_WIN32_REPARSE_TAG_MOUNT_POINT = 0xA0000003
_WIN32_REPARSE_TAG_SYMLINK = 0xA000000C
_WIN32_FILE_ATTRIBUTE_REPARSE_POINT = 0x400
_WIN32_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
_WIN32_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000

_WIN32_GENERIC_READ = 0x80000000
_WIN32_FILE_SHARE_READ = 0x00000001
_WIN32_OPEN_EXISTING = 3


def _win32_is_reparse_point(path: str) -> bool:
    """Return True if the path has the reparse-point attribute set.

    Uses GetFileAttributesW to check FILE_ATTRIBUTE_REPARSE_POINT.
    """
    import ctypes

    try:
        attrs = ctypes.windll.kernel32.GetFileAttributesW(path)
    except Exception:
        return False
    if attrs == 0xFFFFFFFF:
        return False
    return bool(attrs & _WIN32_FILE_ATTRIBUTE_REPARSE_POINT)


def _win32_check_reparse_tag(path: str) -> None:
    """Raise FilesystemError if path is a junction or symlink reparse point.

    Opens the path with FILE_FLAG_OPEN_REPARSE_POINT to inspect the tag
    without following the reparse point.
    """
    import ctypes
    from ctypes import wintypes

    handle = ctypes.windll.kernel32.CreateFileW(
        path,
        _WIN32_GENERIC_READ,
        _WIN32_FILE_SHARE_READ,
        None,
        _WIN32_OPEN_EXISTING,
        _WIN32_FILE_FLAG_OPEN_REPARSE_POINT | _WIN32_FILE_FLAG_BACKUP_SEMANTICS,
        None,
    )
    if handle == -1 or handle is None:
        # Can't open — the caller will get the error from the subsequent I/O
        return

    try:
        # DeviceIoControl FSCTL_GET_REPARSE_POINT to read the tag
        FSCTL_GET_REPARSE_POINT = 0x000900A8
        # Minimal buffer for REPARSE_DATA_BUFFER header (8 bytes)
        buf = ctypes.create_string_buffer(16384)
        bytes_returned = wintypes.DWORD(0)
        result = ctypes.windll.kernel32.DeviceIoControl(
            handle,
            FSCTL_GET_REPARSE_POINT,
            None,
            0,
            buf,
            ctypes.sizeof(buf),
            ctypes.byref(bytes_returned),
            None,
        )
        if not result:
            # Not a reparse point or access denied — fall through
            return

        # ReparseTag is at offset 0 in REPARSE_DATA_BUFFER
        tag = ctypes.c_uint32.from_buffer(buf, 0).value

        if tag in (_WIN32_REPARSE_TAG_MOUNT_POINT, _WIN32_REPARSE_TAG_SYMLINK):
            from psyche_os.adapters.adapters import FilesystemError

            tag_name = "junction" if tag == _WIN32_REPARSE_TAG_MOUNT_POINT else "symlink"
            raise FilesystemError(f"Reparse point ({tag_name}) not permitted in vault path: {path}")
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def _win32_open_no_reparse(path: str, flags: int, mode: int = 0o666) -> int:
    """Open a Windows path without following reparse points (junctions/symlinks).

    Uses CreateFileW with FILE_FLAG_OPEN_REPARSE_POINT.  The returned handle
    is a raw Windows HANDLE; it is converted to a C runtime fd via _open_osfhandle.
    """
    import ctypes
    import msvcrt

    desired_access = 0x80000000  # GENERIC_READ
    share_mode = 0x00000001  # FILE_SHARE_READ
    if flags & os.O_RDWR:
        desired_access = 0xC0000000  # GENERIC_READ | GENERIC_WRITE
        share_mode = 0x00000003  # FILE_SHARE_READ | FILE_SHARE_WRITE
    elif flags & os.O_WRONLY:
        desired_access = 0x40000000  # GENERIC_WRITE
        share_mode = 0x00000003

    creation_disposition = _WIN32_OPEN_EXISTING  # OPEN_EXISTING
    if flags & os.O_CREAT:
        creation_disposition = 2  # CREATE_ALWAYS if O_TRUNC else OPEN_ALWAYS
        if not flags & os.O_TRUNC:
            creation_disposition = 4  # OPEN_ALWAYS

    handle = ctypes.windll.kernel32.CreateFileW(
        path,
        desired_access,
        share_mode,
        None,
        creation_disposition,
        _WIN32_FILE_FLAG_OPEN_REPARSE_POINT | _WIN32_FILE_FLAG_BACKUP_SEMANTICS,
        None,
    )
    if handle == -1 or handle is None:
        err = ctypes.windll.kernel32.GetLastError()
        raise OSError(err, f"CreateFileW failed for {path} (error {err})")

    # Convert Win32 HANDLE to C runtime fd
    fd = msvcrt.open_osfhandle(handle, flags)
    return fd


def _win32_get_final_path_by_handle(fd: int) -> str:
    """Get the final resolved path from an open file descriptor.

    Uses GetFinalPathNameByHandleW to obtain the NT device path from the
    actual handle, then strips the \\\\?\\ prefix for comparison.
    """
    import ctypes
    import msvcrt

    # Get the underlying OS handle from the fd
    handle = msvcrt.get_osfhandle(fd)
    if handle == -1 or handle is None:
        return ""

    buf = ctypes.create_unicode_buffer(32768)
    result = ctypes.windll.kernel32.GetFinalPathNameByHandleW(handle, buf, 32768, 0)
    if result == 0:
        return ""
    return buf.value


# ---------------------------------------------------------------------------
# Filesystem adapter — safe path containment
# ---------------------------------------------------------------------------


class FilesystemError(Exception):
    """Raised for filesystem security violations."""


class FilesystemAdapter:
    """Safe filesystem operations with component-aware path containment.

    F09 (FIX): Routes all read/write/delete through handle-bound paths.
    On Windows, uses CreateFileW with FILE_FLAG_OPEN_REPARSE_POINT to
    inspect reparse attributes and prevent junction/symlink-following.
    Handle identity and containment are verified before any I/O.
    No legacy pathname-based open is reachable from the public API.
    """

    def __init__(self, base_dir: str | Path) -> None:
        self._base = Path(base_dir).resolve()

    @property
    def base_dir(self) -> Path:
        return self._base

    def resolve(self, relative: str | Path) -> Path:
        """Resolve a path relative to base, ensuring containment.

        Rejects:
        - Absolute paths
        - Parent directory traversal (..)
        - Symlinks pointing outside base
        - Sibling path escapes (vault/../vault2)

        Returns the resolved, contained path.
        """
        path_str = str(relative)

        # Reject absolute paths
        if os.path.isabs(path_str):
            raise FilesystemError(f"Absolute path rejected: {relative}")

        # Component-aware check: reject any ".." component
        rel_path = Path(relative)
        for part in rel_path.parts:
            if part == "..":
                raise FilesystemError(f"Parent directory traversal rejected: {relative}")

        # Resolve and verify containment
        full = (self._base / rel_path).resolve()

        # Verify the resolved path is within base
        try:
            full.relative_to(self._base)
        except ValueError:
            raise FilesystemError(f"Path escapes base directory: {relative} -> {full}")

        # Verify no component is a symlink outside base
        # (walk up from full to base, checking each level)
        check = full
        while check != self._base:
            if check.is_symlink():
                resolved_link = check.resolve()
                try:
                    resolved_link.relative_to(self._base)
                except ValueError:
                    raise FilesystemError(f"Symlink escapes base directory: {check}")
            check = check.parent

        return full

    # ------------------------------------------------------------------
    # F09: Windows handle-bound I/O primitives
    # ------------------------------------------------------------------

    def _open_handle_no_follow(self, path: str, flags: int, mode: int = 0o666) -> int:
        """Open a handle without following reparse points (junctions/symlinks).

        On Windows, uses FILE_FLAG_OPEN_REPARSE_POINT via CreateFileW when
        available to prevent following junctions.  On other platforms, uses
        O_NOFOLLOW.
        """
        if sys.platform == "win32":
            return _win32_open_no_reparse(path, flags, mode)
        else:
            o_nofollow = getattr(os, "O_NOFOLLOW", 0)
            return os.open(path, flags | o_nofollow, mode)

    def _get_handle_final_path(self, fd: int) -> str:
        """Obtain the final resolved path from an open file handle.

        On Windows, uses GetFinalPathNameByHandleW to get the NT path
        from the handle itself, not from the pathname used to open it.
        On other platforms, reads /proc/self/fd/{fd}.
        """
        if sys.platform == "win32":
            return _win32_get_final_path_by_handle(fd)
        else:
            try:
                return os.path.realpath(f"/proc/self/fd/{fd}")
            except OSError:
                return ""

    def _verify_handle_containment(self, fd: int, context: str = "") -> None:
        """Verify an open handle resolves within the base directory."""
        final_path = self._get_handle_final_path(fd)
        if final_path.startswith("\\\\\\\\?\\\\"):
            final_path = final_path[4:]
        if final_path.startswith("\\\\\\\\.\\\\"):
            # UNC device path — extract the drive-relative portion
            pass
        try:
            Path(final_path).relative_to(str(self._base))
        except ValueError:
            raise FilesystemError(
                f"Handle final path outside base: {final_path} (context: {context})"
            )

    def _check_reparse_point(self, path: str) -> None:
        """Check for reparse points and reject traversal/junction redirects.

        On Windows, inspects file attributes via Win32 API to detect
        junctions and symlinks and reads the reparse tag.
        On other platforms, uses os.lstat.
        """
        if sys.platform == "win32":
            if _win32_is_reparse_point(path):
                _win32_check_reparse_tag(path)
        else:
            st = os.lstat(path)
            import stat as _stat

            if _stat.S_ISLNK(st.st_mode):
                raise FilesystemError(f"Symlinks are not permitted in vault paths: {path}")

    # ------------------------------------------------------------------
    # Public I/O — ALL routes through handle-bound paths
    # ------------------------------------------------------------------

    def safe_read_bytes(self, relative: str | Path) -> bytes:
        """Read file bytes through handle-bound I/O.

        F09 (FIX):
        1. Resolve the path and verify containment (pre-open).
        2. Check for reparse points on the resolved path.
        3. Open a handle WITHOUT following reparse points.
        4. Verify handle final path within base (post-open).
        5. Stat the fd to confirm the object still exists.
        6. Read through the verified handle.
        """
        resolved = self.resolve(relative)
        path_str = str(resolved)

        # F09: Pre-open reparse-point check
        self._check_reparse_point(path_str)

        # Open handle without following reparse points
        try:
            fd = self._open_handle_no_follow(path_str, os.O_RDONLY | os.O_BINARY)
        except OSError as exc:
            raise FilesystemError(f"Cannot open file for reading: {path_str}: {exc}")

        try:
            # F09: Verify handle containment from the actual open handle
            self._verify_handle_containment(fd, f"safe_read_bytes: {relative}")

            # Verify the inode wasn't deleted/replaced during open
            st = os.fstat(fd)
            if st.st_nlink == 0:
                raise FilesystemError(f"File has zero links (deleted/replaced): {path_str}")

            # Read through the verified handle
            total = bytearray()
            while True:
                chunk = os.read(fd, 65536)
                if not chunk:
                    break
                total.extend(chunk)
            return bytes(total)
        finally:
            os.close(fd)

    def safe_write_bytes(self, relative: str | Path, data: bytes) -> int:
        """Write file bytes atomically through handle-bound I/O.

        F09 (FIX):
        1. Resolve target path and verify containment.
        2. Check for reparse points on the parent directory.
        3. Write to a temp file handle opened in the parent.
        4. Verify the temp handle stays within base.
        5. Atomically replace the target.
        6. Open the replaced target and verify containment.
        """
        if FILESYSTEM_MUTATION_DEFERRED:
            raise FilesystemError(
                "FEATURE_DEFERRED_PRE_REAL_DATA: filesystem mutation is disabled by ADR-021"
            )
        target = self.resolve(relative)
        target_str = str(target)
        parent_str = str(target.parent)

        # F09: Check the parent path for reparse points
        self._check_reparse_point(parent_str)
        target.parent.mkdir(parents=True, exist_ok=True)

        import tempfile as _tempfile

        # Create temp file in the parent directory
        fd, tmp_name = _tempfile.mkstemp(dir=parent_str, prefix=".psyche_tmp_", suffix=".tmp")
        try:
            # F09: Verify the temp handle is within base
            self._verify_handle_containment(fd, f"safe_write_bytes temp: {relative}")

            # Write through the verified handle
            written = 0
            while written < len(data):
                n = os.write(fd, data[written:])
                if n <= 0:
                    break
                written += n
            os.fsync(fd)
            os.close(fd)
            fd = -1  # Mark as closed

            # F09: Verify temp file realpath within base before replace
            tmp_real = os.path.realpath(tmp_name)
            try:
                Path(tmp_real).relative_to(str(self._base))
            except ValueError:
                raise FilesystemError(f"Temp file path escapes base: {tmp_real}")

            # Atomic replace on the same filesystem
            os.replace(tmp_name, target_str)

            # F09: Post-replace — open target handle and verify containment
            vfd = self._open_handle_no_follow(target_str, os.O_RDONLY | os.O_BINARY)
            try:
                self._verify_handle_containment(vfd, f"safe_write_bytes post-replace: {relative}")
            finally:
                os.close(vfd)

        except Exception:
            if fd >= 0:
                os.close(fd)
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

        return len(data)

    def ensure_dir(self, relative: str | Path) -> Path:
        """Ensure a directory exists within base."""
        if FILESYSTEM_MUTATION_DEFERRED:
            raise FilesystemError(
                "FEATURE_DEFERRED_PRE_REAL_DATA: filesystem mutation is disabled by ADR-021"
            )
        path = self.resolve(relative)
        # F09: Check parent for reparse points before mkdir
        self._check_reparse_point(str(path.parent))
        path.mkdir(parents=True, exist_ok=True)
        return path

    def exists(self, relative: str | Path) -> bool:
        return self.resolve(relative).exists()

    # -- F09: ALL legacy API surface routes through handle-bound paths --

    def read_bytes(self, relative: str | Path) -> bytes:
        """Read file bytes — F09: routed through handle-bound path."""
        return self.safe_read_bytes(relative)

    def write_bytes(self, relative: str | Path, data: bytes) -> int:
        """Write file bytes — F09: routed through handle-bound path."""
        return self.safe_write_bytes(relative, data)

    def read_text(self, relative: str | Path, encoding: str = "utf-8") -> str:
        """Read text — F09: routed through handle-bound safe_read_bytes."""
        return self.safe_read_bytes(relative).decode(encoding)

    def write_text(self, relative: str | Path, data: str, encoding: str = "utf-8") -> int:
        """Write text — F09: routed through handle-bound safe_write_bytes."""
        return self.safe_write_bytes(relative, data.encode(encoding))

    def delete(self, relative: str | Path) -> None:
        """Delete via handle-verified path.

        F09 (FIX): Verify parent for reparse points, open target handle
        without following reparse points, verify containment, then unlink.
        """
        if FILESYSTEM_MUTATION_DEFERRED:
            raise FilesystemError(
                "FEATURE_DEFERRED_PRE_REAL_DATA: filesystem mutation is disabled by ADR-021"
            )
        path = self.resolve(relative)
        path_str = str(path)

        # F09: Check parent for reparse points
        self._check_reparse_point(str(path.parent))

        if path.is_file():
            # Open handle, verify containment, then unlink
            fd = self._open_handle_no_follow(path_str, os.O_RDONLY | os.O_BINARY)
            try:
                self._verify_handle_containment(fd, f"delete: {relative}")
            finally:
                os.close(fd)
            path.unlink()
        elif path.is_dir():
            path.rmdir()
        else:
            raise FilesystemError(f"Path does not exist: {path_str}")

    def list_dir(self, relative: str | Path = ".") -> list[str]:
        path = self.resolve(relative)
        if path.is_dir():
            return [str(p.relative_to(path)) for p in path.iterdir()]
        return []


# ---------------------------------------------------------------------------
# Clock adapter
# ---------------------------------------------------------------------------


class ClockAdapter:
    """Deterministic clock for testing; real UTC for production."""

    def __init__(self, frozen_at: str | None = None) -> None:
        self._frozen_at = frozen_at

    def utc_now(self) -> str:
        if self._frozen_at:
            return self._frozen_at
        return datetime.datetime.now(datetime.UTC).isoformat()

    def utc_now_dt(self) -> datetime.datetime:
        if self._frozen_at:
            return datetime.datetime.fromisoformat(self._frozen_at)
        return datetime.datetime.now(datetime.UTC)


# ---------------------------------------------------------------------------
# Secrets adapter
# ---------------------------------------------------------------------------


class SecretsAdapter:
    """Read secrets via TTY prompt, never from argv/env/logs."""

    def __init__(self, source: Any | None = None) -> None:
        self._source = source or TTYSecretSource()

    def read_vault_password(self, purpose: str = "open") -> str:
        """Read vault password from user."""
        return self._source.read_secret(f"Vault password ({purpose}): ")

    def read_recovery_secret(self) -> str:
        """Read recovery secret from user."""
        return self._source.read_secret("Recovery secret: ")

    def read_new_recovery_secret(self) -> str:
        """Read new recovery secret with confirmation."""
        s1 = self._source.read_secret("New recovery secret: ")
        s2 = self._source.read_secret("Confirm recovery secret: ")
        if s1 != s2:
            raise ValueError("Recovery secrets do not match")
        return s1
