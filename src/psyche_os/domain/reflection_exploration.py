"""Non-canonical, session-scoped Guided Exploration vocabulary."""
from enum import StrEnum


class ContextKind(StrEnum):
    REPORTED = "REPORTED"
    UNKNOWN = "UNKNOWN"
    CONTRADICTION = "CONTRADICTION"


class HypothesisStatus(StrEnum):
    ACTIVE = "ACTIVE"
    WEAKENED = "WEAKENED"
    RETIRED = "RETIRED"


class HypothesisOrigin(StrEnum):
    USER = "USER"
    REFERENCE_PLANNER = "REFERENCE_PLANNER"


class QuestionStatus(StrEnum):
    PROPOSED = "PROPOSED"
    ASKED = "ASKED"
    ANSWERED = "ANSWERED"
    SKIPPED = "SKIPPED"


class FormulationStatus(StrEnum):
    PROPOSED = "PROPOSED"
    CURRENT = "CURRENT"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"
