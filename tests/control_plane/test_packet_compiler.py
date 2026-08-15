"""Task/Review packet compiler tests (component E)."""
from __future__ import annotations

import ai_dev_v2 as v2


def sample_contract(conflict_status: str = "none") -> dict:
    return {
        "task_id": "AI-DEV-V2-CONTROL-CANARY-001",
        "base_sha": "ceb3031dd5d7d75564691f59ddf6e23dd71a812f",
        "risk": "high",
        "profile": "quality",
        "goal": ["Implement the bounded canary."],
        "non_goals": ["No E11 implementation."],
        "authority": {
            "highest": ["CONSTITUTION.md"],
            "supporting": [".ai-dev/README.md"],
            "implementation_precedent": ["E10 acceptance evidence"],
        },
        "authority_conflicts": {"status": conflict_status, "items": []},
        "expected_scope": [".ai-dev/contracts/**"],
        "protected_scope": ["src/psyche_os/**"],
        "acceptance": ["V1 rollback remains functional."],
        "verification": ["uv run pytest -q"],
        "permissions": {"network": False, "dependencies": False, "migrations": False,
                        "destructive": False, "control_plane_change": True},
        "routing": {"initial": "strong", "max_grounded_retry": 1, "escalation": "stop_and_report"},
    }


def sample_attestation() -> dict:
    return {
        "configured_provider": "deepseek",
        "configured_model": "deepseek-v4-pro",
        "requested_model": "deepseek-v4-pro",
        "harness_reported_model": "claude-opus-5[1m]",
        "provider_mapping": "claude-opus* -> deepseek-v4-pro (DeepSeek Anthropic-compatible contract)",
        "effective_backend_model": "deepseek-v4-pro",
        "effective_backend_observable": False,
        "attestation_status": "MAPPED_BY_PROVIDER_CONTRACT",
        "evidence_source": ["env:DEEPSEEK_API_KEY present"],
    }


class TestDeterminism:
    def test_task_packet_byte_identical(self) -> None:
        a = v2.render_task_packet(sample_contract(), sample_attestation())
        b = v2.render_task_packet(sample_contract(), sample_attestation())
        assert a == b
        assert a.endswith("\n")

    def test_review_packet_byte_identical(self) -> None:
        state = {
            "candidate_sha": "abc123",
            "changed_files": ["scripts/ai_dev_v2.py"],
            "attestation": sample_attestation(),
            "residuals": ["no direct backend observability"],
            "blockers": [],
            "review_questions": [],
        }
        assert v2.render_review_packet(sample_contract(), state) == (
            v2.render_review_packet(sample_contract(), state)
        )


class TestFieldContent:
    def test_task_packet_has_core_fields(self) -> None:
        text = v2.render_task_packet(sample_contract(), sample_attestation())
        for token in (
            "AI-DEV-V2-CONTROL-CANARY-001",
            "ceb3031dd5d7d75564691f59ddf6e23dd71a812f",
            "risk: high",
            "CONSTITUTION.md",
            "attestation_status: MAPPED_BY_PROVIDER_CONTRACT",
        ):
            assert token in text

    def test_review_packet_has_candidate_sha(self) -> None:
        state = {"candidate_sha": "deadbeef", "changed_files": ["a.py"], "attestation": {}}
        text = v2.render_review_packet(sample_contract(), state)
        assert "candidate_sha: deadbeef" in text

    def test_review_packet_lists_changed_files(self) -> None:
        state = {"candidate_sha": "x", "changed_files": ["a.py", "b.py"], "attestation": {}}
        text = v2.render_review_packet(sample_contract(), state)
        assert "a.py" in text
        assert "b.py" in text


