"""validate_e01_assurance.py — Read-only validator for E01 evidence.

Validates:
1. E01 evidence index file exists and is structurally valid
2. All required artifact paths exist with correct digests
3. Backup/restore CLI returns non-deferred results
4. Blob/general-filesystem paths still return deferred
5. REAL_DATA_GATE remains CLOSED
6. Generated evidence is factual, not fictitious

This validator is READ-ONLY — it never manufactures evidence or claims
independence that doesn't exist. If evidence is missing, it reports
BLOCKED, not PASS.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

EVIDENCE_INDEX_PATH = ROOT / "artifacts" / "e01" / "evidence_index.json"
REAL_DATA_GATE_PATH = ROOT / "docs" / "architecture" / "REAL_DATA_GATE.yaml"
EXPECTED_ACCEPTED_BASELINE = "0090ba0"


def _fail(step: str, detail: str) -> dict:
    return {"step": step, "status": "FAIL", "detail": detail}


def _pass(step: str, detail: str = "") -> dict:
    return {"step": step, "status": "PASS", "detail": detail}


def _blocked(step: str, detail: str = "") -> dict:
    return {"step": step, "status": "BLOCKED", "detail": detail}


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_evidence_index_exists() -> dict:
    """Verify evidence index file exists and is parseable JSON."""
    if not EVIDENCE_INDEX_PATH.exists():
        return _fail(
            "evidence_index_exists",
            f"Evidence index not found at {EVIDENCE_INDEX_PATH}",
        )

    try:
        with open(EVIDENCE_INDEX_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return _fail("evidence_index_exists", f"Evidence index is not valid JSON: {e}")

    required = ["schema_version", "epic", "accepted_commit", "profile", "real_data_gate"]
    missing = [k for k in required if k not in data]
    if missing:
        return _fail(
            "evidence_index_structure",
            f"Evidence index missing required fields: {missing}",
        )

    if data.get("epic") != "E01":
        return _fail("evidence_index_epic", f"Expected epic E01, got {data.get('epic')}")

    if data.get("real_data_gate") != "CLOSED":
        return _fail(
            "evidence_index_gate",
            f"Expected CLOSED gate, got {data.get('real_data_gate')}",
        )

    if data.get("profile") != "synthetic-database-only":
        return _fail(
            "evidence_index_profile",
            f"Wrong profile: {data.get('profile')}",
        )

    return _pass("evidence_index_structure", f"Valid evidence index for E01")


def check_real_data_gate_closed() -> dict:
    """Verify REAL_DATA_GATE remains CLOSED."""
    if not REAL_DATA_GATE_PATH.exists():
        return _blocked(
            "real_data_gate_closed",
            "REAL_DATA_GATE.yaml not found — cannot verify gate state",
        )

    with open(REAL_DATA_GATE_PATH, encoding="utf-8") as f:
        content = f.read()

    if 'status: "CLOSED"' not in content and "status: CLOSED" not in content:
        return _fail(
            "real_data_gate_closed",
            "REAL_DATA_GATE is not CLOSED — E01 must not open the gate",
        )

    return _pass("real_data_gate_closed", "REAL_DATA_GATE remains CLOSED")


def check_backup_restore_not_deferred() -> dict:
    """Verify backup/restore CLI commands are no longer deferred."""
    try:
        from psyche_os.interfaces.cli import create_cli

        cli = create_cli()

        commands = [
            (["backup", "create", "--output", "x"], "backup.create"),
            (["backup", "verify", "--package", "x"], "backup.verify"),
            (["restore", "verify"], "restore.verify"),
            (["restore", "activate"], "restore.activate"),
        ]

        for argv, name in commands:
            result = cli.dispatch(argv)
            data = result.data or {}
            state = data.get("state", "")
            if state == "FEATURE_DEFERRED_PRE_REAL_DATA":
                return _fail(
                    "backup_restore_activated",
                    f"{name} is still deferred — E01 must activate it",
                )

        return _pass("backup_restore_activated", "All backup/restore commands are activated")

    except Exception as exc:
        return _blocked("backup_restore_activated", f"CLI import failed: {exc}")


def check_blob_and_filesystem_still_deferred() -> dict:
    """Verify blob writes and general filesystem mutation remain deferred."""
    try:
        from psyche_os.adapters.adapters import FILESYSTEM_MUTATION_DEFERRED, FilesystemAdapter, FilesystemError

        if not FILESYSTEM_MUTATION_DEFERRED:
            return _fail(
                "blob_filesystem_deferred",
                "FILESYSTEM_MUTATION_DEFERRED is False — general mutation is active",
            )

        adapter = FilesystemAdapter(os.devnull)
        try:
            adapter.safe_write_bytes("test.bin", b"probe")
            return _fail(
                "blob_filesystem_deferred",
                "FilesystemAdapter.safe_write_bytes succeeded — should be deferred",
            )
        except FilesystemError as e:
            if "FEATURE_DEFERRED" in str(e):
                return _pass("blob_filesystem_deferred", "General filesystem mutation remains deferred")
            return _blocked("blob_filesystem_deferred", f"Unexpected error: {e}")

    except Exception as exc:
        return _blocked("blob_filesystem_deferred", f"Import failed: {exc}")


def check_imports_clean() -> dict:
    """Verify all E01 modules import cleanly."""
    modules = [
        "psyche_os.backup_export.operations",
        "psyche_os.backup_export.package_store",
        "psyche_os.backup_export",
        "psyche_os.interfaces.cli",
    ]

    for modname in modules:
        try:
            __import__(modname)
        except Exception as exc:
            return _fail("imports_clean", f"Import failed for {modname}: {exc}")

    return _pass("imports_clean", f"All {len(modules)} modules import cleanly")


def check_allowed_table_inventory() -> dict:
    """Verify backup table inventory matches schema tables."""
    try:
        from psyche_os.backup_export.operations import (
            _BACKUP_INVENTORY_TABLES,
            _EXCLUDED_TABLES,
        )
        from psyche_os.storage.schema import ALL_DDL

        # ALL_DDL is a list of (name, ddl) tuples
        schema_tables = set(name for name, _ in ALL_DDL)
        inventory = set(_BACKUP_INVENTORY_TABLES)
        excluded = _EXCLUDED_TABLES
        expected = schema_tables - excluded

        missing = expected - inventory
        extra = inventory - expected

        if missing:
            return _fail(
                "table_inventory",
                f"Schema tables not in backup inventory: {sorted(missing)}",
            )
        if extra:
            return _fail(
                "table_inventory",
                f"Backup inventory has tables not in schema: {sorted(extra)}",
            )

        return _pass("table_inventory", f"{len(inventory)} tables match schema")

    except Exception as exc:
        return _blocked("table_inventory", f"Import failed: {exc}")


def check_canary_not_in_source() -> dict:
    """Canary scan: verify test canary not hard-coded in production paths.

    This is a best-effort check — unit/integration tests may legitimately
    contain canary values. Only checks production source code.
    """
    canary = b"PSYCHE-E01-CANARY-0429f87e3b1c6a5d"
    canary_hex = canary.hex()

    src_dir = ROOT / "src"
    if not src_dir.exists():
        return _blocked("canary_scan", "src directory not found")

    found_in: list[str] = []
    for py_file in src_dir.rglob("*.py"):
        try:
            content = py_file.read_bytes()
            if canary in content or canary_hex.encode() in content:
                found_in.append(str(py_file.relative_to(ROOT)))
        except Exception:
            pass

    if found_in:
        return _fail(
            "canary_scan",
            f"Canary found in production source: {found_in}",
        )

    return _pass("canary_scan", "No canary found in production source")


def check_e01_test_files_exist() -> dict:
    """Verify E01 test files exist."""
    test_files = [
        "tests/integration/test_e01_backup_restore.py",
        "tests/integration/test_e01_backup_faults.py",
        "tests/integration/test_e01_windows_boundary.py",
        "tests/integration/test_e01_recovery_drill.py",
        "tests/integration/test_e01_evidence_validator.py",
    ]

    missing = [f for f in test_files if not (ROOT / f).exists()]
    if missing:
        return _fail("test_files_exist", f"Missing test files: {missing}")

    return _pass("test_files_exist", f"All {len(test_files)} E01 test files present")


def check_backup_package_store_available() -> dict:
    """Verify BackupPackageStore is importable and functional."""
    try:
        from psyche_os.backup_export.package_store import BackupPackageStore

        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            store = BackupPackageStore(tmp)
            data = b"e01 validation probe"
            written = store.write_package("probe.backup", data)
            if written != len(data):
                return _fail("package_store", "Write returned wrong byte count")
            read_back = store.read_package("probe.backup")
            if read_back != data:
                return _fail("package_store", "Read back does not match written data")

        return _pass("package_store", "BackupPackageStore functional")

    except Exception as exc:
        return _fail("package_store", f"BackupPackageStore check failed: {exc}")


# ---------------------------------------------------------------------------
# E01 REPAIR — Truthful evidence checks (target 7)
# ---------------------------------------------------------------------------

ALLOWED_EVIDENCE_STATUSES = {"REPAIRED", "PASS", "VERIFIED"}
FORBIDDEN_EVIDENCE_STATUSES = {"PENDING", "FIX_REQUIRED", "BLOCKED", "MISSING", "FICTITIOUS"}
FORBIDDEN_REVIEWER_VALUES = {"PENDING", "BLOCKED", "PLACEHOLDER", "", None}


def check_evidence_timestamps_set() -> dict:
    """Reject missing, malformed, future-generated, or expired evidence."""
    with open(EVIDENCE_INDEX_PATH, encoding="utf-8") as f:
        data = json.load(f)

    failures = []
    parsed: dict[str, datetime.datetime] = {}
    for field in ("generated_at", "expiry"):
        val = data.get(field)
        if not val or not isinstance(val, str) or val.strip() == "":
            failures.append(f"'{field}' is empty, missing, or non-string")
            continue
        try:
            parsed_value = datetime.datetime.fromisoformat(val.replace("Z", "+00:00"))
            if parsed_value.tzinfo is None:
                raise ValueError("timezone offset is required")
            parsed[field] = parsed_value.astimezone(datetime.UTC)
        except ValueError as exc:
            failures.append(f"'{field}' is not a timezone-aware ISO-8601 timestamp: {exc}")

    now = datetime.datetime.now(datetime.UTC)
    generated_at = parsed.get("generated_at")
    expiry = parsed.get("expiry")
    if generated_at and generated_at > now + datetime.timedelta(minutes=5):
        failures.append("'generated_at' is in the future")
    if expiry and expiry <= now:
        failures.append("evidence is expired")
    if generated_at and expiry and expiry <= generated_at:
        failures.append("'expiry' must be later than 'generated_at'")

    if failures:
        return _fail("evidence_timestamps", "; ".join(failures))
    return _pass("evidence_timestamps", "timestamps are valid and evidence is unexpired")


def check_artifact_digests_not_empty() -> dict:
    """Reject evidence entries whose artifact_digests map is missing or empty."""
    with open(EVIDENCE_INDEX_PATH, encoding="utf-8") as f:
        data = json.load(f)

    evidence = data.get("evidence", {})
    if not evidence:
        return _fail("artifact_digests", "Evidence section is empty")

    failures = []
    for evidence_key, entry in evidence.items():
        digests = entry.get("artifact_digests", {})
        if not digests:
            failures.append(f"'{evidence_key}' has empty/missing artifact_digests")
            continue
        # Reject placeholder digests
        for artifact_name, digest_val in digests.items():
            if not digest_val or "generated_from_actual_source" in digest_val:
                failures.append(
                    f"'{evidence_key}.artifact_digests.{artifact_name}' "
                    f"has placeholder value: {digest_val}"
                )

    if failures:
        return _fail("artifact_digests", "; ".join(failures))
    return _pass("artifact_digests", "All artifact_digests entries are factual")


def check_evidence_status_not_forbidden() -> dict:
    """Reject evidence with PENDING, FIX_REQUIRED, BLOCKED, or MISSING status."""
    with open(EVIDENCE_INDEX_PATH, encoding="utf-8") as f:
        data = json.load(f)

    evidence = data.get("evidence", {})
    failures = []
    for evidence_key, entry in evidence.items():
        status = entry.get("status", "")
        if status in FORBIDDEN_EVIDENCE_STATUSES:
            failures.append(f"'{evidence_key}' status is '{status}' — must be repaired")

    if failures:
        return _fail("evidence_status", "; ".join(failures))
    return _pass("evidence_status", "All evidence entries have acceptable status")


def check_evidence_state_consistency() -> dict:
    """Reject baseline or aggregate states that contradict their evidence."""
    with open(EVIDENCE_INDEX_PATH, encoding="utf-8") as f:
        data = json.load(f)

    failures: list[str] = []
    if data.get("accepted_commit") != EXPECTED_ACCEPTED_BASELINE:
        failures.append(
            f"accepted_commit must be {EXPECTED_ACCEPTED_BASELINE}, "
            f"got {data.get('accepted_commit')!r}"
        )
    if data.get("real_data_gate") != "CLOSED":
        failures.append("evidence real_data_gate contradicts required CLOSED state")

    verdict = data.get("verdict", "")
    evidence = data.get("evidence", {})
    if verdict == "FIX_REQUIRED_REPAIRED":
        inconsistent = [
            key for key, entry in evidence.items()
            if entry.get("status") != "REPAIRED"
            or entry.get("capability_state") != "CANDIDATE_REPAIRED"
        ]
        if inconsistent:
            failures.append(
                "repaired verdict contradicts evidence entries: "
                + ", ".join(sorted(inconsistent))
            )

    if failures:
        return _fail("evidence_state_consistency", "; ".join(failures))
    return _pass("evidence_state_consistency", "baseline and aggregate evidence state agree")


def check_reviewer_roles_not_pending() -> dict:
    """Reject PENDING, BLOCKED, or PLACEHOLDER reviewer roles."""
    with open(EVIDENCE_INDEX_PATH, encoding="utf-8") as f:
        data = json.load(f)

    reviewer_roles = data.get("reviewer_roles", {})
    if not reviewer_roles:
        return _fail("reviewer_roles", "reviewer_roles section is empty/missing")

    failures = []
    for role_name, role_value in reviewer_roles.items():
        if role_value in FORBIDDEN_REVIEWER_VALUES:
            failures.append(f"'{role_name}' is '{role_value}' — must have a real reviewer or REQUIRED")

    if failures:
        return _fail("reviewer_roles", "; ".join(failures))
    return _pass("reviewer_roles", "No PENDING/BLOCKED reviewer roles")


def check_artifact_digests_match_disk() -> dict:
    """Verify each claimed artifact_digest matches the actual file on disk."""
    with open(EVIDENCE_INDEX_PATH, encoding="utf-8") as f:
        data = json.load(f)

    # Map of artifact short-name → repo-relative path
    KNOWN_ARTIFACTS = {
        "operations.py": "src/psyche_os/backup_export/operations.py",
        "package_store.py": "src/psyche_os/backup_export/package_store.py",
        "envelope.py": "src/psyche_os/crypto/envelope.py",
        "cli.py": "src/psyche_os/interfaces/cli.py",
        "test_e01_backup_restore.py": "tests/integration/test_e01_backup_restore.py",
        "test_e01_backup_faults.py": "tests/integration/test_e01_backup_faults.py",
        "test_e01_windows_boundary.py": "tests/integration/test_e01_windows_boundary.py",
        "test_e01_recovery_drill.py": "tests/integration/test_e01_recovery_drill.py",
        "validate_e01_assurance.py": "scripts/validate_e01_assurance.py",
        "test_e01_evidence_validator.py": "tests/integration/test_e01_evidence_validator.py",
    }

    evidence = data.get("evidence", {})
    mismatches = []
    verified = 0

    for evidence_key, entry in evidence.items():
        digests = entry.get("artifact_digests", {})
        for artifact_name, claimed_digest in digests.items():
            repo_rel = KNOWN_ARTIFACTS.get(artifact_name)
            if not repo_rel:
                mismatches.append(
                    f"'{evidence_key}.{artifact_name}' — unknown artifact, "
                    f"cannot verify on disk"
                )
                continue

            file_path = ROOT / repo_rel
            if not file_path.exists():
                mismatches.append(
                    f"'{evidence_key}.{artifact_name}' → {repo_rel} does not exist"
                )
                continue

            actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
            expected_hash = claimed_digest.replace("sha256:", "")
            if actual_hash != expected_hash:
                mismatches.append(
                    f"'{evidence_key}.{artifact_name}' — digest mismatch: "
                    f"claimed sha256:{expected_hash[:16]}..., "
                    f"actual sha256:{actual_hash[:16]}..."
                )
            else:
                verified += 1

    if mismatches:
        return _fail("artifact_digest_verification", "; ".join(mismatches))
    return _pass(
        "artifact_digest_verification",
        f"All {verified} artifact digests match on-disk files",
    )


def check_overall_verdict_is_repaired() -> dict:
    """Reject a verdict that still says FIX_REQUIRED (must be repaired)."""
    with open(EVIDENCE_INDEX_PATH, encoding="utf-8") as f:
        data = json.load(f)

    verdict = data.get("verdict", "")
    if not verdict:
        return _fail("verdict", "verdict field is empty/missing")
    if verdict in ("FIX_REQUIRED", "BLOCKED", "PENDING"):
        return _fail(
            "verdict",
            f"Overall verdict is '{verdict}' — must be FIX_REQUIRED_REPAIRED or PASS",
        )
    return _pass("verdict", f"Overall verdict: {verdict}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_all_checks() -> tuple[list[dict], bool]:
    """Run all E01 assurance checks. Returns (results, all_passed)."""
    checks = [
        check_evidence_index_exists,
        check_real_data_gate_closed,
        check_imports_clean,
        check_backup_restore_not_deferred,
        check_blob_and_filesystem_still_deferred,
        check_allowed_table_inventory,
        check_e01_test_files_exist,
        check_backup_package_store_available,
        check_canary_not_in_source,
        # E01 REPAIR target 7 — truthful evidence
        check_evidence_timestamps_set,
        check_artifact_digests_not_empty,
        check_evidence_status_not_forbidden,
        check_evidence_state_consistency,
        check_reviewer_roles_not_pending,
        check_artifact_digests_match_disk,
        check_overall_verdict_is_repaired,
    ]

    results: list[dict] = []
    for check_fn in checks:
        try:
            result = check_fn()
        except Exception as exc:
            result = _fail(check_fn.__name__, f"Check raised: {exc}")
        results.append(result)

    all_passed = all(r["status"] == "PASS" for r in results)
    return results, all_passed


def print_report(results: list[dict], all_passed: bool) -> int:
    """Print a human-readable report. Returns exit code."""
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    blocked = sum(1 for r in results if r["status"] == "BLOCKED")

    print(f"E01 Assurance Validation Report")
    print(f"Generated: {datetime.datetime.now(datetime.UTC).isoformat()}")
    print(f"Checks: {len(results)} total | {passed} PASS | {failed} FAIL | {blocked} BLOCKED")
    print()

    for r in results:
        status = r["status"]
        marker = "✓" if status == "PASS" else ("✗" if status == "FAIL" else "∅")
        print(f"  {marker} [{status:7s}] {r['step']}")
        if r["detail"]:
            print(f"       {r['detail']}")

    print()
    if all_passed:
        print("E01 ASSURANCE: PASS")
        return 0
    else:
        print("E01 ASSURANCE: FAIL (see blocked/failed checks above)")
        return 1


if __name__ == "__main__":
    results, all_passed = run_all_checks()
    exit_code = print_report(results, all_passed)
    sys.exit(exit_code)
