"""E10 deterministic professional handoff report model and builder.

The report is a derived informational copy over explicitly selected canonical
records for one frozen profile (``personal_informational_consultation_handoff``,
audience ``mental_health_professional``).  It:

- preserves canonical provenance/epistemic status without inventing new
  interpretation;
- automatically includes materially linked counterevidence under accepted
  canonical relations only;
- applies previewed redaction/exclusion without ever mutating canonical data;
- serializes to deterministic UTF-8 Markdown plus a deterministic JSON manifest
  (manifest carries identity/provenance metadata, never content excerpts);
- is never canonical truth, a medical record, diagnosis, clinical decision
  support, treatment guidance, or synchronized professional access.

No AI, network, provider, or new runtime dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import re
from typing import Any

from psyche_os.projections.e09_lexical import RelationRef, relation_expansion

AUDIENCE = "mental_health_professional"
PURPOSE = "professional_consultation_handoff"
PROFILE_ID = "personal_informational_consultation_handoff"
REPORT_VERSION = "e10-report-v1"
BUILDER_VERSION = "e10-professional-builder-v1"
CONFIG_VERSION = "e10-professional-config-v1"
OUTPUT_FORMAT = "markdown+json"
DISCLOSURE_STATE = "pending_user_delivery"

REPORT_SECTIONS: tuple[str, ...] = (
    "intended_use",
    "selected_records",
    "linked_counterevidence",
    "excluded_records",
    "external_copy_notice",
)

INTENDED_USE_TEXT = (
    "This report is a personal informational consultation handoff: one adult "
    "owner manually provides selected information to a mental-health "
    "professional. It is a derived informational copy. It is not canonical "
    "truth, a medical record, diagnosis, clinical decision support, treatment "
    "guidance, or synchronized professional access."
)

EXTERNAL_COPY_NOTICE = (
    "This report is an external copy of selected synthetic records. "
    "Corrections or deletions made in the vault do not update, delete, or "
    "invalidate copies already shared outside the vault."
)

# Unresolved qualified approvals for the frozen profile.  Recorded truthfully
# as PENDING_QUALIFIED_REVIEW; never invented or waived.
PENDING_REVIEW_ITEMS: tuple[tuple[str, str], ...] = (
    ("legal_regulatory_approval", "legal/regulatory approval"),
    ("privacy_rights_approval", "privacy/rights approval"),
    ("clinical_safety_approval", "clinical-safety approval"),
    ("human_factors_approval", "human-factors approval"),
)

_CONTRADICTION_ROLES = frozenset(
    {"contradicts", "contradicted_by", "counters", "counterevidence"}
)

# Canonical text-bearing tables used for report extraction.  Each entry is
# (table, active-row filter, ordered (label, column) pairs, kind label).
# Mirrors the frozen E09 semantic sources; unknowns has no semantic_version.
_RECORD_SOURCES: tuple[tuple[str, str, tuple[tuple[str, str], ...], str], ...] = (
    (
        "source_artifacts",
        "is_active=1 AND semantic_version=2",
        (
            ("record_id", "record_id"),
            ("version_id", "version_id"),
            ("kind", "source_kind"),
            ("label", "source_label"),
            ("path", "uri_or_path"),
            ("mime", "mime_type"),
            ("rights_note", "rights_note"),
        ),
        "source",
    ),
    (
        "reports",
        "is_active=1 AND semantic_version=2",
        (
            ("record_id", "record_id"),
            ("version_id", "version_id"),
            ("title", "title"),
            ("kind", "report_kind"),
            ("content", "verbatim_content"),
        ),
        "verbatim_report",
    ),
    (
        "observations",
        "is_active=1 AND semantic_version=2",
        (
            ("record_id", "record_id"),
            ("version_id", "version_id"),
            ("kind", "observation_kind"),
            ("phenomenon", "construct_phenomenon"),
            ("value", "value_or_coded_state"),
            ("context", "context"),
        ),
        "observation",
    ),
    (
        "assertions",
        "is_active=1 AND semantic_version=2",
        (
            ("record_id", "record_id"),
            ("version_id", "version_id"),
            ("assertion_type", "assertion_type"),
            ("predicate", "predicate"),
            ("object_value", "object_value"),
            ("scope", "scope"),
            ("modality", "modality"),
            ("negation", "negation"),
        ),
        "assertion",
    ),
    (
        "claims",
        "is_active=1 AND semantic_version=2",
        (
            ("record_id", "record_id"),
            ("version_id", "version_id"),
            ("claim_type", "claim_type"),
            ("claim_status", "claim_status"),
            ("claim_origin", "claim_origin"),
            ("proposition", "proposition"),
            ("bounded_wording", "bounded_wording"),
        ),
        "claim",
    ),
    (
        "unknowns",
        "is_active=1",
        (
            ("record_id", "record_id"),
            ("version_id", "version_id"),
            ("question", "question"),
            ("scope", "scope"),
            ("why_matters", "why_matters"),
            ("status", "status"),
        ),
        "unknown",
    ),
)

_MD_META = frozenset("\\`*_{}[]<>()#+-.!|")


def _digest(value: Any) -> str:
    """Deterministic SHA-256 identity over JSON-serialisable metadata."""
    encoded = json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _escape_text(text: str) -> str:
    """Make hostile/untrusted text inert and literal for Markdown output.

    Backslash-escapes Markdown metacharacters so HTML, links, emphasis and
    headings render literally; control and bidi characters are replaced; the
    text is never interpreted as instructions or markup.
    """
    out: list[str] = []
    for ch in text:
        if ch == "\n":
            out.append("\n")
        elif ch == "\t":
            out.append("    ")
        elif ch.isprintable():
            out.append("\\" + ch if ch in _MD_META else ch)
        else:
            out.append("�")
    return "".join(out)


class E10ReportError(RuntimeError):
    """Typed E10 failure with a stable content-free code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class ReportConfig:
    """Frozen E10 profile configuration; its identity is part of the report."""

    profile: str = PROFILE_ID
    audience: str = AUDIENCE
    purpose: str = PURPOSE
    report_version: str = REPORT_VERSION
    builder_version: str = BUILDER_VERSION
    config_version: str = CONFIG_VERSION
    output_format: str = OUTPUT_FORMAT

    @property
    def identity(self) -> str:
        return _digest(
            {
                "profile": self.profile,
                "audience": self.audience,
                "purpose": self.purpose,
                "report_version": self.report_version,
                "builder_version": self.builder_version,
                "config_version": self.config_version,
                "output_format": self.output_format,
            }
        )


