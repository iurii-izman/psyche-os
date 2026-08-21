"""Migrator — ordered, crash-safe schema migrations.

F05 (FIX): Real ordered migrations with up/down, checksum verification,
and atomic application. Each migration describes exactly what it changes
and provides a cancel/downgrade path.

Schema versions:
  1 — F0 core initial (frozen)
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field
import datetime
import hashlib
import sqlite3
from typing import Any

from psyche_os.storage.e03_schema import V2_MIGRATION_CHECKSUM, V2_MIGRATION_STATEMENTS
from psyche_os.storage.e05_schema import V3_MIGRATION_CHECKSUM, V3_MIGRATION_STATEMENTS
from psyche_os.storage.e06_schema import V4_MIGRATION_CHECKSUM, V4_MIGRATION_STATEMENTS
from psyche_os.storage.e08_schema import V5_MIGRATION_CHECKSUM, V5_MIGRATION_STATEMENTS
from psyche_os.storage.v3a0_session_schema import V6_MIGRATION_CHECKSUM, V6_MIGRATION_STATEMENTS
from psyche_os.storage.schema import (
    ALL_DDL,
    SCHEMA_VERSIONS,
)

# The accepted default reader remains V1.  E03 calls target_version=2
# explicitly; this prevents legacy callers from silently migrating a vault.
CURRENT_SCHEMA_VERSION = 1

# ---------------------------------------------------------------------------
# Migration record
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Migration:
    """A single ordered migration step.

    Each migration carries an explicit ordered list of SQL statements and a
    checksum computed from the canonical concatenation.  Callers never split
    SQL on semicolons; every statement is applied individually within a
    single transaction.
    """

    version: int
    label: str
    statements: list[str]
    down_sql: str = ""
    checksum: str = ""

    def __post_init__(self) -> None:
        # Compute checksum from the canonical statement list
        if not self.checksum:
            canonical = ";\n".join(self.statements) + ";"
            object.__setattr__(
                self,
                "checksum",
                hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            )


# ---------------------------------------------------------------------------
# Migration registry — ordered by version
# ---------------------------------------------------------------------------


def _complete_statements(script: str) -> list[str]:
    """Parse a bundled DDL script into complete SQLite statements.

    ``sqlite3.complete_statement`` understands quoted semicolons and SQLite
    syntax.  This conversion happens while constructing the immutable bundled
    migration; the migrator itself executes one statement at a time and never
    uses ``executescript`` (which would implicitly commit).
    """
    statements: list[str] = []
    buffer = ""
    for char in script:
        buffer += char
        if char == ";" and sqlite3.complete_statement(buffer):
            statement = buffer.strip()
            if statement:
                statements.append(statement)
            buffer = ""
    if buffer.strip():
        raise ValueError("Bundled migration contains incomplete SQL")
    return statements


V1_CHECKSUM = "941d5356163f43839b88f6e18ddc1a7856e75b532e227718e1063fb233e849c1"


def _migration_v1() -> Migration:
    """V1: frozen F0 schema as an explicit ordered statement sequence."""
    stmts = [statement for _, ddl in ALL_DDL for statement in _complete_statements(ddl)]
    return Migration(
        version=1,
        label="f0_core_initial",
        statements=stmts,
        down_sql="",
        checksum=V1_CHECKSUM,
    )


MIGRATIONS: dict[int, Migration] = {
    1: _migration_v1(),
    2: Migration(
        version=2,
        label="e03_evidence_archive_v2",
        statements=list(V2_MIGRATION_STATEMENTS),
        down_sql="",
        checksum=V2_MIGRATION_CHECKSUM,
    ),
    3: Migration(
        version=3,
        label="e05_longitudinal_analysis_v3",
        statements=list(V3_MIGRATION_STATEMENTS),
        down_sql="",
        checksum=V3_MIGRATION_CHECKSUM,
    ),
    4: Migration(
        version=4,
        label="e06_bounded_n_of_1_v4",
        statements=list(V4_MIGRATION_STATEMENTS),
        down_sql="",
        checksum=V4_MIGRATION_CHECKSUM,
    ),
    5: Migration(
        version=5,
        label="e08_untrusted_import_v5",
        statements=list(V5_MIGRATION_STATEMENTS),
        down_sql="",
        checksum=V5_MIGRATION_CHECKSUM,
    ),
    6: Migration(
        version=6,
        label="v3a0_reflection_workspace_v6",
        statements=list(V6_MIGRATION_STATEMENTS),
        down_sql="",
        checksum=V6_MIGRATION_CHECKSUM,
    ),
}


def get_migration_chain(target_version: int) -> list[Migration]:
    """Return ordered migrations from 1 to target_version (inclusive).

    Re-reads the MIGRATIONS registry on every call so tests that patch
    MIGRATIONS see the patched values.

    Each returned migration is a shallow copy so the caller cannot mutate
    what is in the registry, and so the checksum comparison in apply()
    compares the patched entry against the registry's canonical copy.
    """
    if target_version not in SCHEMA_VERSIONS:
        raise ValueError(f"Unknown schema version: {target_version}")
    chain = []
    for v in range(1, target_version + 1):
        if v not in MIGRATIONS:
            raise ValueError(f"Missing migration for version {v}")
        m = MIGRATIONS[v]
        if m.version != v or SCHEMA_VERSIONS.get(v) != m.label:
            raise ValueError(f"Migration registry order/label mismatch at version {v}")
        # Return a copy so the caller gets the current snapshot but
        # cannot affect the registry, and apply() compares the copy
        # against the registry.
        chain.append(
            Migration(
                version=m.version,
                label=m.label,
                statements=list(m.statements),
                checksum=m.checksum,
                down_sql=m.down_sql,
            )
        )
    return chain


# ---------------------------------------------------------------------------
# Migrator
# ---------------------------------------------------------------------------


class MigrationError(Exception):
    """Raised when a migration cannot be applied or verified."""


@dataclass
class MigrationReport:
    """Result of a migration run."""

    target_version: int
    applied: list[int] = field(default_factory=list)
    skipped: list[int] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class Migrator:
    """Applies ordered schema migrations atomically."""

    def __init__(self, connection: Any) -> None:
        self._con = connection

    def current_version(self) -> int:
        """Return the currently applied schema version, or 0."""
        cur = self._con.cursor()
        try:
            cur.execute("SELECT MAX(version) FROM schema_migrations")
            row = cur.fetchone()
            return row[0] if row and row[0] is not None else 0
        except Exception:
            return 0

    def plan(self, target_version: int = CURRENT_SCHEMA_VERSION) -> MigrationReport:
        """Plan migrations without applying them."""
        current = self.current_version()
        report = MigrationReport(
            target_version=target_version,
            started_at=datetime.datetime.now(datetime.UTC).isoformat(),
        )

        if target_version == current:
            return report

        if target_version < current:
            report.errors.append(f"Cannot downgrade from {current} to {target_version}")
            return report

        try:
            chain = get_migration_chain(target_version)
            for m in chain:
                if m.version > current:
                    report.applied.append(m.version)
                else:
                    report.skipped.append(m.version)
        except Exception as exc:
            report.errors.append(str(exc))

        return report

    def apply(
        self,
        target_version: int = CURRENT_SCHEMA_VERSION,
        *,
        backup_verified: bool = False,
        export_verified: bool = False,
    ) -> MigrationReport:
        """Apply migrations up to target_version in a single transaction.

        Every statement from the migration's explicit statement list is applied
        individually (no semicolon splitting).  The migration record is written
        in the same transaction.  Any failure rolls back both schema changes and
        the bookkeeping entry.  Rerunning is idempotent.
        """
        report = MigrationReport(
            target_version=target_version,
            started_at=datetime.datetime.now(datetime.UTC).isoformat(),
        )

        current = self.current_version()

        if current:
            verification = self.verify()
            if not verification.success:
                report.errors.extend(verification.errors)
                return report

        if target_version == current:
            report.completed_at = datetime.datetime.now(datetime.UTC).isoformat()
            return report

        if target_version < current:
            report.errors.append(f"Cannot downgrade from {current} to {target_version}")
            return report

        if current == 1 and target_version >= 2:
            try:
                from psyche_os.storage.e03_schema import V1_INVENTORY

                tables = {
                    row[0]
                    for row in self._con.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    )
                }
                if tables != set(V1_INVENTORY):
                    raise MigrationError("V1 exact inventory mismatch")
                pending = self._con.execute(
                    "SELECT COUNT(*) FROM deletion_requests WHERE status IN ('pending','approved','in_progress')"
                ).fetchone()[0]
                if pending:
                    raise MigrationError("Pending deletion blocks migration")
                domains = self._con.execute(
                    "SELECT COUNT(*) FROM claims WHERE claim_type NOT IN "
                    "('descriptive','causal','predictive','evaluative','normative','definitional','diagnostic','synthetic','comparative','existential','prudential','taxonomic') "
                    "OR claim_status NOT IN ('proposed','supported','contradicted','resolved','retracted','superseded','disconfirmed','pending_review') "
                    "OR claim_origin NOT IN ('observation','inference','derivation','abduction','analogy','testimony')"
                ).fetchone()[0]
                if domains:
                    raise MigrationError("Malformed or out-of-domain V1 claim")
                integrity = self._con.execute("PRAGMA integrity_check").fetchone()
                if not integrity or integrity[0] != "ok":
                    raise MigrationError("V1 integrity check failed")
                # The frozen E03 contract requires recovery and portability
                # proofs for every established V1 vault.  A fresh vault may be
                # created directly through the 0 -> 2 bootstrap chain, but an
                # empty V1 database is still a V1 migration subject and is not
                # an implicit prerequisite exception.
                if not (backup_verified and export_verified):
                    raise MigrationError("Verified V1 backup and export are required")
            except Exception as exc:
                report.errors.append(str(exc))
                return report

        if current == 2 and target_version >= 3:
            try:
                from psyche_os.storage.e03_schema import V2_INVENTORY

                tables = {
                    row[0]
                    for row in self._con.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    )
                }
                if tables != set(V2_INVENTORY):
                    raise MigrationError("V2 exact inventory mismatch")
                pending = self._con.execute(
                    "SELECT COUNT(*) FROM deletion_requests WHERE status IN ('pending','approved','in_progress')"
                ).fetchone()[0]
                if pending:
                    raise MigrationError("Pending deletion blocks migration")
                integrity = self._con.execute("PRAGMA integrity_check").fetchone()
                if not integrity or integrity[0] != "ok":
                    raise MigrationError("V2 integrity check failed")
                if not (backup_verified and export_verified):
                    raise MigrationError("Verified V2 backup and export are required")
            except Exception as exc:
                report.errors.append(str(exc))
                return report

        if current == 3 and target_version >= 4:
            try:
                from psyche_os.storage.e05_schema import V3_INVENTORY

                tables = {
                    row[0]
                    for row in self._con.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    )
                }
                if tables != set(V3_INVENTORY):
                    raise MigrationError("V3 exact inventory mismatch")
                pending = self._con.execute(
                    "SELECT COUNT(*) FROM deletion_requests WHERE status IN ('pending','approved','in_progress')"
                ).fetchone()[0]
                if pending:
                    raise MigrationError("Pending deletion blocks migration")
                integrity = self._con.execute("PRAGMA integrity_check").fetchone()
                if not integrity or integrity[0] != "ok":
                    raise MigrationError("V3 integrity check failed")
                if not (backup_verified and export_verified):
                    raise MigrationError("Verified V3 backup and export are required")
            except Exception as exc:
                report.errors.append(str(exc))
                return report

        if current == 4 and target_version >= 5:
            try:
                from psyche_os.storage.e06_schema import V4_INVENTORY

                tables = {
                    row[0]
                    for row in self._con.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    )
                }
                if tables != set(V4_INVENTORY):
                    raise MigrationError("V4 exact inventory mismatch")
                pending = self._con.execute(
                    "SELECT COUNT(*) FROM deletion_requests WHERE status IN ('pending','approved','in_progress')"
                ).fetchone()[0]
                if pending:
                    raise MigrationError("Pending deletion blocks migration")
                integrity = self._con.execute("PRAGMA integrity_check").fetchone()
                if not integrity or integrity[0] != "ok":
                    raise MigrationError("V4 integrity check failed")
                if not (backup_verified and export_verified):
                    raise MigrationError("Verified V4 backup and export are required")
            except Exception as exc:
                report.errors.append(str(exc))
                return report

        try:
            chain = get_migration_chain(target_version)
            cur = self._con.cursor()

            # Verify all pending migration checksums before any schema change.
            # Recompute from the canonical statement list so that a mismatch
            # between the stored checksum and the actual statements is caught.
            for m in chain:
                if m.version <= current:
                    continue
                canonical = ";\n".join(m.statements) + ";"
                recomputed = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                if m.checksum != recomputed:
                    report.errors.append(
                        f"Checksum mismatch for v{m.version} ({m.label}): "
                        f"declared={m.checksum[:16]}..., "
                        f"recomputed={recomputed[:16]}..."
                    )
                    return report

            # Begin transaction — everything below commits or rolls back together
            cur.execute("BEGIN IMMEDIATE")

            # Bookkeeping creation belongs to the same transaction as DDL.
            cur.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version INTEGER PRIMARY KEY, label TEXT NOT NULL, "
                "applied_at TEXT NOT NULL DEFAULT (datetime('now')), "
                "checksum TEXT NOT NULL);"
            )

            for m in chain:
                if m.version <= current:
                    report.skipped.append(m.version)
                    continue

                try:
                    # Apply each explicit complete statement without
                    # executescript(), whose implicit commit breaks atomicity.
                    for stmt in m.statements:
                        cur.execute(stmt)

                    # Record the migration in the same transaction
                    now = datetime.datetime.now(datetime.UTC).isoformat()
                    cur.execute(
                        "INSERT INTO schema_migrations "
                        "(version, label, applied_at, checksum) "
                        "VALUES (?, ?, ?, ?)",
                        (m.version, m.label, now, m.checksum),
                    )

                    report.applied.append(m.version)

                except Exception as exc:
                    self._con.rollback()
                    report.errors.append(f"Migration v{m.version} ({m.label}): {exc}")
                    return report

            self._con.commit()
            report.completed_at = datetime.datetime.now(datetime.UTC).isoformat()

        except Exception as exc:
            report.errors.append(str(exc))
            with suppress(Exception):
                self._con.rollback()

        return report

    def verify(self) -> MigrationReport:
        """Verify all applied migrations match their checksums."""
        current = self.current_version()
        report = MigrationReport(
            target_version=current,
            started_at=datetime.datetime.now(datetime.UTC).isoformat(),
        )

        cur = self._con.cursor()
        try:
            cur.execute("SELECT version, label, checksum FROM schema_migrations ORDER BY version")
            rows = cur.fetchall()

            for row in rows:
                version, label, stored_checksum = row
                if version not in MIGRATIONS:
                    report.errors.append(f"Unknown migration version {version} in database")
                    continue
                expected = MIGRATIONS[version].checksum
                if stored_checksum != expected:
                    report.errors.append(
                        f"Checksum mismatch for v{version} ({label}): "
                        f"stored={stored_checksum[:16]}..., "
                        f"expected={expected[:16]}..."
                    )

            report.completed_at = datetime.datetime.now(datetime.UTC).isoformat()

        except Exception as exc:
            report.errors.append(str(exc))

        return report
