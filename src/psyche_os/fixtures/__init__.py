"""Package-owned bundled fixture loader — the only authorized content write path.

The loader reads only built-in package resources, validates the manifest,
and invokes the storage write path with a verified FixtureAuthority.
No public object exposes an authority or its token string.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Table-level allowlist — only the bundled fixture's declared tables
# ---------------------------------------------------------------------------

_ALLOWED_FIXTURE_TABLES = frozenset(
    {"actors", "subjects", "source_artifacts", "observations", "assertions", "claims", "data_policies"}
)

# Known bundled fixture packs — exact path relative to the psyche_os package
_KNOWN_PACKS: dict[str, str] = {
    "f0_smoke": "f0_smoke.json",
}


class FixtureLoadError(Exception):
    """Raised when a fixture pack cannot be loaded or validated."""


def _validate_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate fixture manifest and return the verified rows.

    Rejects:
    - missing or falsy ``synthetic_fixture``
    - unknown/unlisted pack ID
    - missing or empty manifest version
    - mismatch between the declared digest and the canonical row content
    - missing or empty ``rows``
    """
    if not payload.get("synthetic_fixture", False):
        raise FixtureLoadError("Fixture manifest is not marked synthetic_fixture=true")

    pack_id = payload.get("fixture_pack_id", "")
    if not pack_id or pack_id not in _KNOWN_PACKS:
        raise FixtureLoadError(f"Unknown fixture pack: {pack_id!r}")

    if payload.get("manifest_version") != "1.0.0":
        raise FixtureLoadError("Unsupported fixture manifest_version")

    expected_schema_version = 1 if pack_id == "f0_smoke" else 2
    if payload.get("schema_version") != expected_schema_version:
        raise FixtureLoadError("Fixture schema_version does not match the current schema")

    rows = payload.get("rows")
    if not rows or not isinstance(rows, dict):
        raise FixtureLoadError("Fixture manifest has no rows — nothing to load")

    tables = payload.get("tables")
    if (
        not isinstance(tables, list)
        or len(tables) != len(set(tables))
        or set(tables) != set(rows)
        or not set(tables) <= _ALLOWED_FIXTURE_TABLES
    ):
        raise FixtureLoadError("Fixture table manifest is invalid or inconsistent")
    if any(
        not isinstance(table_rows, list)
        or any(not isinstance(row, dict) for row in table_rows)
        for table_rows in rows.values()
    ):
        raise FixtureLoadError("Fixture rows must be arrays of objects")

    declared_digest = payload.get("digest", "")
    canonical_rows = json.dumps(rows, sort_keys=True, ensure_ascii=False)
    actual_digest = hashlib.sha256(canonical_rows.encode()).hexdigest()
    if declared_digest != actual_digest:
        raise FixtureLoadError(
            f"Fixture digest mismatch for {pack_id!r}: "
            f"declared={declared_digest[:16]}..., actual={actual_digest[:16]}..."
        )

    return rows


def load_fixture_rows(pack_id: str) -> dict[str, list[dict[str, Any]]]:
    """Load and validate a bundled synthetic fixture pack.

    Returns the validated ``rows`` dict keyed by table name.  No
    FixtureAuthority, capability, or token is returned to the caller.

    This is the ONLY entry point for content writes in F0.  External
    files, user paths, and caller-created JSON are never accepted.
    """
    if pack_id not in _KNOWN_PACKS:
        raise FixtureLoadError(f"Unknown fixture pack: {pack_id!r}")

    resource_name = _KNOWN_PACKS[pack_id]
    fixture_dir = Path(__file__).resolve().parent
    fixture_path = fixture_dir / resource_name

    if not fixture_path.exists():
        raise FixtureLoadError(f"Bundled fixture not found: {resource_name}")

    raw = fixture_path.read_text(encoding="utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FixtureLoadError(f"Fixture JSON is invalid: {exc}")

    return _validate_manifest(payload)


def write_fixture_to_vault(
    connection: Any,
    pack_id: str,
    vault_id: Any,
) -> int:
    """Load a bundled fixture and write its rows into the vault through the
    authorized UoW path.

    Returns the number of rows written.

    This function is the sole public entry point for synthetic content
    writes in F0.  It creates a UnitOfWorkManager, supplies the validated
    FixtureAuthority, and commits atomically.
    """
    rows_by_table = load_fixture_rows(pack_id)

    from psyche_os.application.ports import FixtureAuthority
    from psyche_os.domain.ids import RecordId
    from psyche_os.storage.uow import UnitOfWorkManager

    # Mint authority bound to this exact fixture pack and digest
    canonical = json.dumps(rows_by_table, sort_keys=True, ensure_ascii=False)
    auth = FixtureAuthority._mint(pack_id, hashlib.sha256(canonical.encode()).hexdigest())

    manager = UnitOfWorkManager(connection, _authority=auth)

    total_written = 0
    with manager.begin(actor_id="fixture-loader", purpose="initial") as uow:
        id_columns = {
            "actors": "actor_id",
            "subjects": "subject_id",
            "source_artifacts": "artifact_id",
            "observations": "observation_id",
            "assertions": "assertion_id",
            "claims": "claim_id",
            "data_policies": "policy_id",
        }
        for table, rows in rows_by_table.items():
            if table not in _ALLOWED_FIXTURE_TABLES:
                raise FixtureLoadError(
                    f"Table {table!r} is not in the fixture table allowlist"
                )
            for row in rows:
                uow.add_operation(
                    table=table,
                    record_id=RecordId(row[id_columns[table]]),
                    data=dict(row),
                )
                total_written += 1

    return total_written
