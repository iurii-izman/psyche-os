"""Regression proofs for the bounded E08 high-risk review findings."""

from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import sqlite3
import stat
from types import SimpleNamespace

import pytest

from psyche_os.adapters.e08_filesystem import FilesystemQuarantine
from psyche_os.application.e08_imports import (
    E08BoundaryError,
    E08CanonicalStore,
    E08ErrorCode,
    E08ImportService,
)
from psyche_os.backup_export.versioned import create_versioned_export
from psyche_os.imports.model import CanonicalMapping, ImportTransformation, ProposedMapping
from psyche_os.imports.plain_text import INCOMPATIBLE_SIGNATURES, UTF8_BOM, PlainTextParser

KEY = b"review-vault-fingerprint-key-0001"[:32]


def service(store: E08CanonicalStore | None = None, *, parser=None) -> E08ImportService:  # type: ignore[no-untyped-def]
    return E08ImportService(
        FilesystemQuarantine(digest_key=KEY),
        parser=parser,
        store=store or E08CanonicalStore.for_test(),
    )


def commit_text(instance: E08ImportService, path: Path):  # type: ignore[no-untyped-def]
    candidate = instance.parse(instance.intake(str(path)).quarantine_id)
    preview = instance.preview(candidate)
    consent = instance.issue_consent(candidate, preview, approved=True)
    return candidate, preview, instance.commit(candidate, preview, consent)


class MalformedParser:
    name = PlainTextParser.name
    version = PlainTextParser.version
    config_digest = PlainTextParser.config_digest

    def __init__(self, field: str) -> None:
        self.field = field

    def parse(self, bounded_bytes: bytes, **kwargs: object):  # type: ignore[no-untyped-def]
        candidate = PlainTextParser().parse(bounded_bytes, **kwargs)
        if self.field == "segment":
            return replace(candidate, segments=(replace(candidate.segments[0], segment_id="fabricated"),))
        if self.field in {"physical_line", "character_start", "newline"}:
            values = {"physical_line": 99, "character_start": 99, "newline": "IMPOSSIBLE"}
            changed = replace(candidate.segments[0], **{self.field: values[self.field]})
            return replace(candidate, segments=(changed, *candidate.segments[1:]))
        if self.field == "out_of_order":
            return replace(candidate, segments=tuple(reversed(candidate.segments)))
        if self.field == "duplicate":
            return replace(candidate, segments=(candidate.segments[0], candidate.segments[0]), segment_count=2)
        if self.field == "overlap":
            second = replace(candidate.segments[-1], byte_start=candidate.segments[0].byte_start)
            return replace(candidate, segments=(candidate.segments[0], second))
        values = {
            "candidate_id": "fabricated",
            "source_candidate_id": "wrong-source",
            "profile_id": "wrong-profile",
            "character_count": 999,
            "physical_line_count": 999,
            "encoding": "fictional",
            "bom": not candidate.bom,
            "transformations": ("fictional",),
        }
        return replace(candidate, **{self.field: values[self.field]})


@pytest.mark.parametrize(
    "field",
    ["candidate_id", "source_candidate_id", "profile_id", "segment", "duplicate", "overlap",
     "physical_line", "character_start", "newline", "out_of_order",
     "character_count", "physical_line_count", "encoding", "bom", "transformations"],
)
def test_application_independently_rejects_deterministic_parser_fabrication(tmp_path, field) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "parser-proposal.txt"
    path.write_text("first fictional\nsecond fictional", encoding="utf-8")
    instance = service(parser=MalformedParser(field))
    record = instance.intake(str(path))
    with pytest.raises(E08BoundaryError) as caught:
        instance.parse(record.quarantine_id)
    assert caught.value.code == E08ErrorCode.MALFORMED_CANDIDATE


@pytest.mark.parametrize("signature", [item[0] for item in INCOMPATIBLE_SIGNATURES])
@pytest.mark.parametrize("prefix", [b"", UTF8_BOM])
def test_every_forbidden_signature_is_rejected_with_or_without_bom(tmp_path, signature, prefix) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "signature.txt"
    path.write_bytes(prefix + signature + b" synthetic")
    instance = service()
    record = instance.intake(str(path))
    with pytest.raises(E08BoundaryError) as caught:
        instance.parse(record.quarantine_id)
    assert caught.value.code in {E08ErrorCode.INCOMPATIBLE_SIGNATURE, E08ErrorCode.INVALID_UTF8}


