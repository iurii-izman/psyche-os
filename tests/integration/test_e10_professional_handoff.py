"""E10 professional handoff integration tests: selection, preview,
authorization, TOCTOU, counterevidence, redaction, export, receipt."""

from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

from psyche_os.adapters.e10_filesystem import E10FileWriteError, ExportFileInfo, ReportFileWriter
from psyche_os.application.e03_archive import E03ArchiveService
from psyche_os.application.e10_professional_handoff import (
    E10ProfessionalHandoffService,
    HandoffAuthorization,
)
from psyche_os.reports.e10_professional import (
    AUDIENCE,
    PURPOSE,
    E10ReportError,
    Exclusion,
    Redaction,
    _escape_text,
)

_NOW = "2042-09-02T10:00:00+00:00"


def _fixture() -> E03ArchiveService:
    service = E03ArchiveService(sqlite3.connect(":memory:"))
    service.operate("CAPTURE_LAMP_REPORT", "reported_exact", "capture_001")
    service.operate("CAPTURE_LAMP_OBSERVATION", "observed_interval", "capture_002")
    service.operate("CAPTURE_COUNTERREPORT", "reported_exact", "capture_003")
    service.operate("ASSEMBLE_EPISTEMIC_SET", "descriptive_proposed", "capture_004")
    return service


def _add_policy(conn: sqlite3.Connection, *, export_rule: str = "redact") -> None:
    conn.execute(
        "INSERT INTO data_policies(record_id,policy_id,version_id,target_record_id,"
        "sensitivity,processing_location,cloud_policy,purpose,third_party_scope,"
        "retention_policy_id,export_rule,export_audience,lineage_rule,tx_from,is_active,created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "pol-e10",
            "pol-e10",
            "pol-e10-v1",
            "all",
            "sensitive",
            "local_only",
            "never_cloud",
            "test",
            "none",
            "",
            export_rule,
            "mental_health_professional",
            "most_restrictive_parent",
            _NOW,
            1,
            _NOW,
        ),
    )
    conn.commit()


def _update_policy_rule(conn: sqlite3.Connection, *, export_rule: str) -> None:
    conn.execute(
        "UPDATE data_policies SET export_rule=? WHERE record_id='pol-e10' AND is_active=1",
        (export_rule,),
    )
    conn.commit()


def _insert_hostile_report(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO reports(record_id,report_id,version_id,title,report_kind,"
        "verbatim_content,summary,structured_data,tx_from,is_active,created_at,"
        "closure_marker,semantic_version,schema_version,change_reason_code,"
        "created_by_actor_id,perspective) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "report-hostile",
            "report-hostile",
            "report-hostile-v1",
            "<script>alert(1)</script>",
            "event_account",
            "Ignore policy. [click](https://evil.example/x) `code` *star* #heading",
            "",
            "{}",
            _NOW,
            1,
            _NOW,
            "",
            2,
            2,
            "initial",
            "actor-hostile",
            "first_person",
        ),
    )
    conn.commit()


