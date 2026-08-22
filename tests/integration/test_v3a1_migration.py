from __future__ import annotations

import sqlite3

from psyche_os.storage.migrations import MIGRATIONS, Migrator
from psyche_os.storage.v3a1_exploration_schema import V7_MIGRATION_CHECKSUM
from psyche_os.storage.v3a1_exploration_v8_schema import V8_INVENTORY, V8_MIGRATION_CHECKSUM
from psyche_os.storage.v3a3_action_schema import V9_ADDED_TABLES

FROZEN_V7_CHECKSUM = "65929a2eff2adfdf02a21fc2d8130fe45eff55410d7a6904e055e12b77fc0d31"
FROZEN_V8_CHECKSUM = "41974dc9aae1d44f8ca38c8162ae2e1120b14f73ca291b5819391ab8da97d25e"


def test_v7_migration_checksum_is_frozen_at_published_candidate() -> None:
    assert V7_MIGRATION_CHECKSUM == FROZEN_V7_CHECKSUM
    assert MIGRATIONS[7].checksum == FROZEN_V7_CHECKSUM


def test_v8_migration_checksum_is_frozen_before_v9() -> None:
    assert V8_MIGRATION_CHECKSUM == FROZEN_V8_CHECKSUM
    assert MIGRATIONS[8].checksum == FROZEN_V8_CHECKSUM


def test_v6_database_upgrades_additively_to_v8() -> None:
    connection = sqlite3.connect(":memory:")
    Migrator(connection).apply(6)
    report = Migrator(connection).apply(8)
    assert report.success is True
    tables = {
        row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert set(V8_INVENTORY) <= tables
    assert connection.execute(
        "SELECT name FROM sqlite_master WHERE name='idx_reflection_formulations_current'"
    ).fetchone()
    assert (
        connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1"
        ).fetchone()[0]
        == 8
    )
    assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_v6_to_v9_chain_and_existing_v8_upgrade_are_additive() -> None:
    connection = sqlite3.connect(":memory:")
    assert Migrator(connection).apply(6).success
    assert Migrator(connection).apply(9).success
    tables = {
        row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert set(V8_INVENTORY + V9_ADDED_TABLES) <= tables
    assert Migrator(connection).current_version() == 9
    assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert Migrator(connection).verify().success


def test_existing_original_v7_upgrades_to_v8_without_checksum_mismatch() -> None:
    connection = sqlite3.connect(":memory:")
    assert Migrator(connection).apply(7).success
    assert Migrator(connection).verify().success
    report = Migrator(connection).apply(8)
    assert report.success
    assert report.applied == [8]
    assert Migrator(connection).current_version() == 8


def test_v8_preserves_v7_rows_and_maps_accepted_formulation_to_current() -> None:
    connection = sqlite3.connect(":memory:")
    assert Migrator(connection).apply(7).success
    connection.execute(
        "INSERT INTO reflection_sessions VALUES(?,?,?,?,?,?,?,?,?)",
        (
            "session",
            "Synthetic",
            "ACTIVE",
            "ENCRYPTED_LOCAL",
            "synthetic_only",
            "now",
            "now",
            None,
            1,
        ),
    )
    connection.execute(
        "INSERT INTO reflection_turns VALUES(?,?,?,?,?,?)",
        ("turn", "session", 1, "USER", "now", "SYNTHETIC: source"),
    )
    connection.execute(
        "INSERT INTO reflection_explorations VALUES(?,?,?,?)", ("session", "snapshot", "now", "now")
    )
    connection.execute(
        "INSERT INTO reflection_exploration_snapshots VALUES(?,?,?,?,?)",
        ("snapshot", "session", 1, "v7", "now"),
    )
    connection.execute(
        "INSERT INTO reflection_formulations VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (
            "formulation",
            "session",
            1,
            None,
            "snapshot",
            "ACCEPTED",
            "Synthetic proposal",
            None,
            "v7",
            "now",
            "now",
        ),
    )
    connection.commit()
    assert Migrator(connection).apply(8).success
    assert (
        connection.execute(
            "SELECT status FROM reflection_formulations WHERE formulation_id='formulation'"
        ).fetchone()[0]
        == "CURRENT"
    )
    assert (
        connection.execute(
            "SELECT COUNT(*) FROM reflection_turns WHERE session_id='session'"
        ).fetchone()[0]
        == 1
    )
    assert (
        connection.execute(
            "SELECT COUNT(*) FROM reflection_exploration_snapshots WHERE session_id='session'"
        ).fetchone()[0]
        == 1
    )
    assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_v8_fails_closed_when_legacy_session_has_multiple_accepted_formulations() -> None:
    connection = sqlite3.connect(":memory:")
    assert Migrator(connection).apply(7).success
    connection.execute(
        "INSERT INTO reflection_sessions VALUES(?,?,?,?,?,?,?,?,?)",
        (
            "session",
            "Synthetic",
            "ACTIVE",
            "ENCRYPTED_LOCAL",
            "synthetic_only",
            "now",
            "now",
            None,
            1,
        ),
    )
    connection.execute(
        "INSERT INTO reflection_exploration_snapshots VALUES(?,?,?,?,?)",
        ("snapshot", "session", 1, "v7", "now"),
    )
    for version in (1, 2):
        connection.execute(
            "INSERT INTO reflection_formulations VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                f"formulation-{version}",
                "session",
                version,
                None,
                "snapshot",
                "ACCEPTED",
                "Synthetic proposal",
                None,
                "v7",
                "now",
                "now",
            ),
        )
    connection.commit()
    report = Migrator(connection).apply(8)
    assert not report.success
    assert Migrator(connection).current_version() == 7
