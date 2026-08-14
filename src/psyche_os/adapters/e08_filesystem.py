"""Outer E08 filesystem and application-owned quarantine boundary."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import stat
from typing import Final

from psyche_os.imports.model import PlainTextResourceProfile

REPARSE_POINT: Final = 0x400
READ_CHUNK: Final = 64 * 1024


@dataclass(frozen=True, slots=True)
class FileIdentity:
    device: int
    inode: int
    size: int
    modified_ns: int
    mode: int


@dataclass(frozen=True, slots=True)
class QuarantineRecord:
    quarantine_id: str
    source_candidate_id: str
    source_version_id: str
    protected_digest_ref: str
    byte_count: int
    profile_id: str
    parser_identity: str
    policy_lineage_id: str
    declared_mime: str | None
    declared_encoding: str | None
    processing_state: str
    rejection_reason: str | None = None


@dataclass(frozen=True, slots=True)
class QuarantineSnapshot:
    record: QuarantineRecord
    bounded_bytes: bytes
    source_identity_current: bool

    def __repr__(self) -> str:
        return f"QuarantineSnapshot(record={self.record!r}, bounded_bytes=<redacted>, source_identity_current={self.source_identity_current!r})"


class FilesystemBoundaryError(RuntimeError):
    """Content-free typed outer-boundary error."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(slots=True)
class _StoredObject:
    record: QuarantineRecord
    bounded_bytes: bytes
    path: Path
    identity: FileIdentity


class FilesystemQuarantine:
    """Only E08 component that sees user paths; quarantine names are opaque."""

    def __init__(
        self,
        *,
        identity_hook: Callable[[Path], None] | None = None,
        digest_key: bytes | None = None,
    ) -> None:
        self._objects: dict[str, _StoredObject] = {}
        self._identity_hook = identity_hook
        self._digest_key = digest_key or secrets.token_bytes(32)

    def intake(
        self,
        user_path: str | os.PathLike[str],
        *,
        profile: PlainTextResourceProfile,
        parser_identity: str,
        policy_lineage_id: str,
        declared_mime: str | None = None,
        declared_encoding: str | None = None,
    ) -> QuarantineRecord:
        path = Path(user_path)
        try:
            inspected = path.lstat()
        except OSError:
            raise FilesystemBoundaryError("source_unavailable") from None
        self._validate_regular(inspected)
        identity = self._identity(inspected)
        if self._identity_hook is not None:
            self._identity_hook(path)

        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(path, flags)
        except OSError:
            raise FilesystemBoundaryError("source_open_failed") from None
        try:
            opened = os.fstat(descriptor)
            self._validate_regular(opened)
            if self._identity(opened) != identity:
                raise FilesystemBoundaryError("source_identity_changed")
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = os.read(descriptor, min(READ_CHUNK, profile.maximum_original_bytes + 1 - total))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > profile.maximum_original_bytes:
                    raise FilesystemBoundaryError("byte_limit_exceeded")
            final = os.fstat(descriptor)
            if self._identity(final) != identity:
                raise FilesystemBoundaryError("source_identity_changed")
        finally:
            os.close(descriptor)

        bounded_bytes = b"".join(chunks)
        quarantine_id = "q-" + secrets.token_hex(16)
        source_candidate_id = "import-" + secrets.token_hex(16)
        source_version_id = source_candidate_id + "-v1"
        protected_ref = hmac.new(self._digest_key, bounded_bytes, hashlib.sha256).hexdigest()
        record = QuarantineRecord(
            quarantine_id=quarantine_id,
            source_candidate_id=source_candidate_id,
            source_version_id=source_version_id,
            protected_digest_ref=protected_ref,
            byte_count=total,
            profile_id=profile.profile_id,
            parser_identity=parser_identity,
            policy_lineage_id=policy_lineage_id,
            declared_mime=declared_mime,
            declared_encoding=declared_encoding,
            processing_state="quarantined",
        )
        self._objects[quarantine_id] = _StoredObject(record, bounded_bytes, path, identity)
        return record

    def snapshot(self, quarantine_id: str) -> QuarantineSnapshot:
        stored = self._objects.get(quarantine_id)
        if stored is None:
            raise FilesystemBoundaryError("quarantine_unavailable")
        current = self._current_identity(stored.path) == stored.identity
        expected = hmac.new(self._digest_key, stored.bounded_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, stored.record.protected_digest_ref):
            raise FilesystemBoundaryError("quarantine_integrity_failed")
        return QuarantineSnapshot(stored.record, stored.bounded_bytes, current)

    def transition(self, quarantine_id: str, state: str, rejection_reason: str | None = None) -> None:
        stored = self._objects.get(quarantine_id)
        if stored is None:
            raise FilesystemBoundaryError("quarantine_unavailable")
        stored.record = replace(
            stored.record, processing_state=state, rejection_reason=rejection_reason
        )

    def remove(self, quarantine_id: str) -> None:
        self._objects.pop(quarantine_id, None)

    def contains(self, quarantine_id: str) -> bool:
        return quarantine_id in self._objects

    def replace_bytes_for_test(self, quarantine_id: str, replacement: bytes) -> None:
        """Fault-injection hook: corruption must be detected, never accepted."""
        stored = self._objects[quarantine_id]
        stored.bounded_bytes = replacement

    @staticmethod
    def _identity(info: os.stat_result) -> FileIdentity:
        return FileIdentity(info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_mode)

    @staticmethod
    def _validate_regular(info: os.stat_result) -> None:
        attributes = getattr(info, "st_file_attributes", 0)
        if stat.S_ISLNK(info.st_mode) or attributes & REPARSE_POINT:
            raise FilesystemBoundaryError("link_or_reparse_rejected")
        if not stat.S_ISREG(info.st_mode):
            raise FilesystemBoundaryError("non_regular_file_rejected")

    @classmethod
    def _current_identity(cls, path: Path) -> FileIdentity | None:
        try:
            info = path.lstat()
            cls._validate_regular(info)
        except (OSError, FilesystemBoundaryError):
            return None
        return cls._identity(info)
