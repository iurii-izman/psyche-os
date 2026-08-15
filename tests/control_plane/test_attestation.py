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
        result = v2.attest(
            configured_provider="deepseek",
            configured_model="deepseek-v4-pro",
            requested_model="deepseek-v4-pro",
        )
        assert result["attestation_status"] == "UNKNOWN"
        assert result["effective_backend_model"] == "UNKNOWN"
        assert result["effective_backend_model"] != result["configured_model"]

    def test_requested_model_never_becomes_effective(self) -> None:
        result = v2.attest(requested_model="deepseek-v4-pro")
        assert result["effective_backend_model"] == "UNKNOWN"
        assert result["requested_model"] == "deepseek-v4-pro"


class TestMappingContext:
    """Mapping applies only when the active endpoint/upstream is supported by evidence."""

    def test_endpoint_host_identifies_provider_mapping_applies(self) -> None:
        # Case A: ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
        result = v2.attest(
            configured_provider="deepseek",
            endpoint_identity="api.deepseek.com",
            harness_reported_model="claude-opus-5[1m]",
            provider_mapping=DEEPSEEK_MAPPING,
        )
        assert result["attestation_status"] == "MAPPED_BY_PROVIDER_CONTRACT"
        assert result["effective_backend_model"] == "deepseek-v4-pro"

    def test_active_upstream_provider_config_mapping_applies(self) -> None:
        # Case B: localhost endpoint + active upstream provider config = deepseek.
        result = v2.attest(
            configured_provider="deepseek",
            endpoint_identity="127.0.0.1",
            active_upstream_provider="deepseek",
            harness_reported_model="claude-opus-5[1m]",
            provider_mapping=DEEPSEEK_MAPPING,
        )
        assert result["attestation_status"] == "MAPPED_BY_PROVIDER_CONTRACT"
        assert result["effective_backend_model"] == "deepseek-v4-pro"
        assert any("active upstream" in e for e in result["evidence_source"])

    def test_localhost_plus_key_presence_does_not_apply_mapping(self) -> None:
        # Case C: localhost + key merely exists + cc-switch dir merely exists.
        result = v2.attest(
            configured_provider="deepseek",
            endpoint_identity="127.0.0.1",
            harness_reported_model="claude-opus-5[1m]",
            provider_mapping=DEEPSEEK_MAPPING,
        )
        assert result["attestation_status"] == "HARNESS_ONLY"
        assert result["effective_backend_model"] == "UNKNOWN"
        assert result["provider_mapping"] is None

    def test_mapping_is_never_confirmed(self) -> None:
        result = v2.attest(
            configured_provider="deepseek",
            endpoint_identity="api.deepseek.com",
            harness_reported_model="claude-opus-5[1m]",
            provider_mapping=DEEPSEEK_MAPPING,
        )
        assert result["attestation_status"] != "CONFIRMED"

    def test_sonnet_maps_to_flash(self) -> None:
        result = v2.attest(
            configured_provider="deepseek",
            endpoint_identity="api.deepseek.com",
            harness_reported_model="claude-sonnet-4",
            provider_mapping=DEEPSEEK_MAPPING,
        )
        assert result["effective_backend_model"] == "deepseek-v4-flash"


class TestMappingScoping:
    def test_mapping_is_scoped_to_named_provider_no_fallthrough(self) -> None:
        # A deepseek alias must never be used when the provider is not deepseek.
        rule = v2.resolve_mapping("claude-opus-5[1m]", "anthropic", DEEPSEEK_MAPPING)
        assert rule is None

    def test_resolve_mapping_returns_none_for_unknown_provider(self) -> None:
        assert v2.resolve_mapping("claude-opus-5[1m]", "openai", DEEPSEEK_MAPPING) is None

    def test_resolve_mapping_returns_rule_for_deepseek(self) -> None:
        rule = v2.resolve_mapping("claude-opus-5[1m]", "deepseek", DEEPSEEK_MAPPING)
        assert rule == {"pattern": "claude-opus", "maps_to": "deepseek-v4-pro"}


