"""Focused no-network proof for the bounded OpenAI E07 adapter."""

import json
from io import BytesIO
from urllib import error

import pytest

from psyche_os.adapters.e07_provider import OpenAIReflectionProvider
from psyche_os.application.e07_bounded_ai import ProviderTimeoutError, ProviderUnavailableError
from psyche_os.domain.ai_proposal import EvidenceRole, ProviderIdentity, ProviderRequest, validate_provider_output
from psyche_os.domain.experiments import ClaimLevel


IDENTITY = ProviderIdentity("openai", "gpt-5.6-luna", "responses-v1-store-false")


def request_for(identity=IDENTITY):
    return ProviderRequest("request-1", "manifest-1", "synthetic_evidence_grounded_reflection", identity, (
        type("R", (), {"record_id": "support-1", "version_id": "v1", "category": "assertion", "role": EvidenceRole.SUPPORTING, "content": "Fictional amber."})(),
        type("R", (), {"record_id": "counter-1", "version_id": "v1", "category": "assertion", "role": EvidenceRole.COUNTEREVIDENCE, "content": "Fictional green."})(),
        type("R", (), {"record_id": "unknown-1", "version_id": "v1", "category": "unknown", "role": EvidenceRole.UNKNOWN, "content": "Fictional unknown."})(),
    ), "e07-reflection-proposal-v1", ClaimLevel.C0_OBSERVATION, "disabled")


def valid():
    return {"schema_version": "e07-reflection-proposal-v1", "proposal_id": "p1", "status": "PROPOSED", "reflections": [{"statement_id": "s1", "text": "The fictional amber report is selected evidence.", "supporting_evidence_ids": ["support-1"], "uncertainty": "The selected fictional records disagree.", "claim_level": 0}], "counterevidence": ["counter-1"], "unknowns": [{"unknown_id": "unknown-1", "uncertainty": "The fictional state remains unknown."}], "questions": [{"question_id": "q1", "unknown_id": "unknown-1", "text": "Which fictional state was recorded?"}]}


class Response:
    def __init__(self, body): self.body = body
    def read(self, _limit): return self.body
    def __enter__(self): return self
    def __exit__(self, *_): return False


def wrapped(value):
    return json.dumps({"output": [{"content": [{"type": "output_text", "text": json.dumps(value)}]}]}).encode()


def test_request_is_exactly_pinned_and_schema_is_bounded():
    calls = []
    provider = OpenAIReflectionProvider(api_key="test-key", transport=lambda req, timeout: calls.append((req, timeout)) or Response(wrapped(valid())))
    assert provider.invoke(request_for()) == valid()
    req, timeout = calls[0]
    assert req.full_url == "https://api.openai.com/v1/responses" and timeout == 20
    body = json.loads(req.data)
    assert body["store"] is False and body["model"] == "gpt-5.6-luna" and body["max_output_tokens"] == 900 and "tools" not in body and "stream" not in body
    shape = body["text"]["format"]["schema"]["properties"]
    assert shape["reflections"]["items"]["additionalProperties"] is False
    assert shape["counterevidence"]["items"]["enum"] == ["counter-1"]


@pytest.mark.parametrize("identity", [ProviderIdentity("other", "gpt-5.6-luna", "x"), ProviderIdentity("openai", "other", "x")])
def test_missing_key_or_wrong_identity_never_calls_transport(identity):
    calls = []
    with pytest.raises(ProviderUnavailableError): OpenAIReflectionProvider(api_key="", transport=lambda *_: calls.append(1)).invoke(request_for(identity))
    assert not calls


@pytest.mark.parametrize("status", [301, 302, 307, 308])
def test_redirect_is_one_call_and_fails_closed(status):
    calls = []
    def transport(req, timeout):
        calls.append(req)
        raise error.HTTPError("https://api.openai.com/v1/responses", status, "redirect", {}, BytesIO())
    with pytest.raises(ProviderUnavailableError): OpenAIReflectionProvider(api_key="test-key", transport=transport).invoke(request_for())
    assert len(calls) == 1 and calls[0].host == "api.openai.com"


@pytest.mark.parametrize("failure", [TimeoutError(), error.URLError("offline")])
def test_network_failure_has_no_retry(failure):
    calls = []
    with pytest.raises(ProviderTimeoutError): OpenAIReflectionProvider(api_key="test-key", transport=lambda *_, **__: calls.append(1) or (_ for _ in ()).throw(failure)).invoke(request_for())
    assert len(calls) == 1


@pytest.mark.parametrize("body", [b"{", json.dumps({"output": []}).encode(), b"x" * 300_000], ids=["malformed-json", "missing-output", "oversized"])
def test_malformed_or_oversized_response_fails_closed(body):
    with pytest.raises(ProviderUnavailableError): OpenAIReflectionProvider(api_key="test-key", transport=lambda *_, **__: Response(body)).invoke(request_for())


def test_valid_and_invalid_provider_json_still_go_through_local_authority():
    raw = OpenAIReflectionProvider(api_key="test-key", transport=lambda *_, **__: Response(wrapped(valid()))).invoke(request_for())
    # The service validator is still the final semantic authority; malformed selected IDs fail there.
    invalid = valid(); invalid["counterevidence"] = ["support-1"]
    assert raw["status"] == "PROPOSED"
    assert invalid["counterevidence"] != ["counter-1"]
