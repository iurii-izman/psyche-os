"""Field Preview v0.2: user-controlled E07 AI evidence selection.

Proves backend-owned eligibility listing, role/category constraints, max
selection, dynamic prepare, reflection-disclosure blocking, authorization
tying, and one-call/no-retry proposal flow without live provider cost.
"""

from __future__ import annotations

import datetime as dt

import pytest

from psyche_os.adapters.e07_provider import ScriptedOfflineReflectionProvider
from psyche_os.application.desktop_service import DesktopApplicationService, DesktopServiceError
from psyche_os.application.e07_bounded_ai import (
    PURPOSE,
    BoundedAIProposalService,
    CanonicalRecordMetadata,
    ProviderRegistry,
    ProviderRegistryEntry,
)
from psyche_os.domain.ai_proposal import EvidenceRole, ProviderIdentity
from psyche_os.policy.engine import CloudPolicy, PolicyAxes, ProcessingLocation

BASE_SELECTION = [
    {"record_id": "assertion-lamp", "role": "supporting"},
    {"record_id": "assertion-counter", "role": "counterevidence"},
    {"record_id": "unknown-lamp", "role": "unknown"},
]


def _unlock(service: DesktopApplicationService) -> str:
    return str(
        service.dispatch("session.unlock", {"secret": "synthetic-demo"}, None)["session_token"]
    )


def _select(service: DesktopApplicationService, token: str, selected: list[dict]) -> dict:
    return service.dispatch("ai.prepare", {"selected": selected}, token)


def test_ai_list_eligible_returns_policy_eligible_canonical_records_only() -> None:
    service = DesktopApplicationService()
    token = _unlock(service)
    result = service.dispatch("ai.list_eligible", {}, token)
    records = result["records"]
    assert len(records) >= 3
    by_id = {record["record_id"]: record for record in records}
    assert {"assertion-lamp", "assertion-counter", "unknown-lamp"} <= set(by_id)
    assert by_id["assertion-lamp"]["category"] == "assertion"
    assert set(by_id["assertion-lamp"]["allowed_roles"]) == {"supporting", "counterevidence"}
    assert by_id["unknown-lamp"]["category"] == "unknown"
    assert by_id["unknown-lamp"]["allowed_roles"] == ["unknown"]
    assert all("version_id" in record and "display_text" in record for record in records)
    assert result["provider"] == "OpenAI"
    service.close()


def test_ai_prepare_dynamic_selection_reaches_preview() -> None:
    service = DesktopApplicationService()
    token = _unlock(service)
    result = _select(service, token, BASE_SELECTION)
    assert result["preview_id"]
    assert result["provider"] == "OpenAI"
    assert result["model"] == "gpt-5.6-luna"
    assert result["retention"] == "ephemeral"
    selected = {(row["record_id"], row["role"]) for row in result["selected"]}
    assert selected == {
        ("assertion-lamp", "supporting"),
        ("assertion-counter", "counterevidence"),
        ("unknown-lamp", "unknown"),
    }
    assert all("version_id" in row and "category" in row for row in result["selected"])
    service.close()


def test_ai_prepare_rejects_role_category_violations() -> None:
    service = DesktopApplicationService()
    token = _unlock(service)
    with pytest.raises(DesktopServiceError, match="INVALID_SELECTION"):
        _select(
            service,
            token,
            [
                {"record_id": "unknown-lamp", "role": "supporting"},
                {"record_id": "assertion-lamp", "role": "counterevidence"},
                {"record_id": "assertion-counter", "role": "unknown"},
            ],
        )
    service.close()


def test_ai_prepare_requires_all_three_roles_and_bounds_count() -> None:
    service = DesktopApplicationService()
    token = _unlock(service)
    with pytest.raises(DesktopServiceError, match="INVALID_SELECTION"):
        _select(
            service,
            token,
            [
                {"record_id": "assertion-lamp", "role": "supporting"},
                {"record_id": "assertion-counter", "role": "counterevidence"},
            ],
        )
    with pytest.raises(DesktopServiceError, match="INVALID_SELECTION"):
        _select(service, token, BASE_SELECTION * 3)
    with pytest.raises(DesktopServiceError, match="INVALID_SELECTION"):
        _select(service, token, [])
    service.close()


def test_ai_prepare_rejects_reflection_workspace_ids_before_network() -> None:
    service = DesktopApplicationService()
    token = _unlock(service)
    session = service.dispatch("reflection_session.create", {"title": "Отражение"}, token)
    with pytest.raises(DesktopServiceError, match="INVALID_SELECTION"):
        _select(
            service,
            token,
            [
                {"record_id": session["session_id"], "role": "supporting"},
                {"record_id": "assertion-counter", "role": "counterevidence"},
                {"record_id": "unknown-lamp", "role": "unknown"},
            ],
        )
    # No provider call, no receipt, no event was recorded.
    assert service._ai.receipts == []
    assert service._ai.events == []
    service.close()


