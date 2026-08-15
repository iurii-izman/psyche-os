"""Telemetry redaction tests for the new model/provider attestation fields."""
from __future__ import annotations

from pathlib import Path

import writer


def _cfg(tmp_path: Path) -> dict:
    return writer.load_config(str(tmp_path))


class TestNewAttestationFieldsSurvive:
    def test_non_secret_model_fields_are_not_redacted(self, tmp_path: Path) -> None:
        cfg = _cfg(tmp_path)
        event = {
            "configured_provider": "deepseek",
            "configured_model": "deepseek-v4-pro",
            "requested_model": "deepseek-v4-pro",
            "harness_reported_model": "claude-opus-5[1m]",
            "provider_mapping": "claude-opus* -> deepseek-v4-pro",
            "effective_backend_model": "deepseek-v4-pro",
            "effective_backend_observable": False,
            "attestation_status": "MAPPED_BY_PROVIDER_CONTRACT",
        }
        redacted = writer.redact(event, cfg)
        for key, value in event.items():
            assert redacted[key] == value, f"{key} should survive redaction"


class TestSecretsRedacted:
    def test_secret_values_redacted_alongside_new_fields(self, tmp_path: Path) -> None:
        cfg = _cfg(tmp_path)
        event = {
            "configured_provider": "deepseek",
            "api_key": "sk-super-secret-value",
            "token": "bearer-token-value",
        }
        redacted = writer.redact(event, cfg)
        assert redacted["configured_provider"] == "deepseek"
        assert redacted["api_key"] == writer.REDACT
        assert redacted["token"] == writer.REDACT

    def test_raw_prompt_dropped(self, tmp_path: Path) -> None:
        cfg = _cfg(tmp_path)
        redacted = writer.redact({"raw_prompt": "DO-NOT-PERSIST"}, cfg)
        assert "raw_prompt" not in redacted
