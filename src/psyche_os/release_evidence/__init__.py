"""Exact-candidate, fail-closed E11 release-evidence evaluation."""

from .e11_gate import EvaluationOutcome, evaluate_evaluation, load_evaluation, seal_evaluation

__all__ = ["EvaluationOutcome", "evaluate_evaluation", "load_evaluation", "seal_evaluation"]
