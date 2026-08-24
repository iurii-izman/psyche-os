"""Compute the explicit-task dirty candidate identity, version 1.

The manifest is a UTF-8 text file containing one repository-relative path per
line. Blank lines and lines beginning with ``#`` are ignored. No path is
discovered automatically. Serialization is UTF-8 with NUL-delimited fields:
the version tag, HEAD, then lexically sorted entry records. A tracked record
contains the exact ``git diff --binary HEAD -- <path>`` bytes; an untracked
record contains the path, byte length, and SHA-256 of its current bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ALGORITHM = "PSYCHE-OS-DIRTY-CANDIDATE-v1"


def _git(root: Path, *arguments: str) -> bytes:
    completed = subprocess.run(["git", *arguments], cwd=root, capture_output=True, check=True)
    return completed.stdout


def read_manifest(path: Path) -> list[str]:
    entries = [line.strip().replace("\\", "/") for line in path.read_text(encoding="utf-8").splitlines()]
    result = [entry for entry in entries if entry and not entry.startswith("#")]
    if len(result) != len(set(result)):
        raise ValueError("manifest contains duplicate paths")
    if any(Path(entry).is_absolute() or ".." in Path(entry).parts for entry in result):
        raise ValueError("manifest paths must be repository-relative")
    return sorted(result)


def record_bytes(root: Path, path: str) -> bytes:
    target = root / path
    if not target.is_file():
        raise ValueError(f"manifest path is not a file: {path}")
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "--", path], cwd=root, capture_output=True).returncode == 0
    if tracked:
        diff = _git(root, "diff", "--binary", "HEAD", "--", path)
        return b"T\0" + path.encode("utf-8") + b"\0" + len(diff).to_bytes(8, "big") + diff
    data = target.read_bytes()
    return b"U\0" + path.encode("utf-8") + b"\0" + str(len(data)).encode("ascii") + b"\0" + hashlib.sha256(data).hexdigest().encode("ascii")


def candidate_digest(root: Path, entries: list[str]) -> tuple[str, str]:
    head = _git(root, "rev-parse", "HEAD").decode("ascii").strip()
    payload = b"\0".join([ALGORITHM.encode("ascii"), head.encode("ascii"), *(record_bytes(root, entry) for entry in sorted(entries))])
    return head, hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 for the exact bytes of one file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def detached_receipt(root: Path, manifest_path: Path) -> dict[str, object]:
    """Create receipt metadata without making the receipt a candidate input."""
    entries = read_manifest(manifest_path)
    head, digest = candidate_digest(root, entries)
    evidence_path = root / "docs/development/personal-mode-v1/P1_PACKAGE_BOUNDARY_EVIDENCE.md"
    return {
        "receipt_version": "PMV1-DIRTY-CANDIDATE-DETACHED-RECEIPT-V1",
        "candidate_algorithm": ALGORITHM,
        "head": head,
        "origin_main": _git(root, "rev-parse", "origin/main").decode("ascii").strip(),
        "manifest_path": manifest_path.relative_to(root).as_posix(),
        "manifest_sha256": sha256_file(manifest_path),
        "task_owned_count": len(entries),
        "candidate_sha256": digest,
        "evidence_file_path": evidence_path.relative_to(root).as_posix(),
        "evidence_file_sha256": sha256_file(evidence_path),
        "real_data_gate": "CLOSED",
    }


def verify_detached_receipt(root: Path, manifest_path: Path, receipt_path: Path) -> None:
    """Fail closed unless receipt metadata binds the current frozen candidate."""
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    expected = detached_receipt(root, manifest_path)
    required = (
        "receipt_version", "candidate_algorithm", "head", "origin_main", "manifest_path",
        "manifest_sha256", "task_owned_count", "candidate_sha256", "evidence_file_path",
        "evidence_file_sha256", "real_data_gate",
    )
    for field in required:
        if receipt.get(field) != expected[field]:
            raise ValueError(f"receipt field does not match current candidate: {field}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path, help="explicit repository-relative task-owned manifest")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--write-detached-receipt", type=Path, help="write excluded receipt after candidate freeze")
    actions.add_argument("--verify-detached-receipt", type=Path, help="verify excluded receipt against current candidate")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    manifest = arguments.manifest if arguments.manifest.is_absolute() else root / arguments.manifest
    try:
        entries = read_manifest(manifest)
        head, digest = candidate_digest(root, entries)
        if arguments.write_detached_receipt:
            receipt_path = arguments.write_detached_receipt
            if not receipt_path.is_absolute():
                receipt_path = root / receipt_path
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            receipt_path.write_text(
                json.dumps(detached_receipt(root, manifest), indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        if arguments.verify_detached_receipt:
            receipt_path = arguments.verify_detached_receipt
            if not receipt_path.is_absolute():
                receipt_path = root / receipt_path
            verify_detached_receipt(root, manifest, receipt_path)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(f"algorithm={ALGORITHM}")
    print(f"head={head}")
    print(f"manifest={manifest.relative_to(root).as_posix()}")
    print("task_owned=")
    for entry in entries:
        print(entry)
    print(f"digest={digest}")
    if arguments.write_detached_receipt:
        print(f"detached_receipt={arguments.write_detached_receipt}")
    if arguments.verify_detached_receipt:
        print(f"detached_receipt_verified={arguments.verify_detached_receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
