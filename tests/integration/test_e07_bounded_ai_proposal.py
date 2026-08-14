from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from psyche_os.adapters.e07_provider import (
    ScriptedOfflineReflectionProvider,
    SQLiteCanonicalRecordReader,
)
from psyche_os.application.e03_archive import E03ArchiveService
from psyche_os.application.e07_bounded_ai import (
    PURPOSE,
    BoundedAIProposalService,
    E07BoundaryError,
    E07ErrorCode,
    ProviderRegistry,
    ProviderRegistryEntry,
)
from psyche_os.domain.ai_proposal import EvidenceRole, ProviderIdentity

NOW = dt.datetime(2045, 2, 3, 10, tzinfo=dt.UTC)
IDENTITY = ProviderIdentity("offline-scripted", "orbit-reflection-1.0.0", "cfg-sha256:abc")
SELECTED = (
    ("assertion-lamp", EvidenceRole.SUPPORTING),
    ("assertion-counter", EvidenceRole.COUNTEREVIDENCE),
    ("unknown-lamp", EvidenceRole.UNKNOWN),
)
FIXTURE_PATH = Path(__file__).parents[2] / "src" / "psyche_os" / "fixtures" / "e07_orbit_console_v1.json"


def _database_digest(connection: sqlite3.Connection) -> str:
    return hashlib.sha256("\n".join(connection.iterdump()).encode()).hexdigest()


def _insert_policy(
    connection: sqlite3.Connection,
    *,
    policy_id: str,
    target_record_id: str,
    cloud_policy: str = "ask_each_time",
) -> None:
    timestamp = NOW.isoformat()
    connection.execute(
        "INSERT INTO data_policies("
        "record_id,policy_id,version_id,previous_version_id,target_record_id,sensitivity,"
        "processing_location,cloud_policy,purpose,purpose_expiry,third_party_scope,"
        "retention_policy_id,retention_review,export_rule,export_audience,lineage_rule,"
        "tx_from,tx_to,is_active,created_at,closure_marker) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            f"record-{policy_id}",
            policy_id,
            f"{policy_id}-v1",
            "",
            target_record_id,
            "sensitive",
            "approved_cloud",
            cloud_policy,
            PURPOSE,
            (NOW + dt.timedelta(days=1)).isoformat(),
            "none",
            "ephemeral-e07",
            (NOW + dt.timedelta(days=1)).isoformat(),
            "block",
            "e07-offline-evaluation",
            "most_restrictive_parent",
            timestamp,
            None,
            1,
            timestamp,
            "",
        ),
    )


def _fixture_connection() -> tuple[sqlite3.Connection, E03ArchiveService]:
    connection = sqlite3.connect(":memory:")
    archive = E03ArchiveService(connection)
    archive.operate("CAPTURE_LAMP_REPORT", "reported_exact", "e07-capture-lamp")
    archive.operate("CAPTURE_COUNTERREPORT", "reported_exact", "e07-capture-counter")
    archive.operate("ASSEMBLE_EPISTEMIC_SET", "descriptive_proposed", "e07-assemble")
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    content = {item["record_id"]: item["content"] for item in fixture["records"]}
    connection.execute(
        "UPDATE assertions SET object_value=? WHERE record_id='assertion-lamp' AND is_active=1",
        (content["assertion-lamp"],),
    )
    connection.execute(
        "UPDATE assertions SET object_value=? WHERE record_id='assertion-counter' AND is_active=1",
        (content["assertion-counter"],),
    )
    connection.execute(
        "UPDATE unknowns SET question=? WHERE record_id='unknown-lamp' AND is_active=1",
        (content["unknown-lamp"],),
    )
    for record_id, _ in SELECTED:
        _insert_policy(connection, policy_id=f"policy-{record_id}", target_record_id=record_id)
    connection.commit()
    return connection, archive


def _service(
    connection: sqlite3.Connection,
    *,
    provider: ScriptedOfflineReflectionProvider | None = None,
) -> tuple[BoundedAIProposalService, SQLiteCanonicalRecordReader, ScriptedOfflineReflectionProvider, ProviderRegistry]:
    reader = SQLiteCanonicalRecordReader(connection)
    adapter = provider or ScriptedOfflineReflectionProvider()
    registry = ProviderRegistry(
        (
            ProviderRegistryEntry(
                identity=IDENTITY,
                policy_snapshot="e07-synthetic-disclosure-v1",
                knowledge_snapshot="knowledge-synthetic-v1",
                safety_policy="2.0.0-research-final",
                approved=True,
                evaluated_identity_digest=IDENTITY.digest,
            ),
        )
    )
    return BoundedAIProposalService(reader, registry, adapter), reader, adapter, registry


def _prepare(service: BoundedAIProposalService) -> tuple[object, object]:
    prepared = service.prepare(
        interaction_id="integration-e07",
        purpose=PURPOSE,
        selected=SELECTED,
        provider_identity=IDENTITY,
        cutoff=NOW,
    )
    authorization = service.authorize(
        prepared,
        authorized_at=NOW,
        expires_at=NOW + dt.timedelta(minutes=5),
        opt_in=True,
    )
    return prepared, authorization