class TestDirectBackend:
    def test_provider_without_model_is_not_confirmed(self) -> None:
        result = v2.attest(
            configured_provider="deepseek",
            direct_backend_provider="deepseek",
        )
        assert result["attestation_status"] != "CONFIRMED"
        assert result["effective_backend_model"] == "UNKNOWN"
        assert result["effective_backend_observable"] is False

    def test_matching_direct_backend_is_confirmed(self) -> None:
        result = v2.attest(
            configured_provider="deepseek",
            configured_model="deepseek-v4-pro",
            direct_backend_provider="deepseek",
            direct_backend_model="deepseek-v4-pro",
        )
        assert result["attestation_status"] == "CONFIRMED"
        assert result["effective_backend_observable"] is True

    def test_observed_model_contradicts_configured_model_is_conflict(self) -> None:
        result = v2.attest(
            configured_provider="deepseek",
            configured_model="deepseek-v4-pro",
            direct_backend_provider="deepseek",
            direct_backend_model="deepseek-v4-flash",
        )
        assert result["attestation_status"] == "CONFLICT"
        assert result["contradictions"]

    def test_observed_model_contradicts_applicable_mapping_is_conflict(self) -> None:
        result = v2.attest(
            configured_provider="deepseek",
            endpoint_identity="api.deepseek.com",
            harness_reported_model="claude-opus-5[1m]",
            direct_backend_provider="deepseek",
            direct_backend_model="deepseek-v4-flash",
            provider_mapping=DEEPSEEK_MAPPING,
        )
        assert result["attestation_status"] == "CONFLICT"
        assert any("mapping" in c for c in result["contradictions"])

    def test_observed_provider_contradiction_is_conflict(self) -> None:
        result = v2.attest(
            configured_provider="deepseek",
            direct_backend_provider="anthropic",
            direct_backend_model="claude-opus-5",
        )
        assert result["attestation_status"] == "CONFLICT"


class TestHarnessOnly:
    def test_harness_model_alone_is_harness_only(self) -> None:
        result = v2.attest(harness_reported_model="claude-opus-5[1m]")
        assert result["attestation_status"] == "HARNESS_ONLY"
        assert result["effective_backend_model"] == "UNKNOWN"

    def test_harness_label_is_not_backend_identity(self) -> None:
        result = v2.attest(harness_reported_model="claude-opus-5[1m]")
        assert result["effective_backend_model"] != result["harness_reported_model"]

    def test_unmapped_harness_is_harness_only(self) -> None:
        result = v2.attest(
            configured_provider="deepseek",
            endpoint_identity="api.deepseek.com",
            harness_reported_model="claude-unknown-model",
            provider_mapping=DEEPSEEK_MAPPING,
        )
        assert result["attestation_status"] == "HARNESS_ONLY"


class TestUnknown:
    def test_no_evidence_is_unknown(self) -> None:
        result = v2.attest()
        assert result["attestation_status"] == "UNKNOWN"
        assert result["effective_backend_model"] == "UNKNOWN"


class TestSecretSafety:
    def test_attestation_output_has_no_secret_keys(self) -> None:
        result = v2.attest(
            configured_provider="deepseek",
            endpoint_identity="api.deepseek.com",
            harness_reported_model="claude-opus-5[1m]",
            provider_mapping=DEEPSEEK_MAPPING,
            evidence_source=["env:DEEPSEEK_API_KEY present"],
        )
        for key in ("api_key", "token", "secret", "password", "authorization"):
            assert key not in result

    def test_gather_evidence_records_presence_not_value(self) -> None:
        provider, evidence = v2.gather_config_evidence(
            {"DEEPSEEK_API_KEY": "SHOULD-NOT-LEAK-SECRET-VALUE"}
        )
        assert provider == "deepseek"
        joined = " ".join(evidence)
        assert "SHOULD-NOT-LEAK" not in joined

    def test_endpoint_host_redacts_credentials(self) -> None:
        assert v2._endpoint_host("https://user:pass@api.deepseek.com/x") == (
            "present (credentials redacted)"
        )
        assert v2._endpoint_host("https://api.deepseek.com/x") == "api.deepseek.com"
