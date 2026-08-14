"""Immutable E08 import values and deterministic security identities."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
import hashlib
import json
from typing import Any, Final


def identity_digest(value: Any) -> str:
    """Return a deterministic identity for non-secret security metadata."""
    encoded = json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class PlainTextResourceProfile:
    profile_id: str = "utf8-plain-text-v1"
    maximum_original_bytes: int = 1_048_576
    maximum_code_points: int = 1_000_000
    maximum_physical_lines: int = 4_096
    maximum_line_code_points: int = 16_384
    maximum_segments: int = 4_096

    @property
    def identity(self) -> str:
        return identity_digest(asdict(self))


PLAIN_TEXT_PROFILE: Final = PlainTextResourceProfile()


class CanonicalMapping(StrEnum):
    ATTRIBUTED_VERBATIM_REPORT = "attributed_verbatim_report"
    REVIEW_NEEDED_ASSERTION_PROPOSAL = "review_needed_assertion_proposal"


@dataclass(frozen=True, slots=True)
class ParsedSegment:
    segment_id: str
    source_version_id: str
    physical_line: int
    character_start: int
    character_end: int
    byte_start: int
    byte_end: int
    newline: str
    text: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class ParsedImportCandidate:
    candidate_id: str
    candidate_version: str
    quarantine_id: str
    source_candidate_id: str
    source_version_id: str
    protected_digest_ref: str
    byte_count: int
    encoding: str
    bom: bool
    profile_id: str
    profile_identity: str
    parser_name: str
    parser_version: str
    parser_config_digest: str
    character_count: int
    physical_line_count: int
    segment_count: int
    transformations: tuple[str, ...]
    segments: tuple[ParsedSegment, ...]
    untrusted_content: bool
    policy_lineage_id: str


@dataclass(frozen=True, slots=True)
class ImportTransformation:
    segment_id: str
    kind: str
    method_version: str
    replacement: str | None = None

    def __repr__(self) -> str:
        replacement = "None" if self.replacement is None else "<redacted>"
        return (
            f"ImportTransformation(segment_id={self.segment_id!r}, kind={self.kind!r}, "
            f"method_version={self.method_version!r}, replacement={replacement})"
        )


@dataclass(frozen=True, slots=True)
class ProposedMapping:
    segment_id: str
    mapping: CanonicalMapping


@dataclass(frozen=True, slots=True)
class ImportPreview:
    preview_id: str
    candidate_id: str
    source_type: str
    profile_id: str
    byte_count: int
    character_count: int
    physical_line_count: int
    segment_count: int
    encoding: str
    bom: bool
    parser_identity: str
    mappings: tuple[ProposedMapping, ...]
    transformations: tuple[ImportTransformation, ...]
    escaped_samples: tuple[str, ...]
    samples_truncated: bool
    privacy_effect: str
    policy_lineage_id: str
    deletion_implication: str
    duplicate_decision: str
    correction_of: str | None = None
    urls_active: bool = False
    markdown_active: bool = False
