"""Personal Mode v1 trusted-runtime boundaries.

These modules are deliberately unavailable to renderer-selected paths.  The
production admission evaluator is closed by default; tests inject decisions
directly into the composition root.
"""

from .admission import AdmissionDecision, PersonalAdmissionGuard, PersonalNotAdmitted
from .runtime_profile import PersonalRuntimePaths, RuntimeProfile

__all__ = [
    "AdmissionDecision",
    "PersonalAdmissionGuard",
    "PersonalNotAdmitted",
    "PersonalRuntimePaths",
    "RuntimeProfile",
]