@dataclass(frozen=True, slots=True)
class RecordContent:
    """Rendered snapshot of one canonical record.  Raw text is never stored."""

    record_id: str
    version_id: str
    table: str
    kind: str
    fields: tuple[tuple[str, str], ...]

    def __repr__(self) -> str:
        return (
            f"RecordContent(record_id={self.record_id!r}, "
            f"version_id={self.version_id!r}, kind={self.kind!r}, "
            f"field_count={len(self.fields)!r})"
        )


@dataclass(frozen=True, slots=True)
class Redaction:
    """Previewed report transformation; never mutates canonical data."""

    record_id: str
    version_id: str
    field: str
    pattern: str

    def __repr__(self) -> str:
        return (
            f"Redaction(record_id={self.record_id!r}, version_id={self.version_id!r}, "
            f"field={self.field!r})"
        )


@dataclass(frozen=True, slots=True)
class Exclusion:
    """Previewed report exclusion of one selected record."""

    record_id: str
    version_id: str
    reason: str = "user_excluded"

    def __repr__(self) -> str:
        return (
            f"Exclusion(record_id={self.record_id!r}, version_id={self.version_id!r}, "
            f"reason={self.reason!r})"
        )


@dataclass(frozen=True, slots=True)
class ReportRecord:
    """One record rendered into a report candidate."""

    record_id: str
    version_id: str
    kind: str
    provenance: str
    content: RecordContent
    inclusion_reason: str  # "explicitly_selected" | "materially_linked_counterevidence"
    redactions: tuple[Redaction, ...] = ()

    def __repr__(self) -> str:
        return (
            f"ReportRecord(record_id={self.record_id!r}, version_id={self.version_id!r}, "
            f"kind={self.kind!r}, inclusion={self.inclusion_reason!r})"
        )


