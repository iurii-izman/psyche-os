from __future__ import annotations

import sqlite3

from psyche_os.personal_mode.package_format import (
    PERSONAL_V11_FORMAT_VERSION,
    create_personal_package,
    restore_personal_package,
    verify_personal_package,
)
from psyche_os.personal_mode.schema import initialize_personal_v10, initialize_personal_v11


def test_v10_migrates_additively_to_v11() -> None:
    connection = sqlite3.connect(":memory:")
    initialize_personal_v10(connection)
    connection.execute("INSERT INTO reflection_sessions VALUES('s','Synthetic','ACTIVE','ENCRYPTED_LOCAL','real_personal','now','now',NULL,0)")
    initialize_personal_v11(connection)
    assert connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall() == [(10,), (11,)]
    assert connection.execute("SELECT title FROM reflection_sessions").fetchone() == ("Synthetic",)
    assert connection.execute("SELECT name FROM sqlite_master WHERE name='reflection_ai_provenance'").fetchone()


def test_v11_package_contains_provenance_and_round_trips() -> None:
    source, restored = sqlite3.connect(":memory:"), sqlite3.connect(":memory:")
    initialize_personal_v11(source)
    package = create_personal_package(source)
    assert package["format_version"] == PERSONAL_V11_FORMAT_VERSION
    assert "reflection_ai_provenance" in package["inventory"]
    assert verify_personal_package(package)
    restore_personal_package(package, restored)
    assert restored.execute("SELECT MAX(version) FROM schema_migrations").fetchone() == (11,)