def test_fingerprint_is_restart_stable_only_inside_one_vault(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "same.txt"
    path.write_text("same synthetic bytes", encoding="utf-8")
    args = {
        "profile": service().profile,
        "parser_identity": "parser",
        "policy_lineage_id": "policy",
    }
    a = FilesystemQuarantine(digest_key=KEY).intake(str(path), **args)
    b = FilesystemQuarantine(digest_key=KEY).intake(str(path), **args)
    c = FilesystemQuarantine(digest_key=b"different-vault-key-material-000"[:32]).intake(str(path), **args)
    assert a.protected_digest_ref == b.protected_digest_ref
    assert a.protected_digest_ref != c.protected_digest_ref


def test_committed_canonical_state_reopens_and_deletes_from_v5(tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "vault.sqlite"
    store_a = E08CanonicalStore.for_test(sqlite3.connect(database))
    instance_a = service(store_a)
    path = tmp_path / "durable.txt"
    path.write_text("durable synthetic source", encoding="utf-8")
    _, _, result = commit_text(instance_a, path)
    assert store_a.connection.execute(
        "SELECT COUNT(*) FROM source_artifacts WHERE version_id=?", (result.source_version_id,)
    ).fetchone()[0] == 1
    store_a.connection.close()

    store_b = E08CanonicalStore(sqlite3.connect(database))
    instance_b = service(store_b)
    assert result.source_version_id in store_b.sources
    assert result.segment_ids[0] in store_b.nodes
    plan = instance_b.prepare_deletion(result.source_version_id)
    receipt = instance_b.execute_deletion(plan, plan.confirmation)
    assert receipt.raw_storage_absence and result.source_version_id not in store_b.export()["source_versions"]
    exported = create_versioned_export(store_b.connection)
    canonical_export = json.dumps(
        {
            "sources": exported["tables"]["source_artifacts"],
            "locators": exported["tables"]["source_locators"],
            "reports": exported["tables"]["reports"],
            "e08": exported["tables"]["e08_import_sources"],
            "raw": exported["tables"]["e08_quarantine_objects"],
        },
        sort_keys=True,
    )
    assert result.source_version_id not in canonical_export


@pytest.mark.parametrize("fault", list("ABCDEF"))
def test_every_deletion_fault_boundary_rolls_back_after_reopen(tmp_path, fault) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / f"fault-{fault}.sqlite"
    store_a = E08CanonicalStore.for_test(sqlite3.connect(database))
    instance = service(store_a)
    path = tmp_path / f"fault-{fault}.txt"
    path.write_text("fault-safe synthetic source", encoding="utf-8")
    _, _, result = commit_text(instance, path)
    plan = instance.prepare_deletion(result.source_version_id)
    with pytest.raises(E08BoundaryError) as caught:
        instance.execute_deletion(plan, plan.confirmation, fault_at=fault)
    assert caught.value.code == E08ErrorCode.STORAGE_FAILURE
    store_a.connection.close()
    reopened = E08CanonicalStore(sqlite3.connect(database))
    assert result.source_version_id in reopened.sources
    assert reopened.connection.execute(
        "SELECT COUNT(*) FROM e08_quarantine_objects"
    ).fetchone()[0] == 1
    assert not reopened.receipts


@pytest.mark.parametrize(
    "change",
    ["own_version", "parent_version", "missing", "processing", "cloud", "lineage", "contradictory"],
)
def test_policy_lineage_change_fails_before_mutation(tmp_path, change) -> None:  # type: ignore[no-untyped-def]
    instance = service()
    con = instance.store.connection
    # The accepted V1 lineage table targets the non-unique policy_id column;
    # synthetic lineage fixtures therefore mirror migration loading with FK
    # enforcement suspended, while E08 still resolves the accepted rows.
    con.execute("PRAGMA foreign_keys=OFF")
    now = "2042-01-01T00:00:00+00:00"
    con.execute(
        "INSERT INTO data_policies(record_id,policy_id,version_id,target_record_id,sensitivity,"
        "processing_location,cloud_policy,purpose,third_party_scope,retention_policy_id,export_rule,"
        "lineage_rule,tx_from,is_active,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("e08-parent", "e08-parent-policy", "parent-v1", "e08-imports", "deeply_sensitive",
         "local_only", "never_cloud", "parent", "none", "governed", "block",
         "most_restrictive_parent", now, 1, now),
    )
    con.execute(
        "INSERT INTO policy_lineage(parent_policy_id,child_policy_id,created_at) VALUES(?,?,?)",
        ("e08-parent-policy", "e08-local-never-cloud", now),
    )
    con.commit()
    path = tmp_path / "policy.txt"
    path.write_text("policy synthetic", encoding="utf-8")
    candidate = instance.parse(instance.intake(str(path)).quarantine_id)
    preview = instance.preview(candidate)
    consent = instance.issue_consent(candidate, preview, approved=True)
    if change == "own_version":
        con.execute("UPDATE data_policies SET version_id='e08-policy-v2' WHERE record_id='e08-local-never-cloud'")
    elif change == "parent_version":
        con.execute("UPDATE data_policies SET version_id='parent-v2' WHERE record_id='e08-parent'")
    elif change == "missing":
        con.execute("DELETE FROM policy_lineage WHERE child_policy_id='e08-local-never-cloud'")
        con.execute("DELETE FROM data_policies WHERE record_id='e08-local-never-cloud'")
    elif change == "processing":
        con.execute("UPDATE data_policies SET processing_location='approved_cloud' WHERE record_id='e08-local-never-cloud'")
    elif change == "cloud":
        con.execute("UPDATE data_policies SET cloud_policy='ask_each_time' WHERE record_id='e08-local-never-cloud'")
    else:
        con.execute(
            "INSERT INTO data_policies(record_id,policy_id,version_id,target_record_id,sensitivity,"
            "processing_location,cloud_policy,purpose,third_party_scope,retention_policy_id,export_rule,"
            "lineage_rule,tx_from,is_active,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("e08-second-parent", "e08-second-parent-policy", "parent-v1", "e08-imports",
             "deeply_sensitive", "local_only", "never_cloud", "parent", "none", "governed",
             "block", "most_restrictive_parent", now, 1, now),
        )
        con.execute(
            "INSERT INTO policy_lineage(parent_policy_id,child_policy_id,created_at) VALUES(?,?,?)",
            ("e08-second-parent-policy", "e08-local-never-cloud", now),
        )
        if change == "contradictory":
            con.execute(
                "INSERT INTO data_policies(record_id,policy_id,version_id,target_record_id,sensitivity,"
                "processing_location,cloud_policy,purpose,third_party_scope,retention_policy_id,export_rule,"
                "lineage_rule,tx_from,is_active,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("e08-second-parent-duplicate", "e08-second-parent-policy", "parent-v2", "e08-imports",
                 "deeply_sensitive", "local_only", "never_cloud", "duplicate", "none", "governed",
                 "block", "most_restrictive_parent", now, 1, now),
            )
    con.commit()
    with pytest.raises(E08BoundaryError) as caught:
        instance.commit(candidate, preview, consent)
    assert caught.value.code == E08ErrorCode.POLICY_STALE
    assert not instance.store.sources