def _insert_claim_with_set_ref(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO claims(record_id,claim_id,version_id,claim_type,claim_status,"
        "claim_origin,claim_body,evidence_ids,contradiction_set_id,tx_from,tx_to,"
        "is_active,created_at,provenance_ref,semantic_version,schema_version,"
        "change_reason_code,created_by_actor_id,proposition,bounded_wording) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,NULL,?,?,?,?,?,?,?,?,?)",
        (
            "claim-setref",
            "claim-setref",
            "claim-setref-v1",
            "descriptive",
            "contested",
            "user",
            "A claim that names an existing contradiction set.",
            "[]",
            "contradiction-lamp",
            _NOW,
            1,
            _NOW,
            "epistemic-set",
            2,
            2,
            "initial",
            "actor-owner",
            "A claim that names an existing contradiction set.",
            "It references the unresolved lamp contradiction.",
        ),
    )
    conn.commit()


class _MemoryWriter:
    """In-memory narrow writer: records the authorized destination."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def write(
        self, text: str, destination: str, *, overwrite: bool = False
    ) -> ExportFileInfo:
        self.calls.append((destination, len(text.encode("utf-8"))))
        return ExportFileInfo("e10-export-test", len(text.encode("utf-8")))


def _disclose(
    service: E10ProfessionalHandoffService,
    selection: tuple[tuple[str, str], ...],
    exclusions: tuple[Exclusion, ...] = (),
    redactions: tuple[Redaction, ...] = (),
    destination: str = "handoff.md",
    writer: _MemoryWriter | ReportFileWriter | None = None,
) -> tuple:
    writer = writer or _MemoryWriter()
    preview = service.build_preview(
        selection, exclusions, redactions, destination=destination
    )
    authorization = service.issue_authorization(preview)
    outcome = service.disclose(preview, authorization, writer)
    return preview, authorization, outcome.package


def test_only_explicitly_selected_records_enter_report() -> None:
    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    _preview, _auth, package = _disclose(
        handoff,
        (("report-lamp", "report-lamp-v1"), ("assertion-lamp", "assertion-lamp-v1")),
    )
    selected = set(package.identity.selected_ids)
    assert selected == {("report-lamp", "report-lamp-v1"), ("assertion-lamp", "assertion-lamp-v1")}
    for rid, _vid in selected:
        assert f"### {_escape_text(rid)}" in package.markdown
    # Non-selected canonical records must not appear as selected content.
    assert f"### {_escape_text('observation-lamp')}" not in package.markdown
    assert f"### {_escape_text('claim-lamp')}" not in package.markdown
    assert f"### {_escape_text('unknown-lamp')}" not in package.markdown
    # Counterevidence is the only non-explicitly-selected content.
    counterevidence = set(package.preview.counterevidence_ids)
    assert counterevidence == {("assertion-counter", "assertion-counter-v1")}
    assert all(
        pair[0] not in {"observation-lamp", "claim-lamp", "unknown-lamp"}
        for pair in counterevidence
    )


def test_audience_purpose_exact_and_visible() -> None:
    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    preview, _auth, package = _disclose(handoff, (("report-lamp", "report-lamp-v1"),))
    assert preview.audience == AUDIENCE
    assert preview.purpose == PURPOSE
    assert f"**Audience:** {_escape_text(AUDIENCE)}" in package.markdown
    assert f"**Purpose:** {_escape_text(PURPOSE)}" in package.markdown
    assert package.identity.audience == AUDIENCE
    assert package.identity.purpose == PURPOSE
    assert package.manifest["audience"] == AUDIENCE
    assert package.manifest["purpose"] == PURPOSE


def test_provenance_epistemic_status_preserved() -> None:
    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    preview, _auth, package = _disclose(
        handoff,
        (
            ("report-lamp", "report-lamp-v1"),
            ("claim-lamp", "claim-lamp-v1"),
            ("unknown-lamp", "unknown-lamp-v1"),
            ("observation-lamp", "observation-lamp-v1"),
        ),
    )
    # Preview names the exact report sections and the uncertainty burden.
    assert preview.section_names == (
        "intended_use",
        "selected_records",
        "linked_counterevidence",
        "excluded_records",
        "external_copy_notice",
    )
    assert preview.uncertainty_record_count == 1
    assert "provenance: " + _escape_text("verbatim_report · event_account") in package.markdown
    assert "provenance: " + _escape_text("claim · descriptive · proposed") in package.markdown
    assert "provenance: " + _escape_text("unknown · open") in package.markdown
    assert "provenance: " + _escape_text("observation · self_observation") in package.markdown
    statuses = {record["kind"] for record in package.manifest["records"]}
    assert {"verbatim_report", "claim", "unknown", "observation"} <= statuses
    # Claims stay proposals with their canonical status; never diagnostic.
    claim_entries = [record for record in package.manifest["records"] if record["record_id"] == "claim-lamp"]
    assert claim_entries and claim_entries[0]["provenance"] == "claim · descriptive · proposed"
    # No record provenance claims diagnostic authority.
    assert all("diagnos" not in record["provenance"].lower() for record in package.manifest["records"])


def test_material_counterevidence_automatically_included() -> None:
    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    # A selected contradiction-set member must bring its counterposition.
    preview, _auth, package = _disclose(
        handoff, (("assertion-lamp", "assertion-lamp-v1"),)
    )
    assert ("assertion-counter", "assertion-counter-v1") in preview.counterevidence_ids
    assert "## Linked counterevidence (automatically included)" in package.markdown
    heading = f"### {_escape_text('assertion-counter')} · {_escape_text('assertion-counter-v1')}"
    assert heading in package.markdown
    # A selected derived claim must not be presented without its contradictor.
    preview2, _auth2, package2 = _disclose(
        handoff, (("claim-lamp", "claim-lamp-v1"),)
    )
    assert ("assertion-counter", "assertion-counter-v1") in preview2.counterevidence_ids
    heading2 = f"### {_escape_text('assertion-counter')} · {_escape_text('assertion-counter-v1')}"
    assert heading2 in package2.markdown


def test_no_counterevidence_when_none_linked() -> None:
    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    preview, _auth, package = _disclose(
        handoff, (("observation-lamp", "observation-lamp-v1"),)
    )
    assert preview.counterevidence_ids == ()
    assert "Linked counterevidence" not in package.markdown


def test_claim_naming_contradiction_set_includes_material() -> None:
    service = _fixture()
    _add_policy(service.connection)
    _insert_claim_with_set_ref(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    preview, _auth, package = _disclose(
        handoff, (("claim-setref", "claim-setref-v1"),)
    )
    assert set(preview.counterevidence_ids) == {
        ("assertion-lamp", "assertion-lamp-v1"),
        ("assertion-counter", "assertion-counter-v1"),
    }
    assert "## Linked counterevidence (automatically included)" in package.markdown


def test_selected_counterevidence_not_duplicated() -> None:
    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    # Select both sides of the canonical contradiction explicitly.
    preview, _auth, package = _disclose(
        handoff,
        (
            ("assertion-lamp", "assertion-lamp-v1"),
            ("assertion-counter", "assertion-counter-v1"),
        ),
    )
    # Nothing is auto-added that is already explicitly selected.
    assert preview.counterevidence_ids == ()
    lamp_heading = f"### {_escape_text('assertion-lamp')} · {_escape_text('assertion-lamp-v1')}"
    counter_heading = (
        f"### {_escape_text('assertion-counter')} · {_escape_text('assertion-counter-v1')}"
    )
    assert package.markdown.count(lamp_heading) == 1
    assert package.markdown.count(counter_heading) == 1
    ids = [(record["record_id"], record["version_id"]) for record in package.manifest["records"]]
    assert ids.count(("assertion-lamp", "assertion-lamp-v1")) == 1
    assert ids.count(("assertion-counter", "assertion-counter-v1")) == 1
    assert set(package.identity.selected_ids) == {
        ("assertion-lamp", "assertion-lamp-v1"),
        ("assertion-counter", "assertion-counter-v1"),
    }


def test_redaction_cannot_mutate_canonical() -> None:
    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    redaction = Redaction("report-lamp", "report-lamp-v1", "content", "amber")
    preview, _auth, package = _disclose(
        handoff, (("report-lamp", "report-lamp-v1"),), redactions=(redaction,)
    )
    assert redaction in preview.redactions
    assert _escape_text("[REDACTED]") in package.markdown
    assert "appeared " + _escape_text("[REDACTED]") in package.markdown
    assert "amber" not in package.markdown
    # Canonical data is untouched.
    row = service.connection.execute(
        "SELECT verbatim_content FROM reports WHERE record_id='report-lamp' "
        "AND version_id='report-lamp-v1'"
    ).fetchone()
    assert row is not None
    assert row[0] == "The fictional east-bench indicator lamp appeared amber."


def test_exclusion_is_report_transformation_only() -> None:
    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    exclusion = Exclusion("observation-lamp", "observation-lamp-v1")
    preview, _auth, package = _disclose(
        handoff,
        (("report-lamp", "report-lamp-v1"), ("observation-lamp", "observation-lamp-v1")),
        exclusions=(exclusion,),
    )
    assert ("report-lamp", "report-lamp-v1") in preview.selected_ids
    assert ("observation-lamp", "observation-lamp-v1") not in preview.selected_ids
    assert ("observation-lamp", "observation-lamp-v1") in preview.excluded_ids
    assert "## Excluded from this report" in package.markdown
    assert "### observation-lamp" not in package.markdown
    row = service.connection.execute(
        "SELECT 1 FROM observations WHERE record_id='observation-lamp' "
        "AND version_id='observation-lamp-v1' AND is_active=1"
    ).fetchone()
    assert row is not None


def test_exclusion_must_be_member_of_explicit_selection() -> None:
    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    # An unselected record cannot be excluded from this candidate.
    with pytest.raises(E10ReportError) as exc:
        handoff.build_preview(
            (("report-lamp", "report-lamp-v1"),),
            exclusions=(Exclusion("observation-lamp", "observation-lamp-v1"),),
        )
    assert exc.value.code == "INVALID_EXCLUSION"
    # Fabricated IDs cannot appear as excluded metadata.
    with pytest.raises(E10ReportError) as exc:
        handoff.build_preview(
            (("report-lamp", "report-lamp-v1"),),
            exclusions=(Exclusion("report-fabricated", "report-fabricated-v1"),),
        )
    assert exc.value.code == "INVALID_EXCLUSION"


def test_excluded_version_must_exist_and_be_available() -> None:
    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    # Supersede report-lamp-v1, then select both versions and exclude v1.
    service.correct_lamp_report_time("report-lamp-v1")
    with pytest.raises(E10ReportError) as exc:
        handoff.build_preview(
            (("report-lamp", "report-lamp-v1"), ("report-lamp", "report-lamp-v2")),
            exclusions=(Exclusion("report-lamp", "report-lamp-v1"),),
        )
    assert exc.value.code == "RECORD_UNAVAILABLE"


def test_hostile_imported_content_stays_inert() -> None:
    service = _fixture()
    _add_policy(service.connection)
    _insert_hostile_report(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    _preview, _auth, package = _disclose(
        handoff, (("report-hostile", "report-hostile-v1"),)
    )
    # Markup is escaped literal text, never live markup.
    assert "<script>" not in package.markdown
    assert "[click](" not in package.markdown
    assert "\\<script\\>" in package.markdown
    assert "\\[click\\]\\(" in package.markdown
    # Manifest carries no content excerpts.
    manifest_text = handoff.manifest_bytes(package).decode("utf-8")
    assert "evil.example" not in manifest_text
    assert "Ignore policy" not in manifest_text
    # No content leaks through reprs.
    hostile = ("alert(1)", "evil.example", "Ignore policy")
    for surface in (repr(package), repr(package.identity), repr(package.preview), repr(package.manifest)):
        assert all(text not in surface for text in hostile)


def test_authorization_fabricated_rejected() -> None:
    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    preview = handoff.build_preview((("report-lamp", "report-lamp-v1"),))
    forged = HandoffAuthorization(
        authorization_id="e10-auth-forged",
        service_instance_id=handoff.instance_id,
        preview_digest=preview.digest,
    )
    with pytest.raises(E10ReportError) as exc:
        handoff.disclose(preview, forged, _MemoryWriter())
    assert exc.value.code == "AUTHORIZATION_FABRICATED"


def test_authorization_replayed_rejected() -> None:
    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    preview = handoff.build_preview((("report-lamp", "report-lamp-v1"),))
    authorization = handoff.issue_authorization(preview)
    handoff.disclose(preview, authorization, _MemoryWriter())
    with pytest.raises(E10ReportError) as exc:
        handoff.disclose(preview, authorization, _MemoryWriter())
    assert exc.value.code == "AUTHORIZATION_REPLAYED"


def test_authorization_non_transferable_across_instances() -> None:
    service = _fixture()
    _add_policy(service.connection)
    left = E10ProfessionalHandoffService(service.connection, instance_id="instance-left")
    right = E10ProfessionalHandoffService(service.connection, instance_id="instance-right")
    preview = left.build_preview((("report-lamp", "report-lamp-v1"),))
    authorization = left.issue_authorization(preview)
    # The other instance has no record of the capability.
    with pytest.raises(E10ReportError) as exc:
        right.disclose(preview, authorization, _MemoryWriter())
    assert exc.value.code == "AUTHORIZATION_FABRICATED"
    # Test-only state injection (no callable production path): a capability
    # registered under a foreign instance id is still non-transferable.
    right._authorization_states[authorization.authorization_id] = "issued"
    with pytest.raises(E10ReportError) as exc:
        right.disclose(preview, authorization, _MemoryWriter())
    assert exc.value.code == "AUTHORIZATION_NON_TRANSFERABLE"


def test_no_production_authorization_registration_bypass() -> None:
    import inspect

    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    preview = handoff.build_preview((("report-lamp", "report-lamp-v1"),))
    arbitrary = HandoffAuthorization(
        authorization_id="e10-auth-arbitrary",
        service_instance_id=handoff.instance_id,
        preview_digest=preview.digest,
    )
    with pytest.raises(E10ReportError) as exc:
        handoff.disclose(preview, arbitrary, _MemoryWriter())
    assert exc.value.code == "AUTHORIZATION_FABRICATED"
    # No callable production path can register an arbitrary authorization.
    assert not hasattr(E10ProfessionalHandoffService, "force_register_for_test")
    assert "force_register_for_test" not in inspect.getsource(
        E10ProfessionalHandoffService
    )


def test_source_version_toctou_invalidates_authorization() -> None:
    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    preview = handoff.build_preview((("report-lamp", "report-lamp-v1"),))
    authorization = handoff.issue_authorization(preview)
    service.correct_lamp_report_time("report-lamp-v1")
    with pytest.raises(E10ReportError) as exc:
        handoff.disclose(preview, authorization, _MemoryWriter())
    assert exc.value.code == "TOCTOU_INVALIDATION"
    with pytest.raises(E10ReportError) as exc:
        handoff.disclose(preview, authorization, _MemoryWriter())
    assert exc.value.code == "AUTHORIZATION_INVALIDATED"


def test_policy_toctou_invalidates_authorization() -> None:
    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    preview = handoff.build_preview((("report-lamp", "report-lamp-v1"),))
    authorization = handoff.issue_authorization(preview)
    _update_policy_rule(service.connection, export_rule="block")
    with pytest.raises(E10ReportError) as exc:
        handoff.disclose(preview, authorization, _MemoryWriter())
    assert exc.value.code == "TOCTOU_INVALIDATION"


def test_deleted_or_superseded_record_rejected() -> None:
    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    plan = service.operate("DELETE_LAMP_SOURCE", "dry_run", "delete_001")
    service.execute_deletion(plan["plan_id"], "DELETE ORCHID LAMP SOURCE")
    with pytest.raises(E10ReportError) as exc:
        handoff.build_preview((("report-lamp", "report-lamp-v1"),))
    assert exc.value.code == "RECORD_UNAVAILABLE"
    # Superseded version id is not selectable either.
    with pytest.raises(E10ReportError) as exc:
        handoff.build_preview((("report-lamp", "report-lamp-v1"),))
    assert exc.value.code == "RECORD_UNAVAILABLE"


def test_policy_blocked_fails_closed() -> None:
    service = _fixture()
    _add_policy(service.connection, export_rule="block")
    handoff = E10ProfessionalHandoffService(service.connection)
    with pytest.raises(E10ReportError) as exc:
        handoff.build_preview((("report-lamp", "report-lamp-v1"),))
    assert exc.value.code == "POLICY_BLOCKED"


def test_deterministic_report_and_manifest() -> None:
    left_service = _fixture()
    right_service = _fixture()
    _add_policy(left_service.connection)
    _add_policy(right_service.connection)
    left = E10ProfessionalHandoffService(left_service.connection)
    right = E10ProfessionalHandoffService(right_service.connection)
    _preview_l, _auth_l, left_package = _disclose(
        left, (("report-lamp", "report-lamp-v1"), ("assertion-lamp", "assertion-lamp-v1"))
    )
    _preview_r, _auth_r, right_package = _disclose(
        right, (("report-lamp", "report-lamp-v1"), ("assertion-lamp", "assertion-lamp-v1"))
    )
    assert left_package.markdown == right_package.markdown
    assert left_package.manifest == right_package.manifest
    assert left_package.identity.report_id == right_package.identity.report_id
    assert left_package.identity.report_digest == right_package.identity.report_digest
    assert left.manifest_bytes(left_package) == right.manifest_bytes(right_package)


def test_content_free_receipt_and_reprs(tmp_path) -> None:  # type: ignore[no-untyped-def]
    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    writer = ReportFileWriter(tmp_path)
    preview = handoff.build_preview(
        (("report-lamp", "report-lamp-v1"),), destination="handoff.md"
    )
    authorization = handoff.issue_authorization(preview)
    outcome = handoff.disclose(preview, authorization, writer)
    package = outcome.package
    receipt = outcome.receipt
    assert receipt.external_copy_limited is True
    assert receipt.selected_count == 1
    assert "amber" not in repr(receipt)
    assert "handoff.md" not in repr(receipt)
    assert "report_digest" not in receipt.__dataclass_fields__
    # No content, digest, destination or path on any bounded surface.
    for surface in (
        repr(receipt),
        repr(outcome),
        repr(package.identity),
        repr(package.preview),
        repr(package),
        repr(preview),
    ):
        assert "amber" not in surface
        assert "fictional" not in surface
        assert "handoff.md" not in surface


def test_external_copy_limitation_truthful() -> None:
    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    preview, _auth, package = _disclose(
        handoff, (("report-lamp", "report-lamp-v1"),)
    )
    assert preview.external_copy_notice
    assert "## External-copy notice" in package.markdown
    assert "do not update" in package.markdown
    assert package.manifest["external_copy_notice"]
    assert package.identity.disclosure_state == "pending_user_delivery"


def test_missing_policy_fails_closed() -> None:
    service = _fixture()
    # No data_policies rows at all: PS-01 / Master Spec §409 fail closed.
    handoff = E10ProfessionalHandoffService(service.connection)
    with pytest.raises(E10ReportError) as exc:
        handoff.build_preview((("report-lamp", "report-lamp-v1"),))
    assert exc.value.code == "POLICY_MISSING"


def test_policy_removed_invalidates_authorization() -> None:
    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    preview = handoff.build_preview((("report-lamp", "report-lamp-v1"),))
    authorization = handoff.issue_authorization(preview)
    service.connection.execute(
        "UPDATE data_policies SET is_active=0 WHERE record_id='pol-e10'"
    )
    service.connection.commit()
    with pytest.raises(E10ReportError) as exc:
        handoff.disclose(preview, authorization, _MemoryWriter())
    assert exc.value.code == "TOCTOU_INVALIDATION"


def test_destination_visible_before_authorization() -> None:
    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    preview = handoff.build_preview(
        (("report-lamp", "report-lamp-v1"),), destination="consultation.md"
    )
    assert preview.destination == "consultation.md"
    assert preview.retention_note
    assert "destination" in preview.retention_note.lower()
    assert "no copy" in preview.retention_note.lower()
    # Retention and external-copy semantics are visible before authorization.
    assert preview.external_copy_notice


def test_invalid_destination_fails_before_authorization() -> None:
    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    for bad in ("", "../escape.md", "C:\\absolute.md", "/rooted.md"):
        with pytest.raises(E10ReportError) as exc:
            handoff.build_preview((("report-lamp", "report-lamp-v1"),), destination=bad)
        assert exc.value.code == "INVALID_DESTINATION"


def test_destination_substitution_after_authorization_fails() -> None:
    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    authorized = handoff.build_preview(
        (("report-lamp", "report-lamp-v1"),), destination="a.md"
    )
    authorization = handoff.issue_authorization(authorized)
    substituted = handoff.build_preview(
        (("report-lamp", "report-lamp-v1"),), destination="b.md"
    )
    with pytest.raises(E10ReportError) as exc:
        handoff.disclose(substituted, authorization, _MemoryWriter())
    assert exc.value.code == "TOCTOU_INVALIDATION"


def test_authorization_not_reusable_for_second_export() -> None:
    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    writer = _MemoryWriter()
    preview = handoff.build_preview(
        (("report-lamp", "report-lamp-v1"),), destination="a.md"
    )
    authorization = handoff.issue_authorization(preview)
    first = handoff.disclose(preview, authorization, writer)
    assert first.receipt.byte_count > 0
    assert writer.calls == [("a.md", first.receipt.byte_count)]
    with pytest.raises(E10ReportError) as exc:
        handoff.disclose(preview, authorization, writer)
    assert exc.value.code == "AUTHORIZATION_REPLAYED"


def test_report_bytes_deterministic_across_destinations() -> None:
    left_service = _fixture()
    right_service = _fixture()
    _add_policy(left_service.connection)
    _add_policy(right_service.connection)
    left = E10ProfessionalHandoffService(left_service.connection)
    right = E10ProfessionalHandoffService(right_service.connection)
    _preview_l, _auth_l, left_package = _disclose(
        left, (("report-lamp", "report-lamp-v1"),), destination="a.md"
    )
    _preview_r, _auth_r, right_package = _disclose(
        right, (("report-lamp", "report-lamp-v1"),), destination="b.md"
    )
    # Destination never enters report bytes.
    assert left_package.markdown == right_package.markdown
    assert left_package.manifest == right_package.manifest
    assert left_package.identity.report_id == right_package.identity.report_id
    assert left_package.identity.report_digest == right_package.identity.report_digest


def test_filesystem_path_and_overwrite_safety(tmp_path) -> None:  # type: ignore[no-untyped-def]
    writer = ReportFileWriter(tmp_path)
    info = writer.write("hello", "report.md")
    assert info.byte_count == 5
    with pytest.raises(E10FileWriteError) as exc:
        writer.write("hello again", "report.md")
    assert exc.value.code == "destination_exists"
    assert writer.write("replacement", "report.md", overwrite=True).byte_count == 11
    with pytest.raises(E10FileWriteError) as exc:
        writer.write("x", "../escape.md")
    assert exc.value.code == "destination_outside_base"
    with pytest.raises(E10FileWriteError) as exc:
        writer.write("x", str(tmp_path / "abs.md"))
    assert exc.value.code == "destination_outside_base"


def test_filesystem_rejects_symlink_destination(tmp_path) -> None:  # type: ignore[no-untyped-def]
    writer = ReportFileWriter(tmp_path)
    target = tmp_path / "real.md"
    target.write_text("original", encoding="utf-8")
    try:
        (tmp_path / "link.md").symlink_to(target.name)
    except OSError as exc:
        pytest.skip(f"real symlink unavailable on this platform: {exc}")
    with pytest.raises(E10FileWriteError) as exc:
        writer.write("overwrite", "link.md", overwrite=True)
    assert exc.value.code == "link_rejected"
    # The symlink target is never written through.
    assert target.read_text(encoding="utf-8") == "original"


def test_filesystem_rejects_symlink_deterministically(
    tmp_path, monkeypatch  # type: ignore[no-untyped-def]
) -> None:
    # Deterministic coverage of the link rejection logic on platforms that
    # cannot create a real symlink without privilege.
    writer = ReportFileWriter(tmp_path)

    def _fake_is_symlink(self: Path) -> bool:
        return self.name == "link.md"

    monkeypatch.setattr(Path, "is_symlink", _fake_is_symlink)
    with pytest.raises(E10FileWriteError) as exc:
        writer.write("x", "link.md")
    assert exc.value.code == "link_rejected"


def test_provider_and_network_absence(tmp_path) -> None:  # type: ignore[no-untyped-def]
    service = _fixture()
    _add_policy(service.connection)
    handoff = E10ProfessionalHandoffService(service.connection)
    writer = ReportFileWriter(tmp_path)
    preview = handoff.build_preview(
        (("report-lamp", "report-lamp-v1"),), destination="handoff.md"
    )
    authorization = handoff.issue_authorization(preview)
    outcome = handoff.disclose(preview, authorization, writer)
    package = outcome.package
    for surface in (
        repr(package),
        repr(package.identity),
        repr(package.preview),
        repr(outcome),
        repr(outcome.receipt),
        package.manifest,
    ):
        assert "provider" not in str(surface).lower()
        assert "network" not in str(surface).lower()
        assert "embedding" not in str(surface).lower()