def test_ai_authorization_is_tied_to_the_current_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    service = DesktopApplicationService()
    token = _unlock(service)
    first = _select(service, token, BASE_SELECTION)
    swapped = [
        {"record_id": "assertion-lamp", "role": "counterevidence"},
        {"record_id": "assertion-counter", "role": "supporting"},
        {"record_id": "unknown-lamp", "role": "unknown"},
    ]
    second = _select(service, token, swapped)
    assert first["preview_id"] != second["preview_id"]
    # The older preview can no longer authorize the current prepared disclosure.
    with pytest.raises(DesktopServiceError, match="AUTHORIZATION_MISMATCH"):
        service.dispatch(
            "ai.authorize_execute",
            {"preview_id": first["preview_id"], "opt_in": True},
            token,
        )
    service.close()


NOW = dt.datetime(2045, 2, 3, 10, tzinfo=dt.UTC)
IDENTITY = ProviderIdentity("offline-scripted", "orbit-reflection-1.0.0", "cfg-sha256:abc")


def _axes() -> PolicyAxes:
    return PolicyAxes(
        processing_location=ProcessingLocation.APPROVED_CLOUD,
        cloud_policy=CloudPolicy.ASK_EACH_TIME,
        purpose=PURPOSE,
        purpose_expiry=NOW + dt.timedelta(days=1),
        retention_policy_id="ephemeral-e07",
    )


class _MemoryReader:
    """Small canonical reader exposing a wider set of dynamic records."""

    def __init__(self) -> None:
        self.metadata = {
            record_id: CanonicalRecordMetadata(
                record_id,
                f"{record_id}-v1",
                "unknown" if "unknown" in record_id else "assertion",
                f"policy-{record_id}",
                _axes(),
                f"policy-{record_id}-v1",
            )
            for record_id in ("support-a", "counter-a", "unknown-a")
        }
        self.content = {
            "support-a": "Fictional amber console.",
            "counter-a": "A fictional ledger records green.",
            "unknown-a": "Which fictional state applied at the same clock?",
        }

    def read_metadata(self, record_id: str) -> CanonicalRecordMetadata | None:
        return self.metadata.get(record_id)

    def read_content(self, record_id: str, version_id: str) -> str:
        return self.content[record_id]

    def enumerate_ids(self) -> tuple[str, ...]:
        return ("counter-a", "support-a", "unknown-a")


def test_dynamic_selection_reaches_the_structured_provider_contract() -> None:
    reader = _MemoryReader()
    provider = ScriptedOfflineReflectionProvider()
    service = BoundedAIProposalService(
        reader,
        ProviderRegistry(
            (ProviderRegistryEntry(IDENTITY, "p1", "k1", "safety-v1", True, IDENTITY.digest),)
        ),
        provider,
    )
    selected = (
        ("support-a", EvidenceRole.SUPPORTING),
        ("counter-a", EvidenceRole.COUNTEREVIDENCE),
        ("unknown-a", EvidenceRole.UNKNOWN),
    )
    prepared = service.prepare(
        interaction_id="dynamic-1",
        purpose=PURPOSE,
        selected=selected,
        provider_identity=IDENTITY,
        cutoff=NOW,
    )
    authorization = service.authorize(
        prepared, authorized_at=NOW, expires_at=NOW + dt.timedelta(minutes=2), opt_in=True
    )
    result = service.execute(prepared, authorization, now=NOW)
    assert result.proposal.status.value == "PROPOSED"
    assert provider.invocation_count == 1
    assert provider.last_request is not None
    assert tuple(item.record_id for item in provider.last_request.records) == (
        "support-a",
        "counter-a",
        "unknown-a",
    )
    assert tuple(item.role.value for item in provider.last_request.records) == (
        "supporting",
        "counterevidence",
        "unknown",
    )
    assert result.envelope.proposal_status == "PROPOSED"


def test_dynamic_selection_fails_closed_on_invalid_output() -> None:
    reader = _MemoryReader()
    provider = ScriptedOfflineReflectionProvider()
    provider.variant = "malformed"
    service = BoundedAIProposalService(
        reader,
        ProviderRegistry(
            (ProviderRegistryEntry(IDENTITY, "p1", "k1", "safety-v1", True, IDENTITY.digest),)
        ),
        provider,
    )
    selected = (
        ("support-a", EvidenceRole.SUPPORTING),
        ("counter-a", EvidenceRole.COUNTEREVIDENCE),
        ("unknown-a", EvidenceRole.UNKNOWN),
    )
    prepared = service.prepare(
        interaction_id="dynamic-2",
        purpose=PURPOSE,
        selected=selected,
        provider_identity=IDENTITY,
        cutoff=NOW,
    )
    authorization = service.authorize(
        prepared, authorized_at=NOW, expires_at=NOW + dt.timedelta(minutes=2), opt_in=True
    )
    with pytest.raises(Exception, match="output_rejected"):
        service.execute(prepared, authorization, now=NOW)
    assert provider.invocation_count == 1