def test_canonical_fixture_to_one_proposed_result_without_canonical_write() -> None:
    connection, archive = _fixture_connection()
    service, reader, provider, _ = _service(connection)
    before = _database_digest(connection)
    prepared, authorization = _prepare(service)
    assert reader.content_reads == 0 and provider.invocation_count == 0
    result = service.execute(prepared, authorization, now=NOW, session_id=None, turn_id=None)  # type: ignore[arg-type]
    after = _database_digest(connection)
    assert before == after
    assert provider.invocation_count == 1
    assert result.proposal.status.value == "PROPOSED"
    assert result.proposal.reflections[0].supporting_evidence_ids == ("assertion-lamp",)
    assert result.proposal.counterevidence_ids == ("assertion-counter",)
    assert result.proposal.unknowns[0].unknown_id == "unknown-lamp"
    assert result.proposal.questions[0].unknown_id == "unknown-lamp"
    assert result.envelope.retention == "ephemeral"
    assert archive.explorer()["notice"].startswith("Claims are proposals")
    dump = "\n".join(connection.iterdump())
    assert result.proposal.proposal_id not in dump
    connection.close()


@pytest.mark.parametrize("lineage", ["direct", "reconstructive"])
def test_sqlite_never_cloud_blocks_before_content_or_provider(lineage: str) -> None:
    connection, _ = _fixture_connection()
    if lineage == "direct":
        connection.execute(
            "UPDATE data_policies SET cloud_policy='never_cloud',processing_location='local_only' "
            "WHERE target_record_id='assertion-lamp'"
        )
    else:
        _insert_policy(
            connection,
            policy_id="policy-never-cloud-parent",
            target_record_id="synthetic-parent",
            cloud_policy="never_cloud",
        )
        connection.commit()
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute(
            "INSERT INTO policy_lineage(parent_policy_id,child_policy_id,created_at) VALUES(?,?,?)",
            ("policy-never-cloud-parent", "policy-assertion-lamp", NOW.isoformat()),
        )
        connection.commit()
        connection.execute("PRAGMA foreign_keys=ON")
    connection.commit()
    service, reader, provider, _ = _service(connection)
    with pytest.raises(E07BoundaryError) as raised:
        _prepare(service)
    assert raised.value.code is E07ErrorCode.POLICY_BLOCKED
    assert reader.content_reads == 0 and provider.invocation_count == 0
    connection.close()


def test_canonical_version_change_invalidates_authorization_and_changes_manifest() -> None:
    connection, _ = _fixture_connection()
    service, reader, provider, _ = _service(connection)
    prepared, authorization = _prepare(service)
    connection.execute(
        "UPDATE unknowns SET version_id='unknown-lamp-v2' WHERE record_id='unknown-lamp' AND is_active=1"
    )
    connection.commit()
    with pytest.raises(E07BoundaryError) as raised:
        service.execute(prepared, authorization, now=NOW)  # type: ignore[arg-type]
    assert raised.value.code is E07ErrorCode.STALE_VERSION
    assert reader.content_reads == 0 and provider.invocation_count == 0
    revised_service, _, _, _ = _service(connection)
    revised, _ = _prepare(revised_service)
    assert revised.manifest.manifest_id != prepared.manifest.manifest_id  # type: ignore[union-attr]
    connection.close()


@pytest.mark.parametrize("lineage", ["direct", "reconstructive"])
def test_policy_revocation_after_authorization_blocks_before_disclosure(lineage: str) -> None:
    connection, _ = _fixture_connection()
    service, reader, provider, _ = _service(connection)
    prepared, authorization = _prepare(service)
    if lineage == "direct":
        connection.execute(
            "UPDATE data_policies SET cloud_policy='never_cloud',processing_location='local_only' "
            "WHERE target_record_id='assertion-lamp'"
        )
    else:
        _insert_policy(
            connection,
            policy_id="policy-revoked-parent",
            target_record_id="synthetic-parent",
            cloud_policy="never_cloud",
        )
        connection.commit()
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute(
            "INSERT INTO policy_lineage(parent_policy_id,child_policy_id,created_at) "
            "VALUES(?,?,?)",
            ("policy-revoked-parent", "policy-assertion-lamp", NOW.isoformat()),
        )
        connection.execute("PRAGMA foreign_keys=ON")
    connection.commit()
    with pytest.raises(E07BoundaryError, match="policy_stale"):
        service.execute(prepared, authorization, now=NOW)  # type: ignore[arg-type]
    assert reader.content_reads == 0 and provider.invocation_count == 0
    connection.close()


@pytest.mark.parametrize("variant", ["unavailable", "timeout", "malformed"])
def test_provider_degradation_and_removal_leave_archive_usable_and_unchanged(variant: str) -> None:
    connection, archive = _fixture_connection()
    provider = ScriptedOfflineReflectionProvider(variant=variant)
    service, _, _, registry = _service(connection, provider=provider)
    before = _database_digest(connection)
    prepared, authorization = _prepare(service)
    with pytest.raises(E07BoundaryError):
        service.execute(prepared, authorization, now=NOW)  # type: ignore[arg-type]
    assert _database_digest(connection) == before
    assert archive.timeline("reported")
    registry.remove(IDENTITY)
    assert archive.explorer()["unknowns"][0]["status"] == "open"
    assert _database_digest(connection) == before
    connection.close()
