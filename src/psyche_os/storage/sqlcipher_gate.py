"""SQLCipher profile gate — 8 mandatory probes before storage is accepted.

Implements ADR-007 and the PSYCHE OS encrypted-storage contract:
1. Runtime      — sqlcipher3 import verified
2. Build        — cipher version present and non-empty
3. License      — actual license detected, not placeholder
4. Wrong-key    — wrong passphrase → OperationalError (not silent corruption)
5. Header       — database header is encrypted (not plaintext SQLite)
6. Plaintext    — plaintext SQLite file explicitly rejected under encrypted profile
7. Integrity    — HMAC/page integrity check returns valid result
8. Backup       — backup API verified with actual encrypt/restore cycle

All 8 must pass with real evidence for the profile to be ACCEPTED.
- Empty/placeholder evidence → REJECTED
- Exception text is never treated as evidence
- Gate distinguishes UNAVAILABLE, FAILED, and VERIFIED capabilities
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import os
import secrets
import tempfile

# ---------------------------------------------------------------------------
# Gate states
# ---------------------------------------------------------------------------


class GateState(str, Enum):
    UNPROBED = "unprobed"
    PROBING = "probing"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    BLOCKED = "blocked"  # Library/dependency missing entirely
    UNAVAILABLE = "unavailable"  # Present but cannot function


# ---------------------------------------------------------------------------
# Probe results
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProbeResult:
    probe_number: int
    probe_name: str
    passed: bool
    detail: str
    evidence: str = ""
    capability_verdict: str = ""  # "verified", "failed", "unavailable", "placeholder"


@dataclass
class GateReport:
    gate_state: GateState = GateState.UNPROBED
    results: list[ProbeResult] = field(default_factory=list)
    blocker: str = ""
    real_data_gate: str = "CLOSED"

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results) if self.results else False

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    def to_dict(self) -> dict[str, object]:
        return {
            "gate_state": self.gate_state.value,
            "all_passed": self.all_passed,
            "failed_count": self.failed_count,
            "blocker": self.blocker,
            "real_data_gate": self.real_data_gate,
            "probes": [
                {
                    "number": r.probe_number,
                    "name": r.probe_name,
                    "passed": r.passed,
                    "detail": r.detail,
                    "capability_verdict": r.capability_verdict,
                }
                for r in self.results
            ],
        }


# ---------------------------------------------------------------------------
# Probe implementations
# ---------------------------------------------------------------------------


def _probe_1_runtime() -> ProbeResult:
    """Probe 1: sqlcipher3 module imports and is actually usable."""
    try:
        import sqlcipher3  # noqa: F401
        from sqlcipher3 import dbapi2

        # Verify it actually works by creating an in-memory encrypted DB
        con = dbapi2.connect(":memory:")
        con.execute("PRAGMA key = 'probe_1_test';")
        con.execute("CREATE TABLE IF NOT EXISTS _probe (x INTEGER);")
        con.commit()
        con.close()
        return ProbeResult(
            1,
            "runtime",
            True,
            "sqlcipher3 imported and functional",
            "sqlcipher3.dbapi2",
            capability_verdict="verified",
        )
    except ImportError:
        return ProbeResult(
            1,
            "runtime",
            False,
            "Cannot import sqlcipher3 — install sqlcipher3 package",
            "",
            capability_verdict="unavailable",
        )
    except Exception as exc:
        return ProbeResult(
            1,
            "runtime",
            False,
            f"sqlcipher3 imported but in-memory test failed: {exc}",
            "",
            capability_verdict="failed",
        )


def _probe_2_build() -> ProbeResult:
    """Probe 2: cipher version must match a recognized SQLCipher version pattern.

    F04 (FIX): Accept only explicit recognized version patterns
    (e.g. "3.x.y community", "4.x.y commercial"). Arbitrary non-empty,
    non-placeholder text that does not match a known SQLCipher version
    pattern is REJECTED.
    """
    import re as _re

    # Recognised SQLCipher version patterns:
    #   "X.Y.Z community"  (open-source community build)
    #   "X.Y.Z commercial" (commercial/licensed build)
    # The version may also be reported as just "X.Y.Z".
    # We require at least one numeric version component.
    _RECOGNISED_VERSION_RE = _re.compile(
        r"\b(\d+\.\d+(?:\.\d+)?)\b.*\b(community|commercial)\b",
        _re.IGNORECASE,
    )
    # Also accept bare version-only strings like "4.12.0" from PRAGMA cipher_version
    _BARE_VERSION_RE = _re.compile(r"^(\d+\.\d+(?:\.\d+)?)$")

    try:
        from sqlcipher3 import dbapi2

        con = dbapi2.connect(":memory:")
        cur = con.cursor()
        cur.execute("PRAGMA cipher_version;")
        row = cur.fetchone()
        con.close()
        version = (row[0] if row else "").strip()

        if not version:
            return ProbeResult(
                2,
                "build",
                False,
                "No cipher version returned — possible plaintext SQLite",
                "",
                capability_verdict="failed",
            )

        # F04: Must match an explicit recognised pattern
        if _RECOGNISED_VERSION_RE.search(version):
            return ProbeResult(
                2,
                "build",
                True,
                f"SQLCipher version: {version}",
                version,
                capability_verdict="verified",
            )

        if _BARE_VERSION_RE.match(version):
            return ProbeResult(
                2,
                "build",
                True,
                f"SQLCipher version: {version}",
                version,
                capability_verdict="verified",
            )

        # Arbitrary text that looks plausible but doesn't match known patterns
        return ProbeResult(
            2,
            "build",
            False,
            f"Cipher version '{version[:80]}' does not match a recognised SQLCipher version pattern",
            version[:120],
            capability_verdict="failed",
        )
    except Exception as exc:
        return ProbeResult(
            2,
            "build",
            False,
            f"Cipher version probe failed: {exc}",
            "",
            capability_verdict="unavailable",
        )


def _probe_3_license() -> ProbeResult:
    """Probe 3: License must match an explicit recognised SQLCipher licence/tier.

    F04 (FIX): Only explicit recognised patterns are accepted. Arbitrary
    non-placeholder text that does not match a known Community or Commercial
    licence works is REJECTED. The gate now recognises:
      - "community" within a SQLCipher version/licence string
      - "commercial" within a SQLCipher version/licence string
      - Specific known licence identifiers from Zetetic/Percona

    cipher_license may return None/empty on some builds — the cipher_version
    string is checked as an alternative source ONLY when it also matches an
    explicit licence-tier pattern.
    """
    import re as _re

    # Recognised licence-tier indicators — must contain "community" or
    # "commercial" AND a version-like component to be accepted via version
    _LICENCE_TIER_RE = _re.compile(r"\b(community|commercial)\b", _re.IGNORECASE)

    try:
        from sqlcipher3 import dbapi2

        con = dbapi2.connect(":memory:")
        cur = con.cursor()

        cur.execute("PRAGMA cipher_license;")
        row = cur.fetchone()
        license_info = (row[0] if row else "").strip()

        if not license_info:
            cur.execute("PRAGMA cipher_version;")
            row2 = cur.fetchone()
            version_info = (row2[0] if row2 else "").strip()
        else:
            version_info = ""

        con.close()

        # F04: Reject BOTH empty/placeholder and arbitrary-non-placeholder text
        placeholder_values = (
            "unknown",
            "none",
            "n/a",
            "not available",
            "",
            "0",
            "null",
            "(unknown)",
            "(none)",
            "[unknown]",
            "[none]",
        )

        lic_is_placeholder = license_info.lower() in placeholder_values
        ver_is_placeholder = version_info.lower() in placeholder_values

        if lic_is_placeholder and ver_is_placeholder:
            return ProbeResult(
                3,
                "license",
                False,
                "Both cipher_license and cipher_version returned empty/placeholder",
                "",
                capability_verdict="placeholder",
            )

        # F04: Require an explicit recognised licence-tier pattern
        effective = license_info if (license_info and not lic_is_placeholder) else version_info

        if not effective or len(effective) < 3:
            return ProbeResult(
                3,
                "license",
                False,
                f"License text too short to be valid: '{effective}'",
                effective,
                capability_verdict="placeholder",
            )

        # F04: Must match a recognised licence tier — "community" or "commercial"
        if _LICENCE_TIER_RE.search(effective):
            tier = "community" if "community" in effective.lower() else "commercial"
            return ProbeResult(
                3,
                "license",
                True,
                f"SQLCipher {tier} edition — acceptable for local-only synthetic F0: {effective[:80]}",
                effective,
                capability_verdict="verified",
            )

        # F04: Arbitrary text that does not match a recognised licence pattern → REJECTED
        return ProbeResult(
            3,
            "license",
            False,
            f"License text '{effective[:80]}' does not match a recognised SQLCipher licence tier — expected 'community' or 'commercial'",
            effective[:120],
            capability_verdict="failed",
        )
    except Exception as exc:
        return ProbeResult(
            3,
            "license",
            False,
            f"License probe failed: {exc}",
            "",
            capability_verdict="unavailable",
        )


def _probe_4_wrong_key() -> ProbeResult:
    """Probe 4: Wrong passphrase causes OperationalError, not silent corruption.

    FIX (F04): Must provide explicit wrong-key vs plaintext classification.
    - Wrong key: file is encrypted, wrong password → OperationalError / "file is not a database"
    - Plaintext: file is not encrypted at all, no key needed → silent success is a FAIL

    This probe creates an encrypted DB, then tests BOTH:
      a) wrong key → MUST raise (proves encryption is enforced)
      b) correct key → MUST work (proves the file is valid encrypted SQLCipher, not corrupt)
    """
    db_path = os.path.join(tempfile.gettempdir(), f"_psyche_probe4_{secrets.token_hex(4)}.db")
    try:
        from sqlcipher3 import dbapi2

        # — Phase A: Create encrypted database with key "correct" —
        con = dbapi2.connect(db_path)
        con.execute("PRAGMA key = 'correct';")
        con.execute("CREATE TABLE test (id INTEGER);")
        con.execute("INSERT INTO test VALUES (1);")
        con.commit()
        con.close()

        # — Phase B: Attempt wrong-key access — MUST fail —
        wrong_key_error_type = ""
        wrong_key_error_msg = ""
        try:
            con2 = dbapi2.connect(db_path)
            con2.execute("PRAGMA key = 'wrong';")
            cur = con2.cursor()
            cur.execute("SELECT * FROM test;")
            rows = cur.fetchall()
            con2.close()
            # Wrong key succeeded → file may not be encrypted
            return ProbeResult(
                4,
                "wrong_key",
                False,
                "Wrong key did not raise error — database may not be encrypted (plaintext_classification)",
                f"rows_returned={len(rows)}",
                capability_verdict="failed",
            )
        except Exception as exc:
            wrong_key_error_type = type(exc).__name__
            wrong_key_error_msg = str(exc)

        # Classify: must be a real database error (OperationalError, DatabaseError),
        # not some unrelated exception
        if "OperationalError" in wrong_key_error_type or "DatabaseError" in wrong_key_error_type:
            pass  # Expected — correct classification
        else:
            return ProbeResult(
                4,
                "wrong_key",
                False,
                f"Wrong-key raised unexpected error type: {wrong_key_error_type} (expected OperationalError)",
                wrong_key_error_msg[:120],
                capability_verdict="failed",
            )

        # — Phase C: Verify correct key still works —
        # This proves the file is valid encrypted SQLCipher, not just a corrupt blob
        try:
            con3 = dbapi2.connect(db_path)
            con3.execute("PRAGMA key = 'correct';")
            cur3 = con3.cursor()
            cur3.execute("SELECT * FROM test;")
            rows3 = cur3.fetchall()
            con3.close()
            if rows3 != [(1,)]:
                return ProbeResult(
                    4,
                    "wrong_key",
                    False,
                    f"Correct-key read returned unexpected data: {rows3}",
                    "",
                    capability_verdict="failed",
                )
        except Exception as exc:
            return ProbeResult(
                4,
                "wrong_key",
                False,
                f"Correct-key read failed after wrong-key attempt: {type(exc).__name__}: {exc}",
                "",
                capability_verdict="failed",
            )

        return ProbeResult(
            4,
            "wrong_key",
            True,
            f"Wrong-key correctly raises {wrong_key_error_type} (encrypted, not plaintext)",
            wrong_key_error_type,
            capability_verdict="verified",
        )
    except Exception as exc:
        return ProbeResult(
            4,
            "wrong_key",
            False,
            f"Wrong-key probe failed: {exc}",
            "",
            capability_verdict="unavailable",
        )
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass


def _probe_5_header() -> ProbeResult:
    """Probe 5: Database file header is encrypted, not plaintext SQLite."""
    db_path = os.path.join(tempfile.gettempdir(), f"_psyche_probe5_{secrets.token_hex(4)}.db")
    try:
        from sqlcipher3 import dbapi2

        con = dbapi2.connect(db_path)
        con.execute("PRAGMA key = 'probe5_test_key';")
        con.execute("CREATE TABLE t(x);")
        con.commit()
        con.close()

        with open(db_path, "rb") as f:
            header = f.read(16)

        # Plaintext SQLite header starts with b"SQLite format 3\000"
        if header.startswith(b"SQLite format 3\x00"):
            return ProbeResult(
                5,
                "header",
                False,
                "Header is plaintext SQLite — encryption NOT active",
                header.hex(),
                capability_verdict="failed",
            )
        return ProbeResult(
            5,
            "header",
            True,
            "Header is encrypted (not plaintext SQLite)",
            header.hex()[:32],
            capability_verdict="verified",
        )
    except Exception as exc:
        return ProbeResult(
            5,
            "header",
            False,
            f"Header probe failed: {exc}",
            "",
            capability_verdict="unavailable",
        )
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass


def _probe_6_plaintext_reject() -> ProbeResult:
    """Probe 6: Opening a plaintext SQLite file under an encrypted profile is rejected."""
    db_path = os.path.join(tempfile.gettempdir(), f"_psyche_probe6_{secrets.token_hex(4)}.db")
    try:
        # Create a plaintext SQLite database
        import sqlite3 as plain_sqlite

        con = plain_sqlite.connect(db_path)
        con.execute("CREATE TABLE t(x);")
        con.commit()
        con.close()

        # Now try to open it with sqlcipher3 and a key
        from sqlcipher3 import dbapi2

        con2 = dbapi2.connect(db_path)
        con2.execute("PRAGMA key = 'test_key';")
        cur = con2.cursor()

        # If a plaintext file opens and works with a key, encryption isn't enforced
        try:
            cur.execute("SELECT * FROM sqlite_master;")
            cur.fetchall()
            con2.close()
            return ProbeResult(
                6,
                "plaintext_reject",
                False,
                "Plaintext SQLite file opened under encrypted profile — gate unsafe",
                "",
                capability_verdict="failed",
            )
        except Exception:
            con2.close()
            return ProbeResult(
                6,
                "plaintext_reject",
                True,
                "Plaintext SQLite correctly rejected when encrypted profile used",
                "DatabaseError",
                capability_verdict="verified",
            )
    except Exception as exc:
        return ProbeResult(
            6,
            "plaintext_reject",
            False,
            f"Plaintext reject probe failed: {exc}",
            "",
            capability_verdict="unavailable",
        )
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass


def _probe_7_integrity() -> ProbeResult:
    """Probe 7: Keyed HMAC/page integrity check must demonstrate cipher integrity.

    F04 (FIX): Only the KEYED PRAGMA cipher_integrity_check result is accepted.
    The documented successful result is either:
      - [("ok",)] — explicit OK (SQLCipher commercial / newer builds)
      - [] — empty result set (SQLCipher 4.x community: no errors = clean)

    The following are REJECTED as insufficient to establish cipher integrity:
      - Plain SQLite integrity_check (unkeyed) — does not validate HMAC/pages
      - Any non-"ok" row result — indicates corruption
      - A generic exception/missing capability — probe is unavailable

    The probe MUST open a keyed database and receive one of the two documented
    successful results. It MUST NOT fall back to plain integrity_check.
    """
    db_path = os.path.join(tempfile.gettempdir(), f"_psyche_probe7_{secrets.token_hex(4)}.db")
    try:
        from sqlcipher3 import dbapi2

        con = dbapi2.connect(db_path)
        con.execute("PRAGMA key = 'integrity_test';")
        con.execute("CREATE TABLE t(x);")
        con.execute("INSERT INTO t VALUES (1), (2), (3);")
        con.commit()

        cur = con.cursor()

        # F04: ONLY PRAGMA cipher_integrity_check on a keyed DB is accepted
        cur.execute("PRAGMA cipher_integrity_check;")
        rows = cur.fetchall()
        con.close()

        # Two documented successful results:
        # 1. [("ok",)] — explicit OK
        # 2. [] — empty result set (no errors found, clean on SQLCipher 4.x)
        if rows:
            result = rows[0][0]
            if result == "ok":
                return ProbeResult(
                    7,
                    "integrity",
                    True,
                    "Keyed cipher_integrity_check returned explicit 'ok' — cipher page/HMAC integrity verified",
                    "ok",
                    capability_verdict="verified",
                )
            # Any non-'ok' row result = corruption detected
            return ProbeResult(
                7,
                "integrity",
                False,
                f"Keyed cipher_integrity_check returned non-'ok' result: '{result[:120]}'",
                str(result)[:120],
                capability_verdict="failed",
            )

        # Empty result set: documented successful result on SQLCipher 4.x
        # ("If no errors are found, the function returns an empty result set")
        # NOT a fallback — this is the expected, documented success mode
        return ProbeResult(
            7,
            "integrity",
            True,
            "Keyed cipher_integrity_check returned empty result set — documented clean result (no page-level errors detected)",
            "cipher_integrity_check=clean",
            capability_verdict="verified",
        )
    except Exception as exc:
        return ProbeResult(
            7,
            "integrity",
            False,
            f"Integrity probe failed: {exc}",
            "",
            capability_verdict="unavailable",
        )
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass


def _probe_8_backup() -> ProbeResult:
    """Probe 8: Real encrypted backup → restore → content round trip.

    FIX (F04): Must prove actual encrypt/export → restore/decrypt → content
    verification cycle works end-to-end. API presence alone is NOT sufficient.
    The probe:
      1. Creates an encrypted source DB with known content
      2. Exports it to a file (cipher_export or sqlite3 backup)
      3. Restores into a new encrypted DB
      4. Verifies the restored content matches exactly
    """
    src_path = os.path.join(tempfile.gettempdir(), f"_psyche_probe8a_{secrets.token_hex(4)}.db")
    dst_path = os.path.join(tempfile.gettempdir(), f"_psyche_probe8b_{secrets.token_hex(4)}.db")
    try:
        from sqlcipher3 import dbapi2

        # — Step 1: Create encrypted source with known content —
        con_src = dbapi2.connect(src_path)
        con_src.execute("PRAGMA key = 'roundtrip_key';")
        con_src.execute("CREATE TABLE t(x);")
        con_src.execute("INSERT INTO t VALUES (1), (2), (3);")
        con_src.execute("CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT);")
        con_src.execute("INSERT INTO meta VALUES ('round', 'trip'), ('version', '1.0');")
        con_src.commit()

        # Capture expected content before export
        cur_src = con_src.cursor()
        cur_src.execute("SELECT * FROM t ORDER BY x;")
        expected_t = cur_src.fetchall()
        cur_src.execute("SELECT * FROM meta ORDER BY k;")
        expected_meta = cur_src.fetchall()
        con_src.close()

        # — Step 2: Export source to a file —
        con_export = dbapi2.connect(src_path)
        con_export.execute("PRAGMA key = 'roundtrip_key';")
        try:
            # Use sqlcipher_export for an encrypted-to-encrypted copy
            con_export.execute("ATTACH DATABASE ? AS backup KEY 'roundtrip_key';", (dst_path,))
            con_export.execute("SELECT sqlcipher_export('backup');")
            con_export.execute("DETACH DATABASE backup;")
            export_method = "sqlcipher_export"
        except Exception:
            # Fallback: use sqlite3 backup API (still encrypted since dst uses same key)
            try:
                con_dst = dbapi2.connect(dst_path)
                con_dst.execute("PRAGMA key = 'roundtrip_key';")
                con_export.backup(con_dst)
                con_dst.close()
                export_method = "sqlite3_backup"
            except Exception as backup_exc:
                con_export.close()
                return ProbeResult(
                    8,
                    "backup",
                    False,
                    f"Both sqlcipher_export and sqlite3_backup failed: {backup_exc}",
                    "",
                    capability_verdict="unavailable",
                )
        con_export.close()

        # — Step 3: Verify exported file exists and has content —
        if not os.path.exists(dst_path):
            return ProbeResult(
                8,
                "backup",
                False,
                "Export completed but destination file does not exist",
                "",
                capability_verdict="failed",
            )
        dst_size = os.path.getsize(dst_path)
        if dst_size == 0:
            return ProbeResult(
                8,
                "backup",
                False,
                "Export produced empty file — backup is non-functional",
                "",
                capability_verdict="failed",
            )

        # — Step 4: Open the restored database and verify content —
        con_restore = dbapi2.connect(dst_path)
        con_restore.execute("PRAGMA key = 'roundtrip_key';")
        cur_r = con_restore.cursor()

        # Check schema exists
        cur_r.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [row[0] for row in cur_r.fetchall()]

        if "t" not in tables:
            con_restore.close()
            return ProbeResult(
                8,
                "backup",
                False,
                f"Restored DB missing table 't'. Found: {tables}",
                "",
                capability_verdict="failed",
            )
        if "meta" not in tables:
            con_restore.close()
            return ProbeResult(
                8,
                "backup",
                False,
                f"Restored DB missing table 'meta'. Found: {tables}",
                "",
                capability_verdict="failed",
            )

        # Verify row content
        cur_r.execute("SELECT * FROM t ORDER BY x;")
        restored_t = cur_r.fetchall()
        cur_r.execute("SELECT * FROM meta ORDER BY k;")
        restored_meta = cur_r.fetchall()
        con_restore.close()

        if restored_t != expected_t:
            return ProbeResult(
                8,
                "backup",
                False,
                f"Content mismatch in table 't': expected {expected_t}, got {restored_t}",
                f"expected={expected_t} restored={restored_t}",
                capability_verdict="failed",
            )
        if restored_meta != expected_meta:
            return ProbeResult(
                8,
                "backup",
                False,
                f"Content mismatch in table 'meta': expected {expected_meta}, got {restored_meta}",
                f"expected={expected_meta} restored={restored_meta}",
                capability_verdict="failed",
            )

        return ProbeResult(
            8,
            "backup",
            True,
            f"Encrypted backup → restore → content round trip verified ({export_method}, {dst_size} bytes)",
            f"method={export_method} size={dst_size} tables={len(tables)} rows_t={len(restored_t)} rows_meta={len(restored_meta)}",
            capability_verdict="verified",
        )
    except Exception as exc:
        return ProbeResult(
            8,
            "backup",
            False,
            f"Backup round-trip probe failed: {type(exc).__name__}: {exc}",
            "",
            capability_verdict="unavailable",
        )
    finally:
        for p in (src_path, dst_path):
            try:
                os.unlink(p)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Gate runner
# ---------------------------------------------------------------------------

ALL_PROBES = [
    _probe_1_runtime,
    _probe_2_build,
    _probe_3_license,
    _probe_4_wrong_key,
    _probe_5_header,
    _probe_6_plaintext_reject,
    _probe_7_integrity,
    _probe_8_backup,
]


def run_gate() -> GateReport:
    """Run all 8 SQLCipher probes. Returns a GateReport.

    Verdict logic:
    - All 8 pass with verified evidence → ACCEPTED
    - Probe 1 fails (import missing) → BLOCKED
    - Any probe returns 'unavailable' → UNAVAILABLE
    - Any probe returns 'failed' or 'placeholder' → REJECTED
    """
    report = GateReport(gate_state=GateState.PROBING)

    for probe_fn in ALL_PROBES:
        try:
            result = probe_fn()
        except Exception as exc:
            result = ProbeResult(
                probe_number=0,
                probe_name=probe_fn.__name__,
                passed=False,
                detail=f"Probe crashed: {exc}",
                evidence="",
                capability_verdict="failed",
            )
        report.results.append(result)

        if not result.passed:
            reason = f"Probe {result.probe_number} ({result.probe_name}): {result.detail}"
            if report.blocker:
                report.blocker += "; " + reason
            else:
                report.blocker = reason

    # Determine final gate state
    if report.all_passed:
        report.gate_state = GateState.ACCEPTED
    elif any("Cannot import" in r.detail for r in report.results):
        report.gate_state = GateState.BLOCKED
    elif any(r.capability_verdict == "unavailable" for r in report.results):
        report.gate_state = GateState.UNAVAILABLE
    else:
        report.gate_state = GateState.REJECTED

    return report


def gate_accepted() -> bool:
    """Quick check: run probes and return True if accepted."""
    report = run_gate()
    return report.gate_state == GateState.ACCEPTED


def gate_report_json() -> str:
    """Run probes and return JSON report."""
    import json

    return json.dumps(run_gate().to_dict(), indent=2)
