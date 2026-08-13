"""Repository-owned offline E07 provider and canonical SQLite reader."""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
from typing import Any

from psyche_os.application.e07_bounded_ai import (
    PURPOSE,
    CanonicalRecordMetadata,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from psyche_os.domain.ai_proposal import ProviderRequest
from psyche_os.policy.engine import (
    CloudPolicy,
    ExportRule,
    PolicyAxes,
    ProcessingLocation,
    Sensitivity,
    ThirdPartyScope,
)


def _row(connection: Any, sql: str, args: tuple[Any, ...]) -> dict[str, Any] | None:
    cursor = connection.execute(sql, args)
    value = cursor.fetchone()
    if value is None:
        return None
    return dict(zip((item[0] for item in cursor.description), value, strict=True))


def _policy_axes(row: dict[str, Any]) -> PolicyAxes:
    expiry = row.get("purpose_expiry")
    review = row.get("retention_review")
    return PolicyAxes(
        sensitivity=Sensitivity(row["sensitivity"]),
        processing_location=ProcessingLocation(row["processing_location"]),
        cloud_policy=CloudPolicy(row["cloud_policy"]),
        purpose=str(row["purpose"]),
        purpose_expiry=dt.datetime.fromisoformat(expiry) if expiry else None,
        third_party_scope=ThirdPartyScope(row["third_party_scope"]),
        retention_policy_id=str(row["retention_policy_id"]),
        retention_review_date=dt.datetime.fromisoformat(review) if review else None,
        export_rule=ExportRule(row["export_rule"]),
        export_audience=str(row["export_audience"]),
        lineage_rule=str(row["lineage_rule"]),
    )


class SQLiteCanonicalRecordReader:
    """Read exact active E03 canonical versions; never writes or regenerates fixture text."""

    def __init__(self, connection: Any) -> None:
        self.connection = connection
        self.content_reads = 0

    def read_metadata(self, record_id: str) -> CanonicalRecordMetadata | None:
        category = ""
        version_id = ""
        for table, candidate in (("assertions", "assertion"), ("unknowns", "unknown")):
            row = _row(
                self.connection,
                f"SELECT version_id FROM {table} WHERE record_id=? AND is_active=1",
                (record_id,),
            )
            if row is not None:
                category = candidate
                version_id = str(row["version_id"])
                break
        if not category:
            return None
        own = _row(
            self.connection,
            "SELECT * FROM data_policies WHERE target_record_id=? AND is_active=1",
            (record_id,),
        )
        if own is None:
            return None
        cursor = self.connection.execute(
            "SELECT p.* FROM policy_lineage l JOIN data_policies p "
            "ON p.policy_id=l.parent_policy_id AND p.is_active=1 "
            "WHERE l.child_policy_id=? ORDER BY p.policy_id",
            (own["policy_id"],),
        )
        columns = tuple(item[0] for item in cursor.description)
        parents = tuple(
            (str(parent["policy_id"]), str(parent["version_id"]), _policy_axes(parent))
            for values in cursor.fetchall()
            for parent in (dict(zip(columns, values, strict=True)),)
        )
        return CanonicalRecordMetadata(
            record_id,
            version_id,
            category,
            str(own["policy_id"]),
            _policy_axes(own),
            str(own["version_id"]),
            parents,
        )

    def read_content(self, record_id: str, version_id: str) -> str:
        self.content_reads += 1
        assertion = _row(
            self.connection,
            "SELECT object_value FROM assertions WHERE record_id=? AND version_id=?",
            (record_id, version_id),
        )
        if assertion is not None:
            return str(assertion["object_value"])
        unknown = _row(
            self.connection,
            "SELECT question,knowledge_state FROM unknowns WHERE record_id=? AND version_id=?",
            (record_id, version_id),
        )
        if unknown is not None:
            return f"Unknown: {unknown['question']} State: {unknown['knowledge_state']}"
        raise KeyError("record/version not found")


@dataclass(slots=True)
class ScriptedOfflineReflectionProvider:
    """One-call deterministic test adapter with no state beyond an invocation counter."""

    variant: str = "valid"
    invocation_count: int = 0
    last_request: ProviderRequest | None = None

    def invoke(self, request: ProviderRequest) -> Any:
        self.invocation_count += 1
        self.last_request = request
        if self.variant == "unavailable":
            raise ProviderUnavailableError
        if self.variant == "timeout":
            raise ProviderTimeoutError
        if self.variant == "malformed":
            return {"schema_version": "broken"}
        support = tuple(
            item.record_id for item in request.records if item.role.value == "supporting"
        )
        counters = [
            item.record_id for item in request.records if item.role.value == "counterevidence"
        ]
        unknowns = [item.record_id for item in request.records if item.role.value == "unknown"]
        if request.purpose != PURPOSE or not support or not counters or not unknowns:
            return {"schema_version": "broken"}
        return {
            "schema_version": "e07-reflection-proposal-v1",
            "proposal_id": "proposal-orbit-console-v1",
            "status": "PROPOSED",
            "reflections": [
                {
                    "statement_id": "reflection-1",
                    "text": "The selected fictional console report describes an amber signal.",
                    "supporting_evidence_ids": list(support),
                    "uncertainty": "The selected records disagree, so the signal state remains uncertain.",
                    "claim_level": 0,
                }
            ],
            "counterevidence": counters,
            "unknowns": [
                {
                    "unknown_id": unknown_id,
                    "uncertainty": "The exact fictional controller state is not selected evidence.",
                }
                for unknown_id in unknowns
            ],
            "questions": [
                {
                    "question_id": "question-1",
                    "unknown_id": unknowns[0],
                    "text": "What timestamped fictional controller record could clarify this unknown?",
                }
            ],
        }
