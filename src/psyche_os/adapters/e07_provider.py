"""Repository-owned offline E07 provider and canonical SQLite reader."""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import json
import os
from typing import Any
from urllib import error, request

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


class OpenAIReflectionProvider:
    """One bounded Responses API call for an already-authorized E07 request."""

    host = "api.openai.com"
    endpoint = "https://api.openai.com/v1/responses"
    max_response_bytes = 256_000

    def __init__(self, *, transport: Any | None = None, api_key: str | None = None) -> None:
        self._transport = transport or request.build_opener(_RejectRedirects()).open
        self._api_key = api_key
        self.invocation_count = 0

    def invoke(self, provider_request: ProviderRequest) -> Any:
        key = self._api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ProviderUnavailableError("AI_NOT_CONFIGURED")
        if provider_request.provider_identity.provider != "openai" or provider_request.provider_identity.model_snapshot != "gpt-5.6-luna":
            raise ProviderUnavailableError("MODEL_NOT_AVAILABLE")
        self.invocation_count += 1
        supporting = [item.record_id for item in provider_request.records if item.role.value == "supporting"]
        counters = [item.record_id for item in provider_request.records if item.role.value == "counterevidence"]
        unknowns = [item.record_id for item in provider_request.records if item.role.value == "unknown"]
        text = {"type": "string", "minLength": 1, "maxLength": 500}
        identifier = {"type": "string", "minLength": 1, "maxLength": 128}
        reflection = {"type": "object", "additionalProperties": False, "required": ["statement_id", "text", "supporting_evidence_ids", "uncertainty", "claim_level"], "properties": {"statement_id": identifier, "text": text, "supporting_evidence_ids": {"type": "array", "minItems": 1, "maxItems": len(supporting), "uniqueItems": True, "items": {"type": "string", "enum": supporting}}, "uncertainty": {"type": "string", "minLength": 1, "maxLength": 240}, "claim_level": {"type": "integer", "minimum": 0, "maximum": int(provider_request.claim_ceiling)}}}
        unknown = {"type": "object", "additionalProperties": False, "required": ["unknown_id", "uncertainty"], "properties": {"unknown_id": {"type": "string", "enum": unknowns}, "uncertainty": {"type": "string", "minLength": 1, "maxLength": 240}}}
        question = {"type": "object", "additionalProperties": False, "required": ["question_id", "unknown_id", "text"], "properties": {"question_id": identifier, "unknown_id": {"type": "string", "enum": unknowns}, "text": {"type": "string", "minLength": 1, "maxLength": 240}}}
        shape = {"type": "object", "additionalProperties": False, "required": ["schema_version", "proposal_id", "status", "reflections", "counterevidence", "unknowns", "questions"], "properties": {"schema_version": {"const": "e07-reflection-proposal-v1"}, "proposal_id": identifier, "status": {"const": "PROPOSED"}, "reflections": {"type": "array", "minItems": 1, "maxItems": 4, "items": reflection}, "counterevidence": {"type": "array", "minItems": len(counters), "maxItems": len(counters), "uniqueItems": True, "items": {"type": "string", "enum": counters}}, "unknowns": {"type": "array", "minItems": len(unknowns), "maxItems": len(unknowns), "uniqueItems": True, "items": unknown}, "questions": {"type": "array", "maxItems": 3, "items": question}}}
        schema = {"type": "json_schema", "name": "e07_reflection_proposal", "strict": True, "schema": shape}
        payload = {"model": "gpt-5.6-luna", "store": False, "max_output_tokens": 900,
            "text": {"format": schema}, "input": [{"role": "developer", "content": "Return only the requested bounded E07 proposal. It is a proposal, not evidence, fact, diagnosis, recommendation, or action."}, {"role": "user", "content": json.dumps({"purpose": provider_request.purpose, "records": [{"record_id": r.record_id, "version_id": r.version_id, "category": r.category, "role": r.role.value, "content": r.content} for r in provider_request.records]}, ensure_ascii=False)}]}
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        outbound = request.Request(self.endpoint, data=body, method="POST", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with self._transport(outbound, timeout=20) as response:
                raw = response.read(self.max_response_bytes + 1)
                if len(raw) > self.max_response_bytes:
                    raise ProviderUnavailableError("PROVIDER_RESPONSE_TOO_LARGE")
        except error.HTTPError as exc:
            raise ProviderUnavailableError("PROVIDER_HTTP_ERROR") from exc
        except (error.URLError, TimeoutError, OSError) as exc:
            raise ProviderTimeoutError from exc
        try:
            decoded = json.loads(raw)
            for item in decoded.get("output", []):
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        return json.loads(content["text"])
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProviderUnavailableError("PROVIDER_MALFORMED_RESPONSE") from exc
        raise ProviderUnavailableError("PROVIDER_MALFORMED_RESPONSE")


class _RejectRedirects(request.HTTPRedirectHandler):
    """A credential-bearing request must fail at the first redirect response."""

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


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
