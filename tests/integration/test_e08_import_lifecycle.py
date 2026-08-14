"""Synthetic end-to-end E08 provenance, correction and deletion lifecycle."""

from __future__ import annotations

import pytest

from psyche_os.adapters.e08_filesystem import FilesystemQuarantine
from psyche_os.application.e08_imports import (
    E08BoundaryError,
    E08CanonicalStore,
    E08ErrorCode,
    E08ImportService,
)
from psyche_os.imports.model import CanonicalMapping, ProposedMapping


def make_service(*, key: bytes = b"k" * 32) -> E08ImportService:
    return E08ImportService(
        FilesystemQuarantine(digest_key=key), store=E08CanonicalStore.for_test()
    )


def commit_file(service: E08ImportService, path, *, correction_of=None):  # type: ignore[no-untyped-def]
    record = service.intake(str(path))
    candidate = service.parse(record.quarantine_id)
    mappings = tuple(
        ProposedMapping(item.segment_id, CanonicalMapping.REVIEW_NEEDED_ASSERTION_PROPOSAL)
        for item in candidate.segments
    )
    preview = service.preview(candidate, mappings=mappings, correction_of=correction_of)
    consent = service.issue_consent(candidate, preview, approved=True)
    return candidate, service.commit(candidate, preview, consent)


def test_import_mapping_keeps_source_segment_and_proposal_distinct(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "fictional-source.txt"
    path.write_text("The amber console may be active.", encoding="utf-8")
    service = make_service()
    candidate, result = commit_file(service, path)
    source = service.store.sources[result.source_version_id]
    segment = service.store.nodes[result.segment_ids[0]]
    proposal = service.store.nodes[result.record_ids[0]]

    assert source.source_version_id == segment.source_version_id == proposal.source_version_id
    assert source is not segment and segment is not proposal
    assert segment.kind == "source_segment" and proposal.kind == "review_needed_assertion_proposal"
    assert proposal.status == "review_needed"
    assert proposal.parent_ids == (segment.record_id,)
    locator = segment.locator
    assert locator is not None
    assert source.original_bytes[locator[3] : locator[4]].decode() == candidate.segments[0].text


def test_duplicate_requires_explicit_decision_and_never_silently_reimports(tmp_path) -> None:  # type: ignore[no-untyped-def]
    first = tmp_path / "first.txt"
    second = tmp_path / "renamed.txt"
    first.write_text("duplicate synthetic", encoding="utf-8")
    second.write_text("duplicate synthetic", encoding="utf-8")
    service = make_service(key=b"d" * 32)
    commit_file(service, first)
    candidate = service.parse(service.intake(str(second)).quarantine_id)
    with pytest.raises(E08BoundaryError) as caught:
        service.preview(candidate)
    assert caught.value.code == E08ErrorCode.DUPLICATE_DECISION_REQUIRED
    preview = service.preview(candidate, duplicate_decision="import_separate")
    result = service.commit(candidate, preview, service.issue_consent(candidate, preview, approved=True))
    assert result.source_version_id in service.store.sources


def test_correction_creates_new_immutable_source_and_explicit_relation(tmp_path) -> None:  # type: ignore[no-untyped-def]
    old_path = tmp_path / "old.txt"
    new_path = tmp_path / "new.txt"
    old_path.write_text("fictional amber console", encoding="utf-8")
    new_path.write_text("fictional green console", encoding="utf-8")
    service = make_service()
    _, old = commit_file(service, old_path)
    old_bytes = service.store.sources[old.source_version_id].original_bytes
    _, corrected = commit_file(service, new_path, correction_of=old.source_version_id)
    assert service.store.sources[old.source_version_id].original_bytes == old_bytes
    assert service.store.sources[old.source_version_id].state == "superseded"
    assert corrected.correction_of == old.source_version_id
    assert (
        service.store.sources[old.source_version_id].source_id,
        service.store.sources[corrected.source_version_id].source_id,
        "corrects",
    ) in service.store.relations


def test_deletion_closes_exclusive_graph_invalidates_mixed_and_preserves_unrelated(tmp_path) -> None:  # type: ignore[no-untyped-def]
    one = tmp_path / "one.txt"
    two = tmp_path / "two.txt"
    one.write_text("fictional source one", encoding="utf-8")
    two.write_text("fictional source two", encoding="utf-8")
    service = make_service()
    _, first = commit_file(service, one)
    _, unrelated = commit_file(service, two)
    mixed = service.store.add_mixed_derivative((first.record_ids[0], unrelated.record_ids[0]))
    plan = service.prepare_deletion(first.source_version_id)
    assert mixed in plan.invalidate_ids
    receipt = service.execute_deletion(plan, plan.confirmation)

    assert receipt.canonical_absence and receipt.export_absence and receipt.raw_storage_absence
    assert receipt.quarantine_removed
    assert service.store.nodes[mixed].status == "invalidated"
    assert service.store.nodes[mixed].content is None
    assert unrelated.source_version_id in service.store.sources
    assert service.store.active_content(unrelated.record_ids[0]) == "fictional source two"
    assert "fictional source one" not in repr(receipt)


def test_deletion_cancellation_stale_plan_and_fault_do_not_claim_partial_success(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "rollback.txt"
    path.write_text("fictional rollback source", encoding="utf-8")
    service = make_service()
    _, result = commit_file(service, path)
    cancelled = service.prepare_deletion(result.source_version_id)
    with pytest.raises(E08BoundaryError) as cancel:
        service.execute_deletion(cancelled, "cancel")
    assert cancel.value.code == E08ErrorCode.DELETION_CANCELLED
    assert result.source_version_id in service.store.sources

    stale = service.prepare_deletion(result.source_version_id)
    service.store.add_mixed_derivative((result.record_ids[0], result.segment_ids[0]))
    with pytest.raises(E08BoundaryError) as stale_error:
        service.execute_deletion(stale, stale.confirmation)
    assert stale_error.value.code == E08ErrorCode.DELETION_PLAN_STALE

    fresh = service.prepare_deletion(result.source_version_id)
    with pytest.raises(E08BoundaryError) as fault:
        service.execute_deletion(fresh, fresh.confirmation, inject_failure=True)
    assert fault.value.code == E08ErrorCode.STORAGE_FAILURE
    assert result.source_version_id in service.store.sources
    assert not service.store.receipts
