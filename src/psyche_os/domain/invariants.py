"""Domain invariants and validation.

All invariants from DATA_MODEL.md §15:
1. At most one active semantic version per record_id.
2. Transaction intervals do not overlap.
3. Every derived output has exactly one valid DerivationRun.
4. Source-near assertion has locator or explicit unavailable reason.
5. Active claim has at least one evidence link or is unsupported_proposal.
6. Causal claim requires causal-design record.
7. Score result references approved instrument/algorithm.
8. NEVER_CLOUD ancestry yields NEVER_CLOUD.
9. No content in AuditEvent.
10. Deleted roots don't appear in canonical queries.
11. Model snapshot is immutable and pins cut-offs.
12. Unknown/declined/missing/not-applicable distinguishable.
13. Every blob referenced authenticates; unreferenced blobs quarantined.
14. Restore validates manifests/schema before activation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from psyche_os.domain.entities import ClaimStatus, ClaimType


@dataclass(frozen=True, slots=True)
class InvariantViolation:
    """A named invariant failure."""

    invariant_id: int
    record_id: str
    detail: str
    severity: str = "error"  # error, warning


def _get_attr(obj: Any, key: str, default: Any = None) -> Any:
    """Get value from either a dict or an object attribute."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _is_none(obj: Any, key: str) -> bool:
    """Check if a field is None, working on both dicts and objects."""
    if isinstance(obj, dict):
        return obj.get(key) is None
    return getattr(obj, key, None) is None


def check_single_active_version(
    versions: list[Any],
) -> list[InvariantViolation]:
    """Invariant 1: At most one active version (transaction_to is None) per record_id."""
    violations: list[InvariantViolation] = []

    # Group by record_id
    from collections import defaultdict

    by_record: dict[str, list[Any]] = defaultdict(list)
    for v in versions:
        rid = str(_get_attr(v, "record_id", "unknown"))
        by_record[rid].append(v)

    for rid, rec_versions in by_record.items():
        active_count = sum(1 for v in rec_versions if _is_none(v, "transaction_to"))
        if active_count > 1:
            violations.append(
                InvariantViolation(
                    invariant_id=1,
                    record_id=rid,
                    detail=f"{active_count} active versions for record",
                    severity="error",
                )
            )
    return violations


def check_transaction_interval_non_overlapping(
    versions: list[Any],
) -> list[InvariantViolation]:
    """Invariant 2: Transaction intervals [from, to) do not overlap for same record."""
    violations: list[InvariantViolation] = []
    intervals = sorted(
        [
            (_get_attr(v, "transaction_from"), _get_attr(v, "transaction_to"))
            for v in versions
            if _get_attr(v, "transaction_from") is not None
        ],
        key=lambda x: x[0],
    )
    for i in range(len(intervals) - 1):
        prev_to = intervals[i][1]
        next_from = intervals[i + 1][0]
        if prev_to is not None and next_from is not None and prev_to > next_from:
            record_id = _get_attr(versions[0], "record_id", "unknown") if versions else "unknown"
            violations.append(
                InvariantViolation(
                    invariant_id=2,
                    record_id=str(record_id),
                    detail=f"Overlapping intervals: [{intervals[i]}, {intervals[i + 1]})",
                    severity="error",
                )
            )
    return violations


def check_source_locator_or_reason(
    record: dict[str, Any],
) -> list[InvariantViolation]:
    """Invariant 4: Source-near assertion has locator or unavailable reason."""
    violations: list[InvariantViolation] = []
    has_locator = bool(record.get("source_locator_id"))
    has_reason = bool(record.get("source_unavailable_reason"))
    if not has_locator and not has_reason:
        violations.append(
            InvariantViolation(
                invariant_id=4,
                record_id=str(record.get("record_id", "unknown")),
                detail="Source-near assertion has no locator and no unavailable reason",
                severity="error",
            )
        )
    return violations


def check_active_claim_evidence(
    claim: dict[str, Any],
    evidence_links: list[dict[str, Any]],
) -> list[InvariantViolation]:
    """Invariant 5: Active claim has evidence link or is unsupported_proposal."""
    violations: list[InvariantViolation] = []
    status = claim.get("status", "")
    if isinstance(status, ClaimStatus):
        status = status.value
    if status in ("active", "user_accepted"):
        has_evidence = any(
            link.get("target_claim_id") == claim.get("record_id") for link in evidence_links
        )
        # Check if explicitly marked as unsupported proposal
        is_unsupported = claim.get("origin") == "unsupported_proposal"
        if not has_evidence and not is_unsupported:
            violations.append(
                InvariantViolation(
                    invariant_id=5,
                    record_id=str(claim.get("record_id", "unknown")),
                    detail="Active claim has no evidence link and is not unsupported_proposal",
                    severity="error",
                )
            )
    return violations


def check_causal_claim_requires_design(
    claim: dict[str, Any],
) -> list[InvariantViolation]:
    """Invariant 6: Causal claim requires causal-design record. F0 blocks creation."""
    claim_type = claim.get("claim_type", "")
    if isinstance(claim_type, ClaimType):
        claim_type = claim_type.value
    if claim_type == "causal_hypothesis":
        violations: list[InvariantViolation] = [
            InvariantViolation(
                invariant_id=6,
                record_id=str(claim.get("record_id", "unknown")),
                detail="Causal/diagnostic claim creation is FAIL_CLOSED in F0",
                severity="error",
            )
        ]
        return violations
    return []


def check_audit_content_free(
    audit_record: dict[str, Any],
) -> list[InvariantViolation]:
    """Invariant 9: No content in audit event."""
    violations: list[InvariantViolation] = []
    forbidden_fields = {
        "content",
        "note_text",
        "assessment_responses",
        "filenames",
        "paths",
        "search_terms",
        "prompts",
        "diagnoses",
        "third_party_names",
        "keys",
        "tokens",
        "secrets",
        "exception_dumps",
        "content_hashes",
    }
    present = forbidden_fields & set(record.keys() for record in [audit_record])
    present = forbidden_fields & audit_record.keys()
    if present:
        violations.append(
            InvariantViolation(
                invariant_id=9,
                record_id=str(audit_record.get("event_id", "unknown")),
                detail=f"Audit record contains forbidden fields: {sorted(present)}",
                severity="error",
            )
        )
    return violations


def check_deleted_not_in_canonical(
    deleted_ids: set[str],
    canonical_ids: set[str],
) -> list[InvariantViolation]:
    """Invariant 10: Deleted roots and derivatives don't appear in canonical queries."""
    violations: list[InvariantViolation] = []
    found = deleted_ids & canonical_ids
    if found:
        violations.append(
            InvariantViolation(
                invariant_id=10,
                record_id="batch",
                detail=f"Deleted records still in canonical queries: {sorted(found)}",
                severity="error",
            )
        )
    return violations


def check_unknown_distinguishable(
    record: dict[str, Any],
) -> list[InvariantViolation]:
    """Invariant 12: Unknown reasons are distinguishable."""
    valid_reasons = {
        "not_observed",
        "not_asked",
        "declined",
        "forgotten",
        "not_applicable",
        "measurement_failed",
        "source_unavailable",
        "ambiguous",
        "rights_blocked",
    }
    reason = record.get("unknown_reason", "")
    if reason and reason not in valid_reasons:
        return [
            InvariantViolation(
                invariant_id=12,
                record_id=str(record.get("record_id", "unknown")),
                detail=f"Invalid unknown_reason: {reason}",
                severity="error",
            )
        ]
    return []
