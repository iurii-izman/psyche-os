"""Unit tests for domain IDs."""

import re

from psyche_os.domain.ids import (
    ActorId,
    AuditEventId,
    BackupId,
    BlobId,
    DeletionRequestId,
    DerivationId,
    ExportId,
    OpaqueId,
    PolicyId,
    RecordId,
    SubjectId,
    VaultId,
    VersionId,
    generate_id,
)


class TestGenerateId:
    def test_generates_uuid4_string(self) -> None:
        result = generate_id()
        assert isinstance(result, str)
        uuid_pattern = (
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-"
            r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        )
        assert re.match(uuid_pattern, result), f"Not UUIDv4: {result}"

    def test_generates_unique_ids(self) -> None:
        ids = {generate_id() for _ in range(100)}
        assert len(ids) == 100


class TestOpaqueId:
    def test_construction_and_equality(self) -> None:
        vid = generate_id()
        a = OpaqueId(vid)
        b = OpaqueId(vid)
        c = OpaqueId(generate_id())
        assert a == b
        assert a != c

    def test_str_roundtrip(self) -> None:
        vid = generate_id()
        o = OpaqueId(vid)
        assert str(o) == vid

    def test_hashable(self) -> None:
        s = {OpaqueId(generate_id()) for _ in range(10)}
        assert len(s) == 10


class TestNewTypeAliases:
    def test_vault_id_construction(self) -> None:
        vid = generate_id()
        v = VaultId(vid)
        assert str(v) == vid

    def test_subject_id_construction(self) -> None:
        vid = generate_id()
        s = SubjectId(vid)
        assert str(s) == vid

    def test_actor_id_construction(self) -> None:
        vid = generate_id()
        a = ActorId(vid)
        assert str(a) == vid

    def test_record_id_construction(self) -> None:
        vid = generate_id()
        r = RecordId(vid)
        assert str(r) == vid

    def test_version_id_construction(self) -> None:
        vid = generate_id()
        v = VersionId(vid)
        assert str(v) == vid

    def test_blob_id_construction(self) -> None:
        vid = generate_id()
        b = BlobId(vid)
        assert str(b) == vid

    def test_derivation_id_construction(self) -> None:
        vid = generate_id()
        d = DerivationId(vid)
        assert str(d) == vid

    def test_policy_id_construction(self) -> None:
        vid = generate_id()
        p = PolicyId(vid)
        assert str(p) == vid

    def test_audit_event_id_construction(self) -> None:
        vid = generate_id()
        a = AuditEventId(vid)
        assert str(a) == vid

    def test_deletion_request_id_construction(self) -> None:
        vid = generate_id()
        d = DeletionRequestId(vid)
        assert str(d) == vid

    def test_backup_id_construction(self) -> None:
        vid = generate_id()
        b = BackupId(vid)
        assert str(b) == vid

    def test_export_id_construction(self) -> None:
        vid = generate_id()
        e = ExportId(vid)
        assert str(e) == vid