def test_repr_surfaces_and_redaction_mapping_remain_truthful(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "private-name.txt"
    secret = "private synthetic excerpt"
    path.write_text(secret, encoding="utf-8")
    instance = service()
    record = instance.intake(str(path), declared_mime="text/plain")
    candidate = instance.parse(record.quarantine_id)
    preview = instance.preview(candidate)
    rendered = repr(record) + repr(instance.quarantine.snapshot(record.quarantine_id)) + repr(candidate) + repr(preview)
    assert secret not in rendered and str(path) not in rendered
    assert record.protected_digest_ref not in rendered
    transform = ImportTransformation(candidate.segments[0].segment_id, "redact", "manual-v1", "replacement-secret")
    mapping = ProposedMapping(candidate.segments[0].segment_id, CanonicalMapping.ATTRIBUTED_VERBATIM_REPORT)
    with pytest.raises(E08BoundaryError) as caught:
        instance.preview(candidate, mappings=(mapping,), transformations=(transform,))
    assert caught.value.code == E08ErrorCode.INVALID_MAPPING
    consent = instance.issue_consent(candidate, preview, approved=True)
    result = instance.commit(candidate, preview, consent)
    plan = instance.prepare_deletion(result.source_version_id)
    receipt = instance.execute_deletion(plan, plan.confirmation)
    rendered = (
        repr(consent)
        + repr(result)
        + repr(plan)
        + repr(receipt)
        + repr(transform)
        + repr(instance.events)
    )
    assert record.protected_digest_ref not in rendered
    assert candidate.candidate_id not in rendered
    assert "replacement-secret" not in rendered


def test_same_size_mid_read_mutation_is_rejected(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "race.txt"
    path.write_bytes(b"A" * (128 * 1024))
    original_read = os.read
    changed = False

    def racing_read(fd: int, count: int) -> bytes:
        nonlocal changed
        chunk = original_read(fd, count)
        if chunk and not changed:
            changed = True
            before = path.stat()
            with path.open("r+b") as stream:
                stream.seek(64 * 1024)
                stream.write(b"B" * (64 * 1024))
            os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        return chunk

    monkeypatch.setattr(os, "read", racing_read)
    with pytest.raises(E08BoundaryError):
        service().intake(str(path))


def test_windows_reparse_observed_after_open_and_special_file_are_rejected(
    tmp_path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "reparse.txt"
    path.write_text("never accepted", encoding="utf-8")
    real_lstat = Path.lstat
    calls = 0

    def reparse_after_open(self: Path):  # type: ignore[no-untyped-def]
        nonlocal calls
        calls += 1
        value = real_lstat(self)
        if calls == 1:
            return value
        data = {name: getattr(value, name) for name in (
            "st_mode", "st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns"
        )}
        return SimpleNamespace(**data, st_file_attributes=0x400)

    monkeypatch.setattr(Path, "lstat", reparse_after_open)
    with pytest.raises(E08BoundaryError):
        service().intake(str(path))

    value = real_lstat(path)
    special = SimpleNamespace(
        st_mode=stat.S_IFIFO,
        st_dev=value.st_dev,
        st_ino=value.st_ino,
        st_size=value.st_size,
        st_mtime_ns=value.st_mtime_ns,
        st_ctime_ns=value.st_ctime_ns,
        st_file_attributes=0,
    )
    monkeypatch.setattr(Path, "lstat", lambda _self: special)
    with pytest.raises(E08BoundaryError):
        service().intake(str(path))
