from __future__ import annotations

import sqlite3

from psyche_os.storage.migrations import Migrator


def test_v6_database_upgrades_additively_to_v7() -> None:
    connection = sqlite3.connect(":memory:")
    Migrator(connection).apply(6)
    report = Migrator(connection).apply(7)
    assert report.success is True
    assert connection.execute("SELECT name FROM sqlite_master WHERE name='reflection_exploration_snapshots'").fetchone()
    assert connection.execute("SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1").fetchone()[0] == 7
