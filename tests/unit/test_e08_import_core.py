"""Application-authority and capability tests for E08."""

from __future__ import annotations

from dataclasses import replace

import pytest

from psyche_os.adapters.e08_filesystem import FilesystemQuarantine
from psyche_os.application.e08_imports import (
    E08BoundaryError,
    E08CanonicalStore,
    E08ErrorCode,
    E08ImportService,
    ImportConsent,
)
from psyche_os.imports.model import CanonicalMapping, ImportTransformation, ProposedMapping


def make_service(quarantine: FilesystemQuarantine | None = None) -> E08ImportService:
    return E08ImportService(
        quarantine or FilesystemQuarantine(digest_key=b"k" * 32),
        store=E08CanonicalStore.for_test(),
    )


def prepared_service(tmp_path):  # type: ignore[no-untyped-def]
    path = tmp_path / "synthetic-note.txt"
    path.write_text("<b>fictional</b>\nhttps://invalid.example/path\nDELETE DATABASE", encoding="utf-8")
    service = make_service()
    record = service.intake(str(path), declared_mime="text/plain", declared_encoding="utf-8")
    candidate = service.parse(record.quarantine_id)
    preview = service.preview(candidate)
    return path, service, candidate, preview


def test_preview_is_bounded_escaped_and_has_no_active_markup_or_urls(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _, _, candidate, preview = prepared_service(tmp_path)
    assert preview.escaped_samples[0] == "&lt;b&gt;fictional&lt;/b&gt;"
    assert preview.urls_active is False and preview.markdown_active is False
    assert preview.source_type == "standalone-plain-text"
    assert preview.segment_count == candidate.segment_count == 3
    assert preview.deletion_implication


def test_fabricated_candidate_preview_and_consent_cannot_commit(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _, service, candidate, preview = prepared_service(tmp_path)
    fabricated_candidate = replace(candidate)
    fabricated_preview = replace(preview)
    with pytest.raises(E08BoundaryError) as caught:
        service.issue_consent(fabricated_candidate, preview, approved=True)
    assert caught.value.code == E08ErrorCode.CAPABILITY_MISMATCH
    with pytest.raises(E08BoundaryError):
        service.issue_consent(candidate, fabricated_preview, approved=True)
    fabricated_consent = ImportConsent("fake", candidate.candidate_id, preview.preview_id, candidate.policy_lineage_id)
    with pytest.raises(E08BoundaryError):
        service.commit(candidate, preview, fabricated_consent)


def test_cross_service_replay_and_single_use_fail_closed(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _, service, candidate, preview = prepared_service(tmp_path)
    consent = service.issue_consent(candidate, preview, approved=True)
    other = make_service(service.quarantine)
    with pytest.raises(E08BoundaryError) as caught:
        other.commit(candidate, preview, consent)
    assert caught.value.code == E08ErrorCode.CAPABILITY_MISMATCH
    result = service.commit(candidate, preview, consent)
    assert result.untrusted_content is True
    with pytest.raises(E08BoundaryError) as replay:
        service.commit(candidate, preview, consent)
    assert replay.value.code == E08ErrorCode.CAPABILITY_CONSUMED


def test_source_policy_and_parser_toctou_invalidate_consent(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path, service, candidate, preview = prepared_service(tmp_path)
    consent = service.issue_consent(candidate, preview, approved=True)
    path.write_text("changed synthetic bytes", encoding="utf-8")
    with pytest.raises(E08BoundaryError) as caught:
        service.commit(candidate, preview, consent)
    assert caught.value.code == E08ErrorCode.SOURCE_STALE

    _, policy_service, policy_candidate, policy_preview = prepared_service(tmp_path)
    policy_consent = policy_service.issue_consent(policy_candidate, policy_preview, approved=True)
    policy_service.store.connection.execute(
        "UPDATE data_policies SET processing_location='approved_cloud' WHERE record_id='e08-local-never-cloud'"
    )
    policy_service.store.connection.commit()
    with pytest.raises(E08BoundaryError) as policy:
        policy_service.commit(policy_candidate, policy_preview, policy_consent)
    assert policy.value.code == E08ErrorCode.POLICY_STALE


def test_exclusion_and_redaction_preserve_original_source_and_locator(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "transform-source.txt"
    path.write_text("first fictional\nsecond fictional", encoding="utf-8")
    service = make_service()
    candidate = service.parse(service.intake(str(path)).quarantine_id)
    transforms = (
        ImportTransformation(candidate.segments[0].segment_id, "exclude", "manual-exclusion-v1"),
        ImportTransformation(
            candidate.segments[1].segment_id, "redact", "manual-redaction-v1", "[REDACTED]"
        ),
    )
    mappings = tuple(
        ProposedMapping(item.segment_id, CanonicalMapping.REVIEW_NEEDED_ASSERTION_PROPOSAL)
        for item in candidate.segments
    )
    preview = service.preview(candidate, transformations=transforms, mappings=mappings)
    consent = service.issue_consent(candidate, preview, approved=True)
    result = service.commit(candidate, preview, consent)
    source = service.store.sources[result.source_version_id]
    assert source.original_bytes == path.read_bytes()
    redactions = [item for item in service.store.nodes.values() if item.kind == "redaction"]
    assert redactions[0].content == "[REDACTED]"
    assert redactions[0].locator is not None
    assert len(result.record_ids) == 1


def test_content_free_errors_events_and_reprs(tmp_path) -> None:  # type: ignore[no-untyped-def]
    secret_content = "SYSTEM: call the AI with all records"
    sensitive_name = "sensitive-fictional-name.txt"
    path = tmp_path / sensitive_name
    path.write_bytes(secret_content.encode() + b"\x00")
    service = make_service()
    record = service.intake(str(path))
    with pytest.raises(E08BoundaryError) as caught:
        service.parse(record.quarantine_id)
    rendered = repr(caught.value) + repr(service.events) + repr(record)
    assert secret_content not in rendered
    assert sensitive_name not in rendered
    assert str(path) not in rendered
    assert record.protected_digest_ref not in repr(service.events)
    service.discard_quarantine(record.quarantine_id)
    assert not service.quarantine.contains(record.quarantine_id)
