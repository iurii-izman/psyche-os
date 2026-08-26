from __future__ import annotations

import pytest

from psyche_os.personal_mode.ai_working_formulation import PersonalAIError, validate_working_formulation


def proposal(text: str = "Это может быть предварительная формулировка на основе выбранного текста.") -> dict[str, object]:
    return {"schema_version": "personal-working-formulation-v1", "proposal_id": "synthetic-proposal", "status": "PROPOSED", "formulation": {"text": text, "supporting_turn_ids": ["turn-1"], "uncertainty": "Контекст ограничен выбранными записями."}}


def test_valid_working_formulation_is_local_proposal_only() -> None:
    value = validate_working_formulation(proposal(), {"turn-1"})
    assert value["status"] == "PROPOSED"
    assert value["formulation"]["supporting_turn_ids"] == ["turn-1"]


@pytest.mark.parametrize("text", [
    "У вас диагноз депрессия.", "Вам следует начать лечение.",
    "You should take medication.", "I know your hidden motives.",
    "Это доказывает вытесненную память.", "Это паранойя.",
])
def test_ru_en_unsafe_or_directive_formulation_is_rejected(text: str) -> None:
    with pytest.raises(PersonalAIError) as exc:
        validate_working_formulation(proposal(text), {"turn-1"})
    assert exc.value.code == "AI_OUTPUT_UNSAFE"


def test_invented_or_missing_source_is_rejected() -> None:
    invalid = proposal()
    invalid["formulation"]["supporting_turn_ids"] = ["invented"]
    with pytest.raises(PersonalAIError) as exc:
        validate_working_formulation(invalid, {"turn-1"})
    assert exc.value.code == "AI_OUTPUT_REJECTED"