class TestNoSecretLeakage:
    def test_packet_does_not_leak_secret_or_raw_prompt(self) -> None:
        contract = sample_contract()
        state = {
            "attestation": sample_attestation(),
            "verification_evidence": {"raw_prompt": "DO-NOT-LEAK", "api_key": "SECRET"},
        }
        text = v2.render_review_packet(contract, state)
        # renderer never emits raw prompt / secret keys, even if present in input state.
        assert "DO-NOT-LEAK" not in text
        assert "SECRET" not in text

    def test_packet_does_not_dump_generic_policy(self) -> None:
        # AGENTS.md / .ai-dev policy text must not be reproduced; only pointers.
        text = v2.render_task_packet(sample_contract(), sample_attestation())
        assert "Non-negotiable rules" not in text
        assert "C-01" not in text


class TestBlockedPacket:
    def test_high_unresolved_review_packet_is_blocked(self) -> None:
        contract = sample_contract(conflict_status="unresolved")
        text = v2.render_review_packet(contract, {"attestation": {}})
        assert "BLOCKED" in text
        assert "acceptance_blocked: true" in text

    def test_high_unresolved_task_packet_is_blocked(self) -> None:
        contract = sample_contract(conflict_status="unresolved")
        text = v2.render_task_packet(contract)
        assert "BLOCKED" in text
        assert "acceptance_blocked: true" in text

    def test_resolved_packet_is_not_blocked(self) -> None:
        contract = sample_contract(conflict_status="resolved")
        text = v2.render_review_packet(contract, {"attestation": {}})
        assert "BLOCKED" not in text
        assert "acceptance_blocked: false" in text


class TestGuardComposedIntoPacket:
    def test_review_packet_blocked_on_authority_precedence_violation(self) -> None:
        # A contract check would flag this violation; packet rendering must not bypass it.
        c = sample_contract()
        c["authority"] = {
            "highest": ["CONSTITUTION.md"],
            "supporting": [],
            "implementation_precedent": ["E10 acceptance evidence"],
        }
        c["authority_conflicts"] = {
            "status": "resolved",
            "items": [
                {
                    "refs": ["CONSTITUTION.md", "E10 acceptance evidence"],
                    "outranks": "E10 acceptance evidence",
                    "disposition": "precedent wins",
                    "blocks_acceptance": False,
                }
            ],
        }
        assert v2.guard_decision(c)["violations"]
        text = v2.render_review_packet(c, {"attestation": {}})
        assert "BLOCKED" in text
        assert "acceptance_blocked: true" in text

    def test_review_packet_blocked_on_missing_authority_conflicts(self) -> None:
        c = {
            "task_id": "T-1",
            "base_sha": "x",
            "risk": "high",
            "profile": "quality",
            "authority": {"highest": ["CONSTITUTION.md"], "supporting": [], "implementation_precedent": []},
        }
        text = v2.render_review_packet(c, {"attestation": {}})
        assert "BLOCKED" in text


class TestNestedSanitization:
    def test_nested_secret_and_raw_prompt_are_sanitized(self) -> None:
        state = {
            "verification_evidence": {
                "pytest": {
                    "token": "SUPERSECRET",
                    "raw_prompt": "DO-NOT-LEAK",
                    "nested": {"client_secret": "VALUE", "ok": "keep-me"},
                },
                "items": [{"api_key": "AKIA0123456789ABCDEF"}, "sk-abcdefghijklmnopqrstuvwxyz"],
            },
            "attestation": {},
        }
        text = v2.render_review_packet(sample_contract(), state)
        assert "SUPERSECRET" not in text
        assert "DO-NOT-LEAK" not in text
        assert "VALUE" not in text
        assert "AKIA0123456789ABCDEF" not in text
        assert "sk-abcdefghijklmnopqrstuvwxyz" not in text
        assert "keep-me" in text  # ordinary evidence survives

    def test_conflict_items_are_sanitized(self) -> None:
        c = sample_contract(conflict_status="resolved")
        c["authority_conflicts"] = {
            "status": "resolved",
            "items": [
                {
                    "refs": ["CONSTITUTION.md"],
                    "outranks": "CONSTITUTION.md",
                    "disposition": "resolved",
                    "evidence": "note: token bearer abcdefghijklmnopqrstuvwx",
                }
            ],
        }
        text = v2.render_task_packet(c)
        assert "abcdefghijklmnopqrstuvwx" not in text
