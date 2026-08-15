"""E10 narrow outer filesystem adapter for report file output.

Only this module sees user-selected report destinations.  It validates the
destination against a caller-owned base directory (no traversal), refuses
silent overwrite, rejects links/non-regular targets, and writes atomically.
It never uploads and never touches canonical storage.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
import os
from pathlib import Path
import secrets
import tempfile


class E10FileWriteError(RuntimeError):
    """Typed outer-boundary write failure with a stable content-free code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class ExportFileInfo:
    """Bounded write result; never contains the destination path."""

    export_id: str
    byte_count: int

    def __repr__(self) -> str:
        return (
            f"ExportFileInfo(export_id={self.export_id!r}, "
            f"byte_count={self.byte_count!r})"
        )


class ReportFileWriter:
    """Validates and atomically writes one report file under a base directory."""

    def __init__(self, base_dir: str | os.PathLike[str]) -> None:
        self._base_dir = Path(base_dir).resolve()

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    def resolve_destination(self, destination: str) -> Path:
        """Validate and resolve a relative destination to its concrete target.

        Returns the resolved absolute target path; raises a content-free
        E10FileWriteError otherwise.  The destination link is rejected before
        resolution so a symlink whose target stays inside base_dir cannot hide.
        """
        candidate = Path(destination)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise E10FileWriteError("destination_outside_base")
        candidate_path = self._base_dir / candidate
        if candidate_path.is_symlink():
            raise E10FileWriteError("link_rejected")
        resolved = candidate_path.resolve()
        if not resolved.is_relative_to(self._base_dir):
            raise E10FileWriteError("destination_outside_base")
        if resolved.is_symlink():
            raise E10FileWriteError("link_rejected")
        return resolved

    def write(
        self,
        text: str,
        destination: str,
        *,
        overwrite: bool = False,
    ) -> ExportFileInfo:
        resolved = self.resolve_destination(destination)
        if resolved.exists():
            if not resolved.is_file():
                raise E10FileWriteError("not_regular_file")
            if not overwrite:
                raise E10FileWriteError("destination_exists")

        parent = resolved.parent
        if not parent.is_relative_to(self._base_dir):
            raise E10FileWriteError("destination_outside_base")
        parent.mkdir(parents=True, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(
            dir=parent, prefix=".e10-write-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, resolved)
        except OSError:
            raise E10FileWriteError("write_failed") from None
        finally:
            if os.path.exists(tmp_path):
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)
        return ExportFileInfo(
            export_id="e10-export-" + secrets.token_hex(8),
            byte_count=len(text.encode("utf-8")),
        )