@dataclass(frozen=True, slots=True)
class ReportPreview:
    """Exact preview bound to a single-use authorization."""

    audience: str
    purpose: str
    profile: str
    selected_ids: tuple[tuple[str, str], ...]
    excluded_ids: tuple[tuple[str, str], ...]
    redactions: tuple[Redaction, ...]
    counterevidence_ids: tuple[tuple[str, str], ...]
    section_names: tuple[str, ...]
    uncertainty_record_count: int
    output_format: str
    external_copy_notice: str
    builder_version: str
    config_version: str
    policy_identity: str
    canonical_cutoff: str | None
    pending_review_items: tuple[str, ...]

    @property
    def digest(self) -> str:
        """Deterministic digest over every previewed decision."""
        return _digest(
            {
                "audience": self.audience,
                "purpose": self.purpose,
                "profile": self.profile,
                "selected_ids": self.selected_ids,
                "excluded_ids": self.excluded_ids,
                "redactions": [
                    (r.record_id, r.version_id, r.field, r.pattern) for r in self.redactions
                ],
                "counterevidence_ids": self.counterevidence_ids,
                "section_names": self.section_names,
                "uncertainty_record_count": self.uncertainty_record_count,
                "output_format": self.output_format,
                "external_copy_notice": self.external_copy_notice,
                "builder_version": self.builder_version,
                "config_version": self.config_version,
                "policy_identity": self.policy_identity,
                "canonical_cutoff": self.canonical_cutoff,
                "pending_review_items": self.pending_review_items,
            }
        )

    def __repr__(self) -> str:
        return (
            f"ReportPreview(audience={self.audience!r}, purpose={self.purpose!r}, "
            f"selected_count={len(self.selected_ids)!r}, "
            f"counterevidence_count={len(self.counterevidence_ids)!r})"
        )


@dataclass(frozen=True, slots=True)
class ReportIdentity:
    """Stable typed identity for future professional round-trip."""

    report_id: str
    report_version: str
    profile: str
    audience: str
    purpose: str
    canonical_cutoff: str | None
    selected_ids: tuple[tuple[str, str], ...]
    excluded_ids: tuple[tuple[str, str], ...]
    transformation_identity: str
    builder_version: str
    config_version: str
    policy_identity: str
    report_digest: str
    disclosure_state: str

    def __repr__(self) -> str:
        return (
            f"ReportIdentity(report_id={self.report_id!r}, "
            f"report_version={self.report_version!r}, disclosure={self.disclosure_state!r})"
        )


@dataclass(frozen=True, slots=True)
class ReportPackage:
    """Deterministic report: Markdown text plus JSON manifest."""

    identity: ReportIdentity
    preview: ReportPreview
    markdown: str
    manifest: dict[str, Any]

    def __repr__(self) -> str:
        return (
            f"ReportPackage(report_id={self.identity.report_id!r}, "
            f"report_version={self.identity.report_version!r})"
        )


