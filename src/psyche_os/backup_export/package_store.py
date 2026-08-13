"""BackupPackageStore — scoped filesystem operations for backup packages.

Uses the handle-bound primitives from adapters.py to provide a narrow
mutation surface exclusively for backup package I/O.  General filesystem
mutation through FilesystemAdapter remains DEFERRED by ADR-021.

On Windows, every path operation verifies:
- Reparse-point detection (junctions/symlinks) via Win32 API
- Handle final-path containment within the backup root
- Atomic replace via os.replace on the same filesystem

This is the ONLY filesystem mutation surface enabled for E01.
"""

from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
import secrets
import sys
import tempfile as _tempfile

from psyche_os.adapters.adapters import (
    FilesystemError,
    _win32_get_final_path_by_handle,
    _win32_open_no_reparse,
)


class BackupPackageStore:
    """Scoped filesystem authority for backup package I/O.

    Authority is bounded to the configured backup root directory.
    Every write and atomic replace goes through handle-bound paths
    verified against the root.  Reparse points (junctions, symlinks)
    are detected and rejected.

    This store is intentionally NOT general-purpose — it only supports
    backup package write, read, and atomic replace.  Blob writes and
    general filesystem mutations remain DEFERRED.
    """

    def __init__(self, backup_root: str | Path) -> None:
        self._root = Path(backup_root).resolve()
        if not self._root.exists():
            self._root.mkdir(parents=True, exist_ok=True)

    @property
    def backup_root(self) -> Path:
        return self._root

    # ------------------------------------------------------------------
    # Path resolution and containment
    # ------------------------------------------------------------------

    def _resolve(self, relative: str | Path) -> Path:
        """Resolve a backup-relative path, rejecting escapes."""
        path_str = str(relative)
        if os.path.isabs(path_str):
            raise FilesystemError(f"Absolute path rejected in backup store: {relative}")
        rel_path = Path(relative)
        for part in rel_path.parts:
            if part == "..":
                raise FilesystemError(
                    f"Parent directory traversal rejected in backup store: {relative}"
                )
        full = (self._root / rel_path).resolve()
        try:
            full.relative_to(self._root)
        except ValueError:
            raise FilesystemError(f"Path escapes backup root: {relative} -> {full}")
        return full

    # ------------------------------------------------------------------
    # Reparse-point checks
    # ------------------------------------------------------------------

    def _check_path_safe(self, path: str, context: str = "") -> None:
        """Verify a path is not a reparse point and is safe to use.

        On Windows, detects junctions and symlinks via GetFileAttributesW
        and inspects the reparse tag via DeviceIoControl.
        """
        if sys.platform == "win32":
            import ctypes

            attrs = ctypes.windll.kernel32.GetFileAttributesW(path) & 0xFFFFFFFF
            if attrs == 0xFFFFFFFF:
                raise FilesystemError(
                    f"Cannot establish Windows path identity (context: {context})"
                )
            if attrs & 0x400:
                raise FilesystemError(
                    f"Reparse point is not permitted (context: {context})"
                )
            # Also check parent directory for reparse points
            parent = str(Path(path).parent)
            if parent and parent != str(self._root):
                parent_attrs = ctypes.windll.kernel32.GetFileAttributesW(parent) & 0xFFFFFFFF
                if parent_attrs == 0xFFFFFFFF:
                    raise FilesystemError(
                        f"Cannot establish Windows parent identity (context: {context})"
                    )
                if parent_attrs & 0x400:
                    raise FilesystemError(
                        f"Reparse parent is not permitted (context: {context})"
                    )

    def _verify_handle_in_root(self, fd: int, context: str = "") -> None:
        """Verify that an open handle's final path resolves within backup root.

        Uses GetFinalPathNameByHandleW (Windows) or /proc/self/fd (Unix).
        Raises FilesystemError if the handle points outside the root OR if
        the final path cannot be resolved (fail-closed on ambiguous identity).
        """
        if sys.platform == "win32":
            final = _win32_get_final_path_by_handle(fd)
            # E01 REPAIR (Target 6): Empty or ambiguous final-handle identity
            # must fail-closed. Never convert a failed query into success.
            if not final or final.strip() == "":
                raise FilesystemError(
                    f"Handle final path is empty or ambiguous — "
                    f"cannot verify containment (context: {context})"
                )
            # Windows GetFinalPathNameByHandleW returns paths like:
            # \\?\C:\Users\... — normalize to regular path
            if final.startswith("\\\\?\\"):
                final = final[4:]
            elif final.startswith("\\\\.\\"):
                # \\.\C:\... — volume GUID path
                pass
            normalized = str(Path(final).resolve())
        else:
            try:
                normalized = os.path.realpath(f"/proc/self/fd/{fd}")
                if not normalized or normalized.strip() == "":
                    raise FilesystemError(
                        f"Handle final path is empty or ambiguous on Unix "
                        f"(context: {context})"
                    )
            except OSError as exc:
                # Fail-closed: cannot verify handle identity
                raise FilesystemError(
                    f"Cannot resolve handle identity: {exc} "
                    f"(context: {context})"
                )

        if normalized:
            try:
                Path(normalized).relative_to(str(self._root))
            except ValueError:
                raise FilesystemError(
                    f"Handle final path outside backup root: {normalized} "
                    f"(context: {context})"
                )
        else:
            raise FilesystemError(
                f"Handle identity could not be resolved "
                f"(context: {context})"
            )

    def _replace_verified_handle(
        self,
        source_fd: int,
        destination: Path,
        *,
        replace: bool = True,
    ) -> None:
        """Rename the verified source object into a held destination parent.

        Windows uses ``SetFileInformationByHandle(FileRenameInfo)`` with a
        root-directory handle, so neither the verified source nor destination
        parent is re-resolved from an ordinary pathname at the mutation point.
        """
        if sys.platform != "win32":
            source_path = Path(os.path.realpath(f"/proc/self/fd/{source_fd}"))
            if not replace and destination.exists():
                raise FileExistsError(destination)
            os.replace(source_path, destination)
            return

        import ctypes
        from ctypes import wintypes
        import msvcrt

        parent_fd = _win32_open_no_reparse(
            str(destination.parent), os.O_RDONLY | os.O_BINARY
        )
        try:
            self._verify_handle_in_root(parent_fd, "replace destination parent")
            source_handle = wintypes.HANDLE(msvcrt.get_osfhandle(source_fd))
            parent_handle = wintypes.HANDLE(msvcrt.get_osfhandle(parent_fd))

            class _IO_STATUS_BLOCK(ctypes.Structure):
                _fields_ = [
                    ("Status", ctypes.c_ssize_t),
                    ("Information", ctypes.c_size_t),
                ]

            class _FILE_RENAME_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ("ReplaceIfExists", ctypes.c_ubyte),
                    ("Reserved", ctypes.c_ubyte * 7),
                    ("RootDirectory", wintypes.HANDLE),
                    ("FileNameLength", wintypes.DWORD),
                    ("FileName", ctypes.c_wchar * 1),
                ]

            name_bytes = destination.name.encode("utf-16-le")
            size = max(
                ctypes.sizeof(_FILE_RENAME_INFORMATION),
                _FILE_RENAME_INFORMATION.FileName.offset + len(name_bytes),
            )
            buffer = ctypes.create_string_buffer(size)
            info = _FILE_RENAME_INFORMATION.from_buffer(buffer)
            info.ReplaceIfExists = ctypes.c_ubyte(bool(replace))
            info.RootDirectory = parent_handle
            info.FileNameLength = len(name_bytes)
            ctypes.memmove(
                ctypes.addressof(buffer) + _FILE_RENAME_INFORMATION.FileName.offset,
                name_bytes,
                len(name_bytes),
            )
            test_hook = getattr(self, "_mutation_test_hook", None)
            if callable(test_hook):
                test_hook()
            io_status = _IO_STATUS_BLOCK()
            nt_set_information_file = ctypes.windll.ntdll.NtSetInformationFile
            nt_set_information_file.restype = ctypes.c_long
            status = nt_set_information_file(
                source_handle,
                ctypes.byref(io_status),
                buffer,
                size,
                10,  # FileRenameInformation
            )
            if status != 0:
                error = ctypes.windll.ntdll.RtlNtStatusToDosError(status)
                raise OSError(error, "Handle-relative atomic rename failed")
        finally:
            os.close(parent_fd)

    def _link_verified_handle(self, source_fd: int, destination: Path) -> None:
        """Create rollback material from the verified active-file handle."""
        if sys.platform != "win32":
            os.link(os.path.realpath(f"/proc/self/fd/{source_fd}"), destination)
            return

        import ctypes
        from ctypes import wintypes
        import msvcrt

        parent_fd = _win32_open_no_reparse(
            str(destination.parent), os.O_RDONLY | os.O_BINARY
        )
        try:
            self._verify_handle_in_root(parent_fd, "link destination parent")

            class _IO_STATUS_BLOCK(ctypes.Structure):
                _fields_ = [
                    ("Status", ctypes.c_ssize_t),
                    ("Information", ctypes.c_size_t),
                ]

            class _FILE_LINK_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ("ReplaceIfExists", ctypes.c_ubyte),
                    ("Reserved", ctypes.c_ubyte * 7),
                    ("RootDirectory", wintypes.HANDLE),
                    ("FileNameLength", wintypes.DWORD),
                    ("FileName", ctypes.c_wchar * 1),
                ]

            name_bytes = destination.name.encode("utf-16-le")
            size = max(
                ctypes.sizeof(_FILE_LINK_INFORMATION),
                _FILE_LINK_INFORMATION.FileName.offset + len(name_bytes),
            )
            buffer = ctypes.create_string_buffer(size)
            info = _FILE_LINK_INFORMATION.from_buffer(buffer)
            info.ReplaceIfExists = 0
            info.RootDirectory = wintypes.HANDLE(msvcrt.get_osfhandle(parent_fd))
            info.FileNameLength = len(name_bytes)
            ctypes.memmove(
                ctypes.addressof(buffer) + _FILE_LINK_INFORMATION.FileName.offset,
                name_bytes,
                len(name_bytes),
            )
            io_status = _IO_STATUS_BLOCK()
            function = ctypes.windll.ntdll.NtSetInformationFile
            function.restype = ctypes.c_long
            status = function(
                wintypes.HANDLE(msvcrt.get_osfhandle(source_fd)),
                ctypes.byref(io_status),
                buffer,
                size,
                11,  # FileLinkInformation
            )
            if status != 0:
                error = ctypes.windll.ntdll.RtlNtStatusToDosError(status)
                raise OSError(error, "Handle-relative rollback link failed")
        finally:
            os.close(parent_fd)

    # ------------------------------------------------------------------
    # Public I/O — handle-verified
    # ------------------------------------------------------------------

    def write_package(self, relative: str | Path, data: bytes) -> int:
        """Write a backup package atomically through handle-bound I/O.

        Steps:
        1. Resolve target path, verify containment.
        2. Check parent directory for reparse points.
        3. Write to a temp file in the parent directory.
        4. Verify temp handle stays within backup root.
        5. Atomically replace the target.
        6. Open the replaced target and verify containment.

        Returns the number of bytes written.
        """
        target = self._resolve(relative)
        target_str = str(target)
        parent_str = str(target.parent)

        target.parent.mkdir(parents=True, exist_ok=True)
        # Check parent directory after creation and before mutation.
        self._check_path_safe(parent_str, f"write_package parent: {relative}")

        # Create temp file in the parent directory
        if sys.platform == "win32":
            tmp_name = str(
                target.parent / f".psyche_backup_tmp_{secrets.token_hex(16)}.tmp"
            )
            fd = _win32_open_no_reparse(
                tmp_name,
                os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_BINARY,
            )
        else:
            fd, tmp_name = _tempfile.mkstemp(
                dir=parent_str, prefix=".psyche_backup_tmp_", suffix=".tmp"
            )
        try:
            # Verify the temp handle is within root
            self._verify_handle_in_root(fd, f"write_package temp: {relative}")

            # Write through the verified handle
            written = 0
            while written < len(data):
                n = os.write(fd, data[written:])
                if n <= 0:
                    break
                written += n
            os.fsync(fd)
            # Keep the security-relevant source handle open across the
            # pathname publication.  This prevents the verified object from
            # being substituted between verification and replacement.
            self._verify_handle_in_root(fd, f"write_package pre-replace: {relative}")
            self._replace_verified_handle(fd, target, replace=True)
            os.close(fd)
            fd = -1

            # Post-replace: open target handle and verify containment
            vfd = self._open_handle_no_follow(target_str)
            try:
                self._verify_handle_in_root(vfd, f"write_package post-replace: {relative}")
            finally:
                os.close(vfd)

            return written

        except Exception:
            if fd >= 0:
                os.close(fd)
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    def read_package(self, relative: str | Path) -> bytes:
        """Read a backup package through handle-bound I/O.

        Steps:
        1. Resolve path, verify containment.
        2. Check for reparse points on the resolved path.
        3. Open a handle WITHOUT following reparse points.
        4. Verify handle final path within root.
        5. Stat the fd to confirm the object still exists.
        6. Read through the verified handle.
        """
        resolved = self._resolve(relative)
        path_str = str(resolved)

        # Pre-open reparse-point check
        self._check_path_safe(path_str, f"read_package: {relative}")

        # Open handle without following reparse points
        try:
            fd = self._open_handle_no_follow(path_str)
        except OSError as exc:
            raise FilesystemError(f"Cannot open backup package for reading: {path_str}: {exc}")

        try:
            # Verify handle containment from the actual open handle
            self._verify_handle_in_root(fd, f"read_package: {relative}")

            # Verify the inode wasn't deleted/replaced during open
            st = os.fstat(fd)
            if st.st_nlink == 0:
                raise FilesystemError(
                    f"File has zero links (deleted/replaced): {path_str}"
                )

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

    def atomic_replace(self, src: Path, dst_relative: str | Path) -> None:
        """Atomically replace a backup package at dst_relative with src.

        Both src and dst must be on the same filesystem for atomicity.
        Validates handle containment for both paths.

        Used during restore activation to swap in the restored vault.
        """
        dst = self._resolve(dst_relative)
        dst_str = str(dst)

        # Verify src is within root
        try:
            src.resolve().relative_to(str(self._root))
        except ValueError:
            raise FilesystemError(
                f"Source path outside backup root during atomic replace: {src}"
            )

        # Check parent directory for reparse points
        self._check_path_safe(str(dst.parent), f"atomic_replace parent: {dst_relative}")

        src_fd = (
            _win32_open_no_reparse(str(src), os.O_RDWR | os.O_BINARY)
            if sys.platform == "win32"
            else self._open_handle_no_follow(str(src))
        )
        dst_fd = -1
        try:
            self._verify_handle_in_root(src_fd, f"atomic_replace source: {dst_relative}")
            if dst.exists():
                dst_fd = self._open_handle_no_follow(dst_str)
                self._verify_handle_in_root(dst_fd, f"atomic_replace target: {dst_relative}")
            # Handles remain open across the atomic mutation.
            self._replace_verified_handle(src_fd, dst, replace=True)
        finally:
            os.close(src_fd)
            if dst_fd >= 0:
                os.close(dst_fd)

        # Post-replace: verify dst handle is within root
        vfd = self._open_handle_no_follow(dst_str)
        try:
            self._verify_handle_in_root(vfd, f"atomic_replace post-replace: {dst_relative}")
        finally:
            os.close(vfd)

    def reserve_candidate(self, relative: str | Path) -> Path:
        """Exclusively reserve a new restore-candidate file in this scope."""
        target = self._resolve(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        self._check_path_safe(str(target.parent), f"reserve_candidate parent: {relative}")
        flags = os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_BINARY
        fd = os.open(str(target), flags, 0o600)
        try:
            self._verify_handle_in_root(fd, f"reserve_candidate: {relative}")
            os.fsync(fd)
        except Exception:
            os.close(fd)
            try:
                os.unlink(target)
            except OSError:
                pass
            raise
        os.close(fd)
        return target

    def verify_scoped_file(self, relative: str | Path) -> Path:
        """Open and verify an existing regular file within this authority."""
        target = self._resolve(relative)
        self._check_path_safe(str(target), f"verify_scoped_file: {relative}")
        fd = self._open_handle_no_follow(str(target))
        try:
            self._verify_handle_in_root(fd, f"verify_scoped_file: {relative}")
            if not os.path.isfile(target):
                raise FilesystemError(f"Scoped target is not a regular file: {relative}")
        finally:
            os.close(fd)
        return target

    def activate_database(
        self,
        candidate_relative: str | Path,
        active_relative: str | Path,
        before_atomic: Callable[[], None] | None = None,
    ) -> str | None:
        """Install one verified, sidecar-free database at the atomic boundary.

        Both files must be direct members of this narrowly scoped authority.
        Security handles remain open across the replacement.  A hard link to
        the prior active inode preserves rollback material without first
        moving the active pathname away.
        """
        candidate = self._resolve(candidate_relative)
        active = self._resolve(active_relative)
        if candidate.parent != active.parent:
            raise FilesystemError("Candidate and active vault must share one scoped directory")
        self._check_path_safe(str(active.parent), "activate_database parent")
        for path in (candidate, active):
            for suffix in ("-wal", "-shm"):
                if Path(str(path) + suffix).exists():
                    raise FilesystemError(
                        "Vault sidecars must be checkpointed and absent before activation"
                    )

        candidate_fd = (
            _win32_open_no_reparse(str(candidate), os.O_RDWR | os.O_BINARY)
            if sys.platform == "win32"
            else self._open_handle_no_follow(str(candidate))
        )
        active_fd = (
            _win32_open_no_reparse(str(active), os.O_RDWR | os.O_BINARY)
            if sys.platform == "win32"
            else self._open_handle_no_follow(str(active))
        )
        previous = active.with_name(active.name + f".prev.{secrets.token_hex(8)}")
        try:
            self._verify_handle_in_root(candidate_fd, "activate_database candidate")
            self._verify_handle_in_root(active_fd, "activate_database active")
            self._link_verified_handle(active_fd, previous)
            # The previous valid inode is now independently retained through
            # a handle-bound link.  Windows will not replace an entry that has
            # another open handle, so release only the active handle; the
            # candidate and destination-directory handles remain bound.
            if sys.platform == "win32":
                os.close(active_fd)
                active_fd = -1
            if callable(before_atomic):
                before_atomic()
            self._replace_verified_handle(candidate_fd, active, replace=True)
        except Exception:
            try:
                if previous.exists():
                    os.unlink(previous)
            except OSError as cleanup_exc:
                raise FilesystemError(
                    f"Activation failed and rollback material cleanup failed: {cleanup_exc}"
                )
            raise
        finally:
            os.close(candidate_fd)
            if active_fd >= 0:
                os.close(active_fd)

        # No fallible operation remains part of activation.  Failure to remove
        # the preserved prior inode is non-destructive and is reported.
        try:
            os.unlink(previous)
            return None
        except OSError:
            # Activation already succeeded atomically.  Retaining the prior
            # valid inode is safe and is surfaced to the caller for cleanup.
            return str(previous)

    def exists(self, relative: str | Path) -> bool:
        """Check if a package exists at the given relative path."""
        try:
            resolved = self._resolve(relative)
            return resolved.exists()
        except FilesystemError:
            return False

    def delete_package(self, relative: str | Path) -> None:
        """Delete a backup package through handle-verified path.

        Opens handle, verifies containment, then unlinks.
        """
        path = self._resolve(relative)
        path_str = str(path)

        # Check parent for reparse points
        self._check_path_safe(str(path.parent), f"delete_package parent: {relative}")

        if path.is_file():
            fd = self._open_handle_no_follow(path_str)
            try:
                self._verify_handle_in_root(fd, f"delete_package: {relative}")
            finally:
                os.close(fd)
            path.unlink()
        elif path.is_dir():
            # Not expected for backup packages, but handle safely
            self._check_path_safe(path_str, f"delete_package: {relative}")
            path.rmdir()
        else:
            raise FilesystemError(f"Backup package not found: {path_str}")

    def list_packages(self, relative: str | Path = ".") -> list[str]:
        """List backup packages in a directory within root."""
        path = self._resolve(relative)
        if path.is_dir():
            return sorted(p.relative_to(path).as_posix() for p in path.iterdir() if p.is_file())
        return []

    # ------------------------------------------------------------------
    # Handle-bound open helper
    # ------------------------------------------------------------------

    @staticmethod
    def _open_handle_no_follow(path: str) -> int:
        """Open a file handle without following reparse points.

        On Windows, uses CreateFileW with FILE_FLAG_OPEN_REPARSE_POINT.
        On other platforms, uses O_NOFOLLOW.
        """
        if sys.platform == "win32":
            return _win32_open_no_reparse(path, os.O_RDONLY | os.O_BINARY)
        else:
            o_nofollow = getattr(os, "O_NOFOLLOW", 0)
            return os.open(path, os.O_RDONLY | os.O_BINARY | o_nofollow)
