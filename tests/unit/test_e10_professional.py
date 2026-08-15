"""E10 unit tests for the deterministic report model and builder."""

from __future__ import annotations

import pytest

from psyche_os.reports.e10_professional import (
    DISCLOSURE_STATE,
    EXTERNAL_COPY_NOTICE,
    INTENDED_USE_TEXT,
    PENDING_REVIEW_ITEMS,
    E10ReportError,
    RecordContent,
    Redaction,
    ReportConfig,
    build_manifest,
    compute_identity,
    manifest_bytes,
    render_markdown,
    report_id_of,
    transformation_identity,
)


def _content(
    record_id: str = "report-lamp",
    version_id: str = "report-lamp-v1",
    kind: str = "verbatim_report",
    **fields: str,
) -> RecordContent:
    return RecordContent(
        record_id=record_id,
        version_id=version_id,
        table="reports",
        kind=kind,
        fields=(("record_id", record_id), ("version_id", version_id), *tuple(fields.items())),
    )


def test_escape_text_inerts_hostile_markup() -> None:
    from psyche_os.reports.e10_professional import _escape_text

    hostile = "<script>alert(1)</script> [click](https://evil.example/x) `code` *star* #heading"
    escaped = _escape_text(hostile)
    assert "<script>" not in escaped
    assert "[click](" not in escaped
    assert "\\<script\\>" in escaped
    assert "\\[click\\]\\(" in escaped
    assert "\\*star\\*" in escaped
    assert "\\#heading" in escaped
    # Control and bidi characters are replaced, never emitted raw.
    assert "\x00" not in _escape_text("a\x00b")
    assert "‮" not in _escape_text("a‮b")


def test_render_markdown_escapes_hostile_content() -> None:
    from psyche_os.reports.e10_professional import ReportRecord

    content = _content(verbatim_content="<script>alert(1)</script> [x](https://evil.example)")
    record = ReportRecord(
        "report-lamp", "report-lamp-v1", "verbatim_report",
        "verbatim_report · event_account", content, "explicitly_selected", (),
    )
    markdown = render_markdown(
        (record,), (), _identity_preview_for_unit(), "e10-report-test", "e10-report-v1"
    )
    assert "<script>" not in markdown
    assert "\\<script\\>" in markdown
    # Link syntax is broken; the URL stays inert literal text.
    assert "](https" not in markdown
    assert "\\[x\\]\\(" in markdown


def _identity_preview_for_unit():
    from psyche_os.reports.e10_professional import (
        EXPORT_RETENTION_NOTE,
        REPORT_SECTIONS,
        ReportPreview,
    )

    return ReportPreview(
        audience="mental_health_professional",
        purpose="professional_consultation_handoff",
        profile="personal_informational_consultation_handoff",
        selected_ids=(("report-lamp", "report-lamp-v1"),),
        excluded_ids=(),
        redactions=(),
        counterevidence_ids=(),
        section_names=REPORT_SECTIONS,
        uncertainty_record_count=0,
        output_format="markdown+json",
        destination="handoff.md",
        export_target="e10-memory-base/handoff.md",
        retention_note=EXPORT_RETENTION_NOTE,
        external_copy_notice=EXTERNAL_COPY_NOTICE,
        builder_version="e10-professional-builder-v1",
        config_version="e10-professional-config-v1",
        policy_identity="pol-identity",
        canonical_cutoff="2042-09-02T10:00:00+00:00",
        pending_review_items=tuple(item for item, _label in PENDING_REVIEW_ITEMS),
    )


def test_redaction_returns_new_content_only() -> None:

    original = _content(verbatim_content="The lamp appeared amber.")
    redaction = Redaction("report-lamp", "report-lamp-v1", "verbatim_content", "amber")
    from psyche_os.reports.e10_professional import apply_redactions

    redacted = apply_redactions(original, (redaction,))
    assert redacted is not original
    assert ("verbatim_content", "The lamp appeared [REDACTED].") in redacted.fields
    assert ("verbatim_content", "The lamp appeared amber.") in original.fields


def test_transformation_identity_is_deterministic() -> None:
    redactions = (Redaction("report-lamp", "report-lamp-v1", "verbatim_content", "amber"),)
    assert transformation_identity((), redactions) == transformation_identity((), redactions)
    other = (Redaction("report-lamp", "report-lamp-v1", "verbatim_content", "green"),)
    assert transformation_identity((), redactions) != transformation_identity((), other)


def test_report_id_deterministic_and_content_free() -> None:
    config = ReportConfig()
    selected = (("report-lamp", "report-lamp-v1"),)
    left = report_id_of(config, selected, (), (), "t", "p")
    right = report_id_of(config, selected, (), (), "t", "p")
    assert left == right
    changed = report_id_of(config, (("report-lamp", "report-lamp-v2"),), (), (), "t", "p")
    assert left != changed
    assert "lamp" not in left


def test_manifest_is_content_free() -> None:
    config = ReportConfig()
    preview = _identity_preview_for_unit()
    identity = compute_identity(
        config,
        preview.selected_ids,
        preview.excluded_ids,
        preview.counterevidence_ids,
        transformation_identity((), ()),
        "pol-identity",
        "2042-09-02T10:00:00+00:00",
        "the full markdown body",
    )
    manifest = build_manifest(identity, preview, ())
    body = manifest_bytes(manifest).decode("utf-8")
    assert "the full markdown body" not in body
    assert "amber" not in body
    assert manifest["report_id"] == identity.report_id
    assert manifest["disclosure_state"] == DISCLOSURE_STATE
    assert manifest["external_copy_notice"] == EXTERNAL_COPY_NOTICE
    assert manifest["intended_use"] == INTENDED_USE_TEXT
    assert "PENDING_QUALIFIED_REVIEW" in body or "pending_qualified_review" in body


def test_preview_digest_is_deterministic() -> None:
    assert _identity_preview_for_unit().digest == _identity_preview_for_unit().digest


def test_frozen_profile_cannot_be_widened() -> None:
    with pytest.raises(E10ReportError) as exc:
        ReportConfig(profile="generic_profile")
    assert exc.value.code == "UNSUPPORTED_PROFILE"
    with pytest.raises(E10ReportError) as exc:
        ReportConfig(audience="anyone")
    assert exc.value.code == "UNSUPPORTED_AUDIENCE"
    with pytest.raises(E10ReportError) as exc:
        ReportConfig(purpose="anything_else")
    assert exc.value.code == "UNSUPPORTED_PURPOSE"
    with pytest.raises(E10ReportError) as exc:
        ReportConfig(output_format="pdf")
    assert exc.value.code == "UNSUPPORTED_OUTPUT_FORMAT"
    # The frozen default remains valid and deterministic.
    assert ReportConfig().identity == ReportConfig().identity