def _render_value(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if value is None:
        return ""
    return str(value)


def resolve_record(
    connection: Any, record_id: str, version_id: str
) -> RecordContent | None:
    """Resolve an exact active canonical (record_id, version_id) to content."""
    for table, where, cols, kind in _RECORD_SOURCES:
        names = [column for _label, column in cols]
        row = connection.execute(
            f"SELECT {','.join(names)} FROM {table} "
            f"WHERE {where} AND record_id=? AND version_id=?",
            (record_id, version_id),
        ).fetchone()
        if row is None:
            continue
        fields = tuple(
            (label, _render_value(value))
            for (label, _column), value in zip(cols, row, strict=False)
            if value is not None and value != ""
        )
        return RecordContent(record_id, version_id, table, kind, fields)
    return None


def resolve_active(connection: Any, record_id: str) -> tuple[str, str] | None:
    """Resolve the active (record_id, version_id) for a record, if any."""
    for table, where, _cols, _kind in _RECORD_SOURCES:
        row = connection.execute(
            f"SELECT record_id, version_id FROM {table} "
            f"WHERE {where} AND record_id=?",
            (record_id,),
        ).fetchone()
        if row is not None:
            return (str(row[0]), str(row[1]))
    return None


def _contradiction_members(connection: Any, set_record_id: str) -> tuple[tuple[str, str], ...]:
    rows = connection.execute(
        "SELECT member_record_id, member_version_id FROM contradiction_members "
        "WHERE set_record_id=? ORDER BY member_record_id, member_version_id",
        (set_record_id,),
    ).fetchall()
    return tuple((str(row[0]), str(row[1])) for row in rows)


def collect_counterevidence_ids(
    connection: Any, effective_ids: tuple[tuple[str, str], ...]
) -> tuple[tuple[str, str], ...]:
    """Deterministically gather materially linked counterevidence record ids.

    Only accepted canonical relations are used (contradiction-set membership
    and contradicts-family evidence links).  No new contradiction is inferred.
    """
    if not effective_ids:
        return ()
    expansion: dict[str, tuple[RelationRef, ...]] = relation_expansion(
        connection, [rid for rid, _vid in effective_ids]
    )
    targets: set[tuple[str, str]] = set()
    for rid, vid in effective_ids:
        for ref in expansion.get(rid, ()):
            if ref.role == "contradiction_set":
                for member_id, member_vid in _contradiction_members(
                    connection, ref.related_record_id
                ):
                    if (member_id, member_vid) != (rid, vid):
                        targets.add((member_id, member_vid))
            elif ref.role in _CONTRADICTION_ROLES:
                resolved = resolve_active(connection, ref.related_record_id)
                if resolved is not None and resolved != (rid, vid):
                    targets.add(resolved)
        # A selected claim that directly names a contradiction set must not
        # be presented without that set's material.
        set_row = connection.execute(
            "SELECT contradiction_set_id FROM claims WHERE record_id=? AND version_id=? "
            "AND is_active=1 AND contradiction_set_id IS NOT NULL AND contradiction_set_id != ''",
            (rid, vid),
        ).fetchone()
        if set_row is not None and set_row[0]:
            for member_id, member_vid in _contradiction_members(
                connection, str(set_row[0])
            ):
                if (member_id, member_vid) != (rid, vid):
                    targets.add((member_id, member_vid))
    return tuple(sorted(targets))


def policy_identity_of(connection: Any) -> str:
    """Digest over active canonical policies (unchanged gate identity)."""
    rows = connection.execute(
        "SELECT record_id, policy_id, version_id, sensitivity, processing_location, "
        "cloud_policy, purpose, third_party_scope, retention_policy_id, export_rule, "
        "export_audience, lineage_rule FROM data_policies WHERE is_active=1 ORDER BY record_id"
    ).fetchall()
    return _digest([tuple(str(value) for value in row) for row in rows])


def canonical_cutoff_of(connection: Any) -> str | None:
    """Latest tx_from across the indexed canonical sources, if any."""
    cutoff: str | None = None
    for table, where, _cols, _kind in _RECORD_SOURCES:
        for (tx_from,) in connection.execute(
            f"SELECT tx_from FROM {table} WHERE {where} AND tx_from IS NOT NULL"
        ):
            if tx_from is not None and (cutoff is None or str(tx_from) > cutoff):
                cutoff = str(tx_from)
    return cutoff


def apply_redactions(
    content: RecordContent, redactions: tuple[Redaction, ...]
) -> RecordContent:
    """Return a redacted copy; canonical data is never touched."""
    if not redactions:
        return content
    fields = list(content.fields)
    for redaction in redactions:
        if (
            redaction.record_id != content.record_id
            or redaction.version_id != content.version_id
        ):
            continue
        pattern = re.compile(redaction.pattern)
        fields = [
            (label, pattern.sub("[REDACTED]", value) if label == redaction.field else value)
            for label, value in fields
        ]
    return replace(content, fields=tuple(fields))


def _provenance_label(content: RecordContent) -> str:
    values = dict(content.fields)
    kind = content.kind
    if kind == "source":
        return "source · " + (values.get("kind") or "unspecified")
    if kind == "verbatim_report":
        return "verbatim_report · " + (values.get("kind") or "unspecified")
    if kind == "observation":
        return "observation · " + (values.get("kind") or "unspecified")
    if kind == "assertion":
        modality = values.get("modality", "unspecified")
        if values.get("negation") == "1":
            modality = modality + " · negated"
        return "assertion · " + modality
    if kind == "claim":
        return (
            "claim · "
            + values.get("claim_type", "?")
            + " · "
            + values.get("claim_status", "?")
        )
    if kind == "unknown":
        return "unknown · " + values.get("status", "open")
    return kind


def _report_record(
    connection: Any,
    record_id: str,
    version_id: str,
    redactions: tuple[Redaction, ...],
    inclusion_reason: str,
) -> ReportRecord:
    content = resolve_record(connection, record_id, version_id)
    if content is None:
        raise E10ReportError("RECORD_UNAVAILABLE")
    targeted = tuple(
        r
        for r in redactions
        if (r.record_id, r.version_id) == (record_id, version_id)
    )
    redacted = apply_redactions(content, targeted)
    return ReportRecord(
        record_id,
        version_id,
        content.kind,
        _provenance_label(redacted),
        redacted,
        inclusion_reason,
        targeted,
    )


def build_report_records(
    connection: Any, preview: ReportPreview
) -> tuple[tuple[ReportRecord, ...], tuple[ReportRecord, ...]]:
    """Build selected and linked-counterevidence records for one preview."""
    selected = tuple(
        _report_record(connection, rid, vid, preview.redactions, "explicitly_selected")
        for rid, vid in preview.selected_ids
    )
    counterevidence = tuple(
        _report_record(
            connection, rid, vid, preview.redactions, "materially_linked_counterevidence"
        )
        for rid, vid in preview.counterevidence_ids
    )
    return selected, counterevidence


def transformation_identity(
    exclusions: tuple[Exclusion, ...], redactions: tuple[Redaction, ...]
) -> str:
    """Digest over every report transformation (exclusions and redactions)."""
    return _digest(
        {
            "exclusions": [
                (e.record_id, e.version_id, e.reason)
                for e in sorted(exclusions, key=lambda e: (e.record_id, e.version_id))
            ],
            "redactions": [
                (r.record_id, r.version_id, r.field, r.pattern)
                for r in sorted(redactions, key=lambda r: (r.record_id, r.version_id, r.field))
            ],
        }
    )


def render_markdown(
    selected: tuple[ReportRecord, ...],
    counterevidence: tuple[ReportRecord, ...],
    preview: ReportPreview,
    report_id: str,
    report_version: str,
) -> str:
    """Deterministic Markdown; all untrusted content is escaped literal text."""
    lines: list[str] = [
        "# Professional Handoff Report",
        "",
        f"**Audience:** {_escape_text(preview.audience)}",
        f"**Purpose:** {_escape_text(preview.purpose)}",
        f"**Profile:** {_escape_text(preview.profile)}",
        f"**Report version:** {_escape_text(report_version)}",
        f"**Report ID:** {_escape_text(report_id)}",
    ]
    if preview.canonical_cutoff:
        lines.append(f"**Canonical cutoff:** {_escape_text(preview.canonical_cutoff)}")
    lines.append("")
    lines.append("## Intended use")
    lines.append("")
    lines.extend(_escape_text(line) for line in INTENDED_USE_TEXT.splitlines())
    lines.append("")
    lines.append("**Unresolved qualified approvals for this profile:**")
    lines.append("")
    for _item_id, label in PENDING_REVIEW_ITEMS:
        lines.append(f"- {_escape_text(label)} — `PENDING_QUALIFIED_REVIEW`")
    lines.append("")
    lines.append("## Selected records")
    lines.append("")
    for record in selected:
        lines.extend(_render_record(record))
    if counterevidence:
        lines.append("")
        lines.append("## Linked counterevidence (automatically included)")
        lines.append("")
        for record in counterevidence:
            lines.extend(_render_record(record))
    if preview.excluded_ids:
        lines.append("")
        lines.append("## Excluded from this report")
        lines.append("")
        for rid, vid in preview.excluded_ids:
            lines.append(f"- {_escape_text(rid)} {_escape_text(vid)}")
    lines.append("")
    lines.append("## External-copy notice")
    lines.append("")
    lines.extend(_escape_text(line) for line in EXTERNAL_COPY_NOTICE.splitlines())
    lines.append("")
    return "\n".join(lines) + "\n"


def _render_record(record: ReportRecord) -> list[str]:
    lines: list[str] = [
        f"### {_escape_text(record.record_id)} · {_escape_text(record.version_id)}",
        "",
        f"provenance: {_escape_text(record.provenance)}",
        f"inclusion: {_escape_text(record.inclusion_reason)}",
    ]
    if record.redactions:
        lines.append(f"redactions: {len(record.redactions)}")
    lines.append("")
    lines.append("content:")
    for label, value in record.content.fields:
        if label in ("record_id", "version_id"):
            continue
        for line in value.splitlines() or [""]:
            lines.append(f"    {_escape_text(label)}: {_escape_text(line)}")
    lines.append("")
    return lines


def report_id_of(
    config: ReportConfig,
    selected_ids: tuple[tuple[str, str], ...],
    excluded_ids: tuple[tuple[str, str], ...],
    counterevidence_ids: tuple[tuple[str, str], ...],
    transformation: str,
    policy: str,
) -> str:
    """Deterministic non-content report identifier for professional round-trip."""
    return "e10-report-" + _digest(
        {
            "report_version": config.report_version,
            "profile": config.profile,
            "audience": config.audience,
            "purpose": config.purpose,
            "selected_ids": selected_ids,
            "excluded_ids": excluded_ids,
            "counterevidence_ids": counterevidence_ids,
            "transformation_identity": transformation,
            "policy_identity": policy,
        }
    )[:12]


def compute_identity(
    config: ReportConfig,
    selected_ids: tuple[tuple[str, str], ...],
    excluded_ids: tuple[tuple[str, str], ...],
    counterevidence_ids: tuple[tuple[str, str], ...],
    transformation: str,
    policy: str,
    canonical_cutoff: str | None,
    markdown: str,
) -> ReportIdentity:
    """Deterministic report identity; never derived from report content."""
    return ReportIdentity(
        report_id=report_id_of(
            config,
            selected_ids,
            excluded_ids,
            counterevidence_ids,
            transformation,
            policy,
        ),
        report_version=config.report_version,
        profile=config.profile,
        audience=config.audience,
        purpose=config.purpose,
        canonical_cutoff=canonical_cutoff,
        selected_ids=selected_ids,
        excluded_ids=excluded_ids,
        transformation_identity=transformation,
        builder_version=config.builder_version,
        config_version=config.config_version,
        policy_identity=policy,
        report_digest=_digest(markdown),
        disclosure_state=DISCLOSURE_STATE,
    )


def build_manifest(
    identity: ReportIdentity, preview: ReportPreview, records: tuple[ReportRecord, ...]
) -> dict[str, Any]:
    """Deterministic machine-readable manifest; carries no content excerpts."""
    return {
        "format": preview.output_format,
        "report_id": identity.report_id,
        "report_version": identity.report_version,
        "profile": identity.profile,
        "audience": identity.audience,
        "purpose": identity.purpose,
        "canonical_cutoff": identity.canonical_cutoff,
        "selected_ids": [list(pair) for pair in identity.selected_ids],
        "excluded_ids": [list(pair) for pair in identity.excluded_ids],
        "counterevidence_ids": [list(pair) for pair in preview.counterevidence_ids],
        "records": [
            {
                "record_id": record.record_id,
                "version_id": record.version_id,
                "kind": record.kind,
                "provenance": record.provenance,
                "inclusion": record.inclusion_reason,
                "redactions": [{"field": redaction.field} for redaction in record.redactions],
            }
            for record in records
        ],
        "transformations": {
            "identity": identity.transformation_identity,
            "redaction_count": sum(len(record.redactions) for record in records),
            "exclusion_count": len(identity.excluded_ids),
        },
        "builder_version": identity.builder_version,
        "config_version": identity.config_version,
        "policy_identity": identity.policy_identity,
        "report_digest": identity.report_digest,
        "disclosure_state": identity.disclosure_state,
        "external_copy_notice": EXTERNAL_COPY_NOTICE,
        "intended_use": INTENDED_USE_TEXT,
        "pending_qualified_review": [item_id for item_id, _label in PENDING_REVIEW_ITEMS],
    }


def manifest_bytes(manifest: dict[str, Any]) -> bytes:
    """Deterministic serialized manifest bytes."""
    return json.dumps(manifest, sort_keys=True, ensure_ascii=False, indent=2).encode(
        "utf-8"
    )
