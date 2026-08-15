"""Model/provider attestation tests (component A)."""
from __future__ import annotations

import ai_dev_v2 as v2

DEEPSEEK_MAPPING = {
    "provider_mapping": {
        "deepseek": {
            "aliases": [
                {"pattern": "claude-opus", "maps_to": "deepseek-v4-pro"},
                {"pattern": "claude-sonnet", "maps_to": "deepseek-v4-flash"},
                {"pattern": "claude-haiku", "maps_to": "deepseek-v4-flash"},
            ]
        }
    }
}


class TestConfiguredVsEffective:
    def test_configured_model_is_not_effective_without_evidence(self) -> None:
        # Configuration evidence alone must not prove runtime backend identity.
        result = v2.attest(
            configured_provider="deepseek",
            configured_model="deepseek-v4-pro",
            requested_model="deepseek-v4-pro",
        )
        assert result["attestation_status"] == "UNKNOWN"
        assert result["effective_backend_model"] == "UNKNOWN"
        assert result["configured_model"] == "deepseek-v4-pro"
        assert result["effective_backend_model"] != result["configured_model"]

    def test_requested_model_never_becomes_effective(self) -> None:
        result = v2.attest(requested_model="deepseek-v4-pro", harness_reported_model=None)
        assert result["effective_backend_model"] == "UNKNOWN"
        assert result["requested_model"] == "deepseek-v4-pro"


class TestHarnessOnly:
    def test_harness_model_alone_is_harness_only(self) -> None:
        result = v2.attest(harness_reported_model="claude-opus-5[1m]")
        assert result["attestation_status"] == "HARNESS_ONLY"
        assert result["effective_backend_model"] == "UNKNOWN"
        assert result["harness_reported_model"] == "claude-opus-5[1m]"

    def test_harness_label_is_not_backend_identity(self) -> None:
        result = v2.attest(harness_reported_model="claude-opus-5[1m]")
        assert result["effective_backend_model"] != result["harness_reported_model"]


class TestDeepSeekMapping:
    def test_claude_opus_maps_to_deepseek_v4_pro(self) -> None:
        result = v2.attest(
            configured_provider="deepseek",
            harness_reported_model="claude-opus-5[1m]",
            provider_mapping=DEEPSEEK_MAPPING,
        )
        assert result["attestation_status"] == "MAPPED_BY_PROVIDER_CONTRACT"
        assert result["effective_backend_model"] == "deepseek-v4-pro"
        assert result["effective_backend_observable"] is False

    def test_mapping_is_never_confirmed(self) -> None:
        result = v2.attest(
            configured_provider="deepseek",
            harness_reported_model="claude-opus-5[1m]",
            provider_mapping=DEEPSEEK_MAPPING,
        )
        assert result["attestation_status"] != "CONFIRMED"

    def test_sonnet_maps_to_flash(self) -> None:
        result = v2.attest(
            configured_provider="deepseek",
            harness_reported_model="claude-sonnet-4",
            provider_mapping=DEEPSEEK_MAPPING,
        )
        assert result["effective_backend_model"] == "deepseek-v4-flash"


class TestUnknownAndConflict:
    def test_no_evidence_is_unknown(self) -> None:
        result = v2.attest()
        assert result["attestation_status"] == "UNKNOWN"
        assert result["effective_backend_model"] == "UNKNOWN"

    def test_unmapped_harness_is_harness_only(self) -> None:
        result = v2.attest(
            configured_provider="deepseek",
            harness_reported_model="claude-unknown-model",
            provider_mapping=DEEPSEEK_MAPPING,
        )
        assert result["attestation_status"] == "HARNESS_ONLY"

    def test_contradictory_backend_is_conflict(self) -> None:
        result = v2.attest(
            configured_provider="deepseek",
            direct_backend_provider="anthropic",
            direct_backend_model="claude-opus-5",
        )
        assert result["attestation_status"] == "CONFLICT"
        assert result["contradictions"]

    def test_matching_direct_backend_is_confirmed(self) -> None:
        result = v2.attest(
            configured_provider="deepseek",
            direct_backend_provider="deepseek",
            direct_backend_model="deepseek-v4-pro",
        )
        assert result["attestation_status"] == "CONFIRMED"
        assert result["effective_backend_observable"] is True


class TestSecretSafety:
    def test_attestation_output_has_no_secret_keys(self) -> None:
        result = v2.attest(
            configured_provider="deepseek",
            harness_reported_model="claude-opus-5[1m]",
            provider_mapping=DEEPSEEK_MAPPING,
            evidence_source=["env:DEEPSEEK_API_KEY present"],
        )
        serialized = str(result).lower()
        assert "api_key_value" not in serialized
        assert "secret_value" not in serialized
        for key in ("api_key", "token", "secret", "password", "authorization"):
            assert key not in result

    def test_gather_evidence_records_presence_not_value(self) -> None:
        provider, evidence = v2.gather_config_evidence(
            {"DEEPSEEK_API_KEY": "SHOULD-NOT-LEAK-SECRET-VALUE"}
        )
        assert provider == "deepseek"
        joined = " ".join(evidence)
        assert "SHOULD-NOT-LEAK" not in joined
        assert "present" in joined

    def test_endpoint_host_redacts_credentials(self) -> None:
        assert v2._endpoint_host("https://user:pass@api.deepseek.com/x") == (
            "present (credentials redacted)"
        )
        assert v2._endpoint_host("https://api.deepseek.com/x") == "api.deepseek.com"
