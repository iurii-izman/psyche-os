"""E08 quarantine-to-canonical application authority."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import asdict, dataclass
import datetime
from enum import StrEnum
import html
import json
import secrets
import sqlite3
from typing import Protocol

from psyche_os.adapters.e08_filesystem import (
    FilesystemBoundaryError,
    FilesystemQuarantine,
    QuarantineRecord,
    QuarantineSnapshot,
)
from psyche_os.imports.model import (
    PLAIN_TEXT_PROFILE,
    CanonicalMapping,
    ImportPreview,
    ImportTransformation,
    ParsedImportCandidate,
    PlainTextResourceProfile,
    ProposedMapping,
    identity_digest,
)
from psyche_os.imports.plain_text import PlainTextParser


class E08ErrorCode(StrEnum):
    FILESYSTEM_REJECTED = "filesystem_rejected"
    BYTE_LIMIT_EXCEEDED = "byte_limit_exceeded"
    INVALID_UTF8 = "invalid_utf8"
    DISALLOWED_CONTROL = "disallowed_control"
    INCOMPATIBLE_SIGNATURE = "incompatible_signature"
    UNSUPPORTED_DECLARATION = "unsupported_declaration"
    CHARACTER_LIMIT_EXCEEDED = "character_limit_exceeded"
    LINE_LIMIT_EXCEEDED = "line_limit_exceeded"
    LINE_LENGTH_EXCEEDED = "line_length_exceeded"
    SEGMENT_LIMIT_EXCEEDED = "segment_limit_exceeded"
    EMPTY_CANDIDATE = "empty_candidate"
    MALFORMED_RESOURCE = "malformed_resource"
    MALFORMED_CANDIDATE = "malformed_candidate"
    CAPABILITY_MISMATCH = "capability_mismatch"
    CAPABILITY_CONSUMED = "capability_consumed"
    SOURCE_STALE = "source_stale"
    POLICY_STALE = "policy_stale"
    PARSER_STALE = "parser_stale"
    DUPLICATE_DECISION_REQUIRED = "duplicate_decision_required"
    DUPLICATE_REJECTED = "duplicate_rejected"
    INVALID_MAPPING = "invalid_mapping"
    INVALID_TRANSFORMATION = "invalid_transformation"
    CORRECTION_TARGET_INVALID = "correction_target_invalid"
    DELETION_PLAN_INVALID = "deletion_plan_invalid"
    DELETION_PLAN_STALE = "deletion_plan_stale"
    DELETION_CANCELLED = "deletion_cancelled"
    STORAGE_FAILURE = "storage_failure"


_REJECTION_CODES = {item.value: item for item in E08ErrorCode}


class E08BoundaryError(RuntimeError):
    """Typed error whose text and repr never contain source-derived material."""

    def __init__(self, code: E08ErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class CandidateParser(Protocol):
    name: str
    version: str
    config_digest: str

    def parse(self, bounded_bytes: bytes, **kwargs: object) -> ParsedImportCandidate: ...


@dataclass(frozen=True, slots=True)
class ImportConsent:
    consent_id: str
    candidate_id: str
    preview_id: str
    policy_lineage_id: str

    def __repr__(self) -> str:
        return "ImportConsent(capability=<redacted>)"


@dataclass(frozen=True, slots=True)
class CanonicalSource:
    source_id: str
    source_version_id: str
    quarantine_id: str
    protected_digest_ref: str
    byte_count: int
    parser_identity: str
    profile_identity: str
    policy_lineage_id: str
    preview_id: str
    consent_id: str
    correction_of: str | None
    state: str
    original_bytes: bytes

    def __repr__(self) -> str:
        return (
            f"CanonicalSource(byte_count={self.byte_count!r}, state={self.state!r}, "
            "original_bytes=<redacted>)"
        )


@dataclass(frozen=True, slots=True)
class CanonicalNode:
    record_id: str
    version_id: str
    kind: str
    source_version_id: str
    parent_ids: tuple[str, ...]
    policy_lineage_id: str
    locator: tuple[int, int, int, int, int, str] | None
    method_version: str | None
    status: str
    content: str | None

    def __repr__(self) -> str:
        return (
            f"CanonicalNode(kind={self.kind!r}, parent_count={len(self.parent_ids)!r}, "
            f"status={self.status!r}, content=<redacted>)"
        )


@dataclass(frozen=True, slots=True)
class ImportCommitResult:
    source_id: str
    source_version_id: str
    record_ids: tuple[str, ...]
    segment_ids: tuple[str, ...]
    correction_of: str | None
    untrusted_content: bool = True

    def __repr__(self) -> str:
        return (
            f"ImportCommitResult(record_count={len(self.record_ids)!r}, "
            f"segment_count={len(self.segment_ids)!r}, untrusted_content=True)"
        )


@dataclass(frozen=True, slots=True)
class ImportDeletionPlan:
    plan_id: str
    source_version_id: str
    delete_ids: tuple[str, ...]
    invalidate_ids: tuple[str, ...]
    graph_identity: str
    confirmation: str

    def __repr__(self) -> str:
        return (
            f"ImportDeletionPlan(delete_count={len(self.delete_ids)!r}, "
            f"invalidate_count={len(self.invalidate_ids)!r})"
        )


@dataclass(frozen=True, slots=True)
class ImportDeletionReceipt:
    receipt_id: str
    plan_id: str
    records_deleted: int
    records_invalidated: int
    quarantine_removed: bool
    canonical_absence: bool
    export_absence: bool
    raw_storage_absence: bool
    external_copies: str = "outside_local_control"
    backup_state: str = "governed_expiry"

    def __repr__(self) -> str:
        return (
            f"ImportDeletionReceipt(records_deleted={self.records_deleted!r}, "
            f"records_invalidated={self.records_invalidated!r}, "
            f"canonical_absence={self.canonical_absence!r}, "
            f"raw_storage_absence={self.raw_storage_absence!r})"
        )


class E08CanonicalStore:
    """Durable V5 repository; dictionaries are reloadable read caches only."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        version = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        if not version or version[0] != 5:
            raise ValueError("E08 requires an explicitly migrated V5 canonical store")
        connection.execute("PRAGMA foreign_keys=ON")
        self.connection = connection
        self.sources: dict[str, CanonicalSource] = {}
        self.nodes: dict[str, CanonicalNode] = {}
        self.relations: set[tuple[str, str, str]] = set()
        self.receipts: list[ImportDeletionReceipt] = []
        self.reload()

    @classmethod
    def for_test(cls, connection: sqlite3.Connection | None = None) -> E08CanonicalStore:
        """Create a synthetic V5 store with an accepted conservative policy."""
        from psyche_os.storage.migrations import Migrator

        con = connection or sqlite3.connect(":memory:")
        report = Migrator(con).apply(5)
        if not report.success:
            raise ValueError("Synthetic V5 store migration failed")
        now = datetime.datetime.now(datetime.UTC).isoformat()
        con.execute(
            "INSERT OR IGNORE INTO data_policies(record_id,policy_id,version_id,target_record_id,"
            "sensitivity,processing_location,cloud_policy,purpose,third_party_scope,"
            "retention_policy_id,export_rule,lineage_rule,tx_from,is_active,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("e08-local-never-cloud", "e08-local-never-cloud", "e08-policy-v1", "e08-imports",
             "deeply_sensitive", "local_only", "never_cloud", "synthetic import fixture",
             "none", "governed", "block", "most_restrictive_parent", now, 1, now),
        )
        con.commit()
        return cls(con)

    def reload(self) -> None:
        self.sources.clear()
        self.nodes.clear()
        self.relations.clear()
        self.receipts.clear()
        for row in self.connection.execute(
            "SELECT s.source_record_id,s.source_version_id,s.quarantine_id,q.protected_digest_ref,"
            "q.byte_count,s.parser_identity,s.profile_identity,s.policy_decision_id,s.preview_id,"
            "s.consent_id,s.correction_of,s.state,q.bounded_bytes FROM e08_import_sources s "
            "JOIN e08_quarantine_objects q USING(quarantine_id)"
        ):
            self.sources[row[1]] = CanonicalSource(
                row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7],
                row[8], row[9], row[10], row[11], bytes(row[12]),
            )
        for row in self.connection.execute(
            "SELECT record_id,version_id,kind,source_version_id,parent_ids,policy_decision_id,"
            "locator,method_version,status,content FROM e08_import_nodes"
        ):
            locator = tuple(json.loads(row[6])) if row[6] is not None else None
            self.nodes[row[0]] = CanonicalNode(
                row[0], row[1], row[2], row[3], tuple(json.loads(row[4])), row[5],
                locator, row[7], row[8], row[9],
            )
        for row in self.connection.execute(
            "SELECT parent_record_id,child_record_id,relation_kind FROM record_relations "
            "WHERE relation_id LIKE 'e08-rel-%'"
        ):
            self.relations.add((row[0], row[1], row[2]))
        for row in self.connection.execute(
            "SELECT receipt_id,plan_id,records_deleted,records_invalidated FROM deletion_receipts "
            "WHERE receipt_id LIKE 'e08-receipt-%'"
        ):
            self.receipts.append(ImportDeletionReceipt(row[0], row[1], row[2], row[3], True, True, True, True))

    def resolve_policy(self, policy_record_id: str) -> tuple[str, str, str]:
        """Return exact own version and a fail-closed effective lineage identity."""
        selected: list[tuple[object, ...]] = []
        edges: list[tuple[str, str]] = []
        pending = [policy_record_id]
        seen: set[str] = set()
        while pending:
            record_id = pending.pop()
            if record_id in seen:
                raise E08BoundaryError(E08ErrorCode.POLICY_STALE)
            seen.add(record_id)
            rows = self.connection.execute(
                "SELECT record_id,policy_id,version_id,sensitivity,processing_location,cloud_policy,"
                "purpose,third_party_scope,retention_policy_id,export_rule,export_audience,lineage_rule "
                "FROM data_policies WHERE record_id=? AND is_active=1 AND tx_to IS NULL",
                (record_id,),
            ).fetchall()
            if len(rows) != 1:
                raise E08BoundaryError(E08ErrorCode.POLICY_STALE)
            row = rows[0]
            selected.append(tuple(row))
            parents = self.connection.execute(
                "SELECT parent_policy_id,child_policy_id FROM policy_lineage WHERE child_policy_id=?",
                (row[1],),
            ).fetchall()
            for parent_policy_id, child_policy_id in parents:
                parent_records = self.connection.execute(
                    "SELECT DISTINCT record_id FROM data_policies WHERE policy_id=? AND is_active=1 AND tx_to IS NULL",
                    (parent_policy_id,),
                ).fetchall()
                if len(parent_records) != 1:
                    raise E08BoundaryError(E08ErrorCode.POLICY_STALE)
                edges.append((parent_policy_id, child_policy_id))
                pending.append(parent_records[0][0])
        if any(row[4] != "local_only" or row[5] != "never_cloud" for row in selected):
            raise E08BoundaryError(E08ErrorCode.POLICY_STALE)
        own = selected[0]
        decision = identity_digest({"policies": sorted(selected), "lineage": sorted(edges)})
        return str(own[0]), str(own[2]), decision

    def persist_import(
        self,
        source: CanonicalSource,
        *,
        policy_record_id: str,
        inject_failure: bool = False,
    ) -> None:
        """Persist quarantine, E08 metadata and accepted E03 records atomically."""
        now = datetime.datetime.now(datetime.UTC).isoformat()
        policy_record_id, policy_version_id, decision = self.resolve_policy(policy_record_id)
        if decision != source.policy_lineage_id:
            raise E08BoundaryError(E08ErrorCode.POLICY_STALE)
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            self.connection.execute(
                "INSERT INTO e08_quarantine_objects VALUES(?,?,?,?,?,?,?)",
                (source.quarantine_id, source.original_bytes, source.protected_digest_ref,
                 source.protected_digest_ref.split(":", 1)[0], "committed", source.byte_count, now),
            )
            previous = source.correction_of or ""
            self.connection.execute(
                "INSERT INTO source_artifacts(record_id,artifact_id,version_id,previous_version_id,source_kind,"
                "source_label,uri_or_path,mime_type,source_metadata,tx_from,is_active,created_at,semantic_version,"
                "schema_version,change_reason_code,created_by_actor_id,artifact_kind,origin_kind,captured_at,"
                "language_tags,declared_mime_type,observed_mime_type,byte_size,parser_state,quarantine_state,policy_id,rights_note) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (source.source_id, source.source_id, source.source_version_id, previous, "document", "", "", "text/plain",
                 '{"untrusted_content":true}', now, 1, now, 2, 2, "e08_import", "actor:local-owner",
                 "standalone_plain_text", "user_import", now, "[]", "text/plain", "text/plain", source.byte_count,
                 "certified", "committed", policy_record_id, "user-provided synthetic fixture"),
            )
            self.connection.execute(
                "INSERT INTO e08_import_sources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (source.source_version_id, source.source_id, source.quarantine_id, source.parser_identity,
                 source.profile_identity, policy_record_id, policy_version_id, decision, source.preview_id,
                 source.consent_id, source.correction_of, source.state, now),
            )
            for node in [n for n in self.nodes.values() if n.source_version_id == source.source_version_id]:
                self._insert_node(node, now)
            if source.correction_of:
                self._supersede(source.correction_of, now)
                old = self.sources[source.correction_of]
                self._insert_relation(old.source_id, source.correction_of, source.source_id,
                                      source.source_version_id, "corrects", now)
            if inject_failure:
                raise RuntimeError("injected")
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        self.reload()

    def _insert_node(self, node: CanonicalNode, now: str) -> None:
        self.connection.execute(
            "INSERT INTO e08_import_nodes VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (node.record_id, node.version_id, node.kind, node.source_version_id,
             json.dumps(node.parent_ids), node.policy_lineage_id,
             json.dumps(node.locator) if node.locator is not None else None,
             node.method_version, node.status, node.content, now),
        )
        if node.kind == "source_segment":
            self.connection.execute(
                "INSERT INTO source_locators(record_id,version_id,schema_version,tx_from,is_active,change_reason_code,"
                "created_by_actor_id,artifact_record_id,artifact_version_id,locator_type,locator_value,extractor_name,extractor_version) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (node.record_id, node.version_id, 2, now, 1, "e08_import", "actor:local-owner",
                 self.sources[node.source_version_id].source_id, node.source_version_id, "extractor_locator",
                 json.dumps(node.locator), "e08_plain_text", "1.0.0"),
            )
        elif node.kind == "attributed_verbatim_report":
            self.connection.execute(
                "INSERT INTO reports(record_id,report_id,version_id,source_ids,structured_data,tx_from,is_active,created_at,"
                "semantic_version,schema_version,change_reason_code,created_by_actor_id,report_kind,verbatim_content,"
                "perspective,elicitation_method,source_locator_record_id,source_locator_version_id) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (node.record_id, node.record_id, node.version_id, json.dumps([node.source_version_id]), "{}", now, 1, now,
                 2, 2, "e08_import", "actor:local-owner", "other", node.content, "document_author", "import",
                 node.parent_ids[0], self.nodes[node.parent_ids[0]].version_id),
            )
        elif node.kind == "review_needed_assertion_proposal":
            self.connection.execute(
                "INSERT INTO assertions(record_id,assertion_id,version_id,assertion_type,predicate,support_ids,contra_ids,"
                "tx_from,is_active,created_at,provenance_ref,semantic_version,schema_version,change_reason_code,"
                "created_by_actor_id,object_value,qualifiers,negation,modality,scope,source_locator_record_id,source_locator_version_id) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (node.record_id, node.record_id, node.version_id, "review_needed_proposal", "untrusted_import_text",
                 json.dumps(list(node.parent_ids)), "[]", now, 1, now, node.source_version_id, 2, 2, "e08_import",
                 "actor:local-owner", node.content, "[]", 0, "reported", "imported_segment",
                 node.parent_ids[0], self.nodes[node.parent_ids[0]].version_id),
            )
        for parent in node.parent_ids:
            self._insert_relation(parent, self.nodes[parent].version_id, node.record_id, node.version_id, "derived_from", now)

    def _insert_relation(self, parent: str, parent_version: str, child: str, child_version: str,
                         kind: str, now: str) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO record_relations VALUES(?,?,?,?,?,?,?,?)",
            ("e08-rel-" + identity_digest((parent, child, kind)), parent, parent_version,
             child, child_version, kind, None, now),
        )

    def _supersede(self, source_version_id: str, now: str) -> None:
        self.connection.execute(
            "UPDATE e08_import_sources SET state='superseded' WHERE source_version_id=?", (source_version_id,)
        )
        self.connection.execute(
            "UPDATE source_artifacts SET is_active=0,tx_to=?,closure_marker='invalidated' WHERE version_id=?",
            (now, source_version_id),
        )
        ids = [r[0] for r in self.connection.execute(
            "SELECT record_id FROM e08_import_nodes WHERE source_version_id=?", (source_version_id,)
        )]
        self.connection.execute(
            "UPDATE e08_import_nodes SET status='superseded',content=NULL WHERE source_version_id=?",
            (source_version_id,),
        )
        if ids:
            marks = ",".join("?" for _ in ids)
            self.connection.execute(
                f"UPDATE source_locators SET is_active=0,tx_to=? WHERE record_id IN ({marks})",
                (now, *ids),
            )
            for table in ("reports", "assertions"):
                self.connection.execute(
                    f"UPDATE {table} SET is_active=0,tx_to=?,closure_marker='invalidated' "
                    f"WHERE record_id IN ({marks})", (now, *ids),
                )

    def graph_identity(self) -> str:
        return identity_digest(
            {
                "sources": sorted((key, value.state) for key, value in self.sources.items()),
                "nodes": sorted(
                    (key, value.status, value.parent_ids) for key, value in self.nodes.items()
                ),
                "relations": sorted(self.relations),
            }
        )

    def active_content(self, record_id: str) -> str | None:
        node = self.nodes.get(record_id)
        return (
            node.content
            if node is not None and node.status in {"active", "review_needed"}
            else None
        )

    def export(self) -> dict[str, tuple[str, ...]]:
        return {
            "source_versions": tuple(
                sorted(key for key, item in self.sources.items() if item.state != "deleted")
            ),
            "record_ids": tuple(
                sorted(
                    key
                    for key, item in self.nodes.items()
                    if item.status in {"active", "review_needed"}
                )
            ),
        }

    def add_mixed_derivative(
        self, parent_ids: tuple[str, ...], *, content: str = "synthetic mixed derivative"
    ) -> str:
        if len(parent_ids) < 2 or any(parent not in self.nodes for parent in parent_ids):
            raise E08BoundaryError(E08ErrorCode.MALFORMED_RESOURCE)
        record_id = "mixed-" + secrets.token_hex(12)
        first = self.nodes[parent_ids[0]]
        self.nodes[record_id] = CanonicalNode(
            record_id,
            record_id + "-v1",
            "derived_relation",
            "mixed-lineage",
            parent_ids,
            first.policy_lineage_id,
            None,
            "e08-derived-relation-v1",
            "active",
            content,
        )
        for parent in parent_ids:
            self.relations.add((parent, record_id, "derived_from"))
        now = datetime.datetime.now(datetime.UTC).isoformat()
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            self._insert_node(self.nodes[record_id], now)
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            self.reload()
            raise
        return record_id

    def delete_import(
        self, plan: ImportDeletionPlan, *, fault_at: str | None = None
    ) -> ImportDeletionReceipt:
        """Delete accepted canonical rows, governed bytes and receipt in one transaction."""
        source = self.sources[plan.source_version_id]
        now = datetime.datetime.now(datetime.UTC).isoformat()
        request_id = "e08-request-" + identity_digest(plan.plan_id)
        receipt_id = "e08-receipt-" + identity_digest((plan.plan_id, plan.graph_identity))
        delete_ids = list(plan.delete_ids)
        invalidate_ids = list(plan.invalidate_ids)
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            if fault_at == "A":
                raise RuntimeError("fault A")
            self.connection.execute(
                "INSERT INTO deletion_requests(request_id,reason,scope,target_ids,status,created_at) "
                "VALUES(?,?,?,?,?,?)",
                (request_id, "e08_governed_source_deletion", "tree",
                 json.dumps([plan.source_version_id]), "in_progress", now),
            )
            self.connection.execute(
                "INSERT INTO deletion_plans(plan_id,request_id,target_record_ids,exclusive_descendant_ids,"
                "mixed_descendant_ids,invalidate_ids,recompute_ids,dependency_graph_snapshot,status,created_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (plan.plan_id, request_id, json.dumps([plan.source_version_id]), json.dumps(delete_ids),
                 json.dumps(invalidate_ids), json.dumps(invalidate_ids), "[]",
                 json.dumps({"identity": plan.graph_identity}), "executing", now),
            )
            for table in ("reports", "assertions", "source_locators"):
                if delete_ids:
                    marks = ",".join("?" for _ in delete_ids)
                    self.connection.execute(f"DELETE FROM {table} WHERE record_id IN ({marks})", delete_ids)
                if invalidate_ids:
                    marks = ",".join("?" for _ in invalidate_ids)
                    closure = ",closure_marker='invalidated'" if table != "source_locators" else ""
                    self.connection.execute(
                        f"UPDATE {table} SET is_active=0,tx_to=?{closure} "
                        f"WHERE record_id IN ({marks})", (now, *invalidate_ids),
                    )
            if invalidate_ids:
                marks = ",".join("?" for _ in invalidate_ids)
                self.connection.execute(
                    f"UPDATE e08_import_nodes SET status='invalidated',content=NULL "
                    f"WHERE record_id IN ({marks})", invalidate_ids,
                )
            if delete_ids:
                marks = ",".join("?" for _ in delete_ids)
                self.connection.execute(f"DELETE FROM e08_import_nodes WHERE record_id IN ({marks})", delete_ids)
                self.connection.execute(
                    f"DELETE FROM record_relations WHERE parent_record_id IN ({marks}) "
                    f"OR child_record_id IN ({marks})", (*delete_ids, *delete_ids),
                )
            if fault_at == "B":
                raise RuntimeError("fault B")
            self.connection.execute(
                "DELETE FROM record_relations WHERE parent_record_id=? OR child_record_id=?",
                (source.source_id, source.source_id),
            )
            self.connection.execute(
                "DELETE FROM e08_import_sources WHERE source_version_id=?", (plan.source_version_id,)
            )
            self.connection.execute(
                "DELETE FROM source_artifacts WHERE record_id=? AND version_id=?",
                (source.source_id, plan.source_version_id),
            )
            if fault_at == "C":
                raise RuntimeError("fault C")
            self.connection.execute(
                "DELETE FROM e08_quarantine_objects WHERE quarantine_id=?", (source.quarantine_id,)
            )
            if fault_at == "D":
                raise RuntimeError("fault D")
            absent = self.connection.execute(
                "SELECT NOT EXISTS(SELECT 1 FROM e08_import_sources WHERE source_version_id=?) "
                "AND NOT EXISTS(SELECT 1 FROM e08_quarantine_objects WHERE quarantine_id=?)",
                (plan.source_version_id, source.quarantine_id),
            ).fetchone()[0]
            dangling = self.connection.execute(
                "SELECT COUNT(*) FROM record_relations WHERE parent_record_id=? OR child_record_id=?",
                (source.source_id, source.source_id),
            ).fetchone()[0]
            if not absent or dangling:
                raise RuntimeError("deletion verification failed")
            if fault_at == "E":
                raise RuntimeError("fault E")
            if fault_at == "F":
                raise RuntimeError("fault F")
            verification = identity_digest(
                {"plan": plan.plan_id, "deleted": len(delete_ids) + 1, "invalidated": len(invalidate_ids)}
            )
            self.connection.execute(
                "INSERT INTO deletion_receipts(receipt_id,plan_id,request_id,records_deleted,"
                "records_invalidated,records_recomputed,verification_hash,executed_at,created_at) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (receipt_id, plan.plan_id, request_id, len(delete_ids) + 1, len(invalidate_ids),
                 0, verification, now, now),
            )
            self.connection.execute(
                "UPDATE deletion_plans SET status='completed',executed_at=?,receipt_id=? WHERE plan_id=?",
                (now, receipt_id, plan.plan_id),
            )
            self.connection.execute(
                "UPDATE deletion_requests SET status='completed' WHERE request_id=?", (request_id,)
            )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            self.reload()
            raise E08BoundaryError(E08ErrorCode.STORAGE_FAILURE) from None
        self.reload()
        return ImportDeletionReceipt(
            receipt_id, plan.plan_id, len(delete_ids) + 1, len(invalidate_ids),
            True, True, True, True,
        )


class E08ImportService:
    """Owns parsing, preview, exact consent, commit, correction and deletion."""

    def __init__(
        self,
        quarantine: FilesystemQuarantine,
        *,
        parser: CandidateParser | None = None,
        profile: PlainTextResourceProfile = PLAIN_TEXT_PROFILE,
        policy_record_id: str = "e08-local-never-cloud",
        store: E08CanonicalStore,
    ) -> None:
        self.quarantine = quarantine
        self.parser = parser or PlainTextParser()
        self.profile = profile
        self.policy_record_id = policy_record_id
        self.store = store
        self.policy_lineage_id = self.store.resolve_policy(policy_record_id)[2]
        self.events: list[dict[str, str]] = []
        self._candidates: dict[str, ParsedImportCandidate] = {}
        self._previews: dict[str, tuple[ParsedImportCandidate, ImportPreview]] = {}
        self._consents: dict[str, tuple[ParsedImportCandidate, ImportPreview, ImportConsent]] = {}
        self._consumed_consents: set[str] = set()
        self._plans: dict[str, ImportDeletionPlan] = {}

    @property
    def parser_identity(self) -> str:
        return identity_digest((self.parser.name, self.parser.version, self.parser.config_digest))

    def intake(
        self,
        user_path: str,
        *,
        declared_mime: str | None = None,
        declared_encoding: str | None = None,
    ) -> QuarantineRecord:
        try:
            self.policy_lineage_id = self.store.resolve_policy(self.policy_record_id)[2]
            return self.quarantine.intake(
                user_path,
                profile=self.profile,
                parser_identity=self.parser_identity,
                policy_lineage_id=self.policy_lineage_id,
                declared_mime=declared_mime,
                declared_encoding=declared_encoding,
            )
        except FilesystemBoundaryError as exc:
            code = _REJECTION_CODES.get(exc.code, E08ErrorCode.FILESYSTEM_REJECTED)
            raise E08BoundaryError(code) from None

    def parse(self, quarantine_id: str) -> ParsedImportCandidate:
        snapshot = self._snapshot(quarantine_id)
        record = snapshot.record
        if record.declared_encoding is not None and self._encoding(record.declared_encoding) != "utf8":
            self._reject(quarantine_id, E08ErrorCode.UNSUPPORTED_DECLARATION)
        if record.declared_mime is not None and record.declared_mime.casefold().split(";", 1)[0].strip() != "text/plain":
            self._reject(quarantine_id, E08ErrorCode.UNSUPPORTED_DECLARATION)
        try:
            candidate = self.parser.parse(
                snapshot.bounded_bytes,
                quarantine_id=record.quarantine_id,
                source_candidate_id=record.source_candidate_id,
                source_version_id=record.source_version_id,
                protected_digest_ref=record.protected_digest_ref,
                policy_lineage_id=record.policy_lineage_id,
                profile=self.profile,
                rejection=self._parser_rejection,
            )
            self._validate_candidate(candidate, record, snapshot.bounded_bytes)
        except E08BoundaryError as exc:
            self.quarantine.transition(quarantine_id, "rejected", exc.code.value)
            self._event(quarantine_id, "rejected", exc.code.value)
            raise
        except Exception:
            self.quarantine.transition(quarantine_id, "rejected", "malformed_candidate")
            self._event(quarantine_id, "rejected", "malformed_candidate")
            raise E08BoundaryError(E08ErrorCode.MALFORMED_CANDIDATE) from None
        self.quarantine.transition(quarantine_id, "parsed")
        self._candidates[candidate.candidate_id] = candidate
        self._event(quarantine_id, "parsed", "accepted")
        return candidate

    def preview(
        self,
        candidate: ParsedImportCandidate,
        *,
        mappings: tuple[ProposedMapping, ...] | None = None,
        transformations: tuple[ImportTransformation, ...] = (),
        duplicate_decision: str = "not_duplicate",
        correction_of: str | None = None,
    ) -> ImportPreview:
        if self._candidates.get(candidate.candidate_id) is not candidate:
            raise E08BoundaryError(E08ErrorCode.CAPABILITY_MISMATCH)
        duplicate = any(
            source.protected_digest_ref == candidate.protected_digest_ref
            and source.state != "deleted"
            for source in self.store.sources.values()
        )
        if duplicate and duplicate_decision not in {"import_separate", "reject"}:
            raise E08BoundaryError(E08ErrorCode.DUPLICATE_DECISION_REQUIRED)
        if duplicate and duplicate_decision == "reject":
            raise E08BoundaryError(E08ErrorCode.DUPLICATE_REJECTED)
        if not duplicate:
            duplicate_decision = "not_duplicate"
        if correction_of is not None and correction_of not in self.store.sources:
            raise E08BoundaryError(E08ErrorCode.CORRECTION_TARGET_INVALID)

        proposed = mappings or tuple(
            ProposedMapping(item.segment_id, CanonicalMapping.ATTRIBUTED_VERBATIM_REPORT)
            for item in candidate.segments
        )
        if (
            len(proposed) != candidate.segment_count
            or {item.segment_id for item in proposed}
            != {item.segment_id for item in candidate.segments}
            or any(not isinstance(item.mapping, CanonicalMapping) for item in proposed)
        ):
            raise E08BoundaryError(E08ErrorCode.INVALID_MAPPING)
        self._validate_transformations(candidate, transformations)
        redacted = {item.segment_id for item in transformations if item.kind == "redact"}
        if any(
            item.segment_id in redacted
            and item.mapping == CanonicalMapping.ATTRIBUTED_VERBATIM_REPORT
            for item in proposed
        ):
            raise E08BoundaryError(E08ErrorCode.INVALID_MAPPING)
        samples = tuple(html.escape(item.text[:256], quote=True) for item in candidate.segments[:8])
        material = {
            "candidate_id": candidate.candidate_id,
            "profile_identity": candidate.profile_identity,
            "parser": (candidate.parser_name, candidate.parser_version, candidate.parser_config_digest),
            "mappings": [(item.segment_id, item.mapping.value) for item in proposed],
            "transformations": [asdict(item) for item in transformations],
            "policy_lineage_id": candidate.policy_lineage_id,
            "duplicate_decision": duplicate_decision,
            "correction_of": correction_of,
        }
        preview = ImportPreview(
            preview_id=identity_digest(material),
            candidate_id=candidate.candidate_id,
            source_type="standalone-plain-text",
            profile_id=candidate.profile_id,
            byte_count=candidate.byte_count,
            character_count=candidate.character_count,
            physical_line_count=candidate.physical_line_count,
            segment_count=candidate.segment_count,
            encoding=candidate.encoding,
            bom=candidate.bom,
            parser_identity=self.parser_identity,
            mappings=proposed,
            transformations=transformations,
            escaped_samples=samples,
            samples_truncated=candidate.segment_count > len(samples)
            or any(len(item.text) > 256 for item in candidate.segments[:8]),
            privacy_effect="local_only_never_cloud_inherited",
            policy_lineage_id=candidate.policy_lineage_id,
            deletion_implication="source_and_exclusive_descendants_governed_together",
            duplicate_decision=duplicate_decision,
            correction_of=correction_of,
        )
        self._previews[preview.preview_id] = (candidate, preview)
        return preview

    def issue_consent(
        self, candidate: ParsedImportCandidate, preview: ImportPreview, *, approved: bool
    ) -> ImportConsent:
        issued = self._previews.get(preview.preview_id)
        if not approved or issued is None or issued[0] is not candidate or issued[1] is not preview:
            raise E08BoundaryError(E08ErrorCode.CAPABILITY_MISMATCH)
        consent = ImportConsent(
            "consent-" + secrets.token_hex(24),
            candidate.candidate_id,
            preview.preview_id,
            candidate.policy_lineage_id,
        )
        del self._previews[preview.preview_id]
        self._consents[consent.consent_id] = (candidate, preview, consent)
        return consent

    def commit(
        self,
        candidate: ParsedImportCandidate,
        preview: ImportPreview,
        consent: ImportConsent,
        *,
        inject_failure: bool = False,
    ) -> ImportCommitResult:
        if consent.consent_id in self._consumed_consents:
            raise E08BoundaryError(E08ErrorCode.CAPABILITY_CONSUMED)
        issued = self._consents.pop(consent.consent_id, None)
        self._consumed_consents.add(consent.consent_id)
        if (
            issued is None
            or issued[0] is not candidate
            or issued[1] is not preview
            or issued[2] is not consent
        ):
            raise E08BoundaryError(E08ErrorCode.CAPABILITY_MISMATCH)
        self._final_revalidation(candidate, preview, consent)

        snapshot = self._snapshot(candidate.quarantine_id)
        try:
            result = self._canonical_commit(
                candidate,
                preview,
                consent,
                snapshot.bounded_bytes,
                inject_failure=inject_failure,
            )
        except Exception as exc:
            self.store.reload()
            if isinstance(exc, E08BoundaryError):
                raise
            raise E08BoundaryError(E08ErrorCode.STORAGE_FAILURE) from None
        with suppress(FilesystemBoundaryError):
            self.quarantine.transition(candidate.quarantine_id, "committed")
        self._candidates.pop(candidate.candidate_id, None)
        self._event(candidate.quarantine_id, "committed", "accepted")
        return result

    def discard_quarantine(self, quarantine_id: str) -> None:
        """Abandon a rejected or uncommitted object through an explicit path."""
        try:
            snapshot = self.quarantine.snapshot(quarantine_id)
        except FilesystemBoundaryError:
            raise E08BoundaryError(E08ErrorCode.SOURCE_STALE) from None
        if snapshot.record.processing_state == "committed":
            raise E08BoundaryError(E08ErrorCode.CAPABILITY_MISMATCH)
        self.quarantine.remove(quarantine_id)
        self._candidates = {
            key: value
            for key, value in self._candidates.items()
            if value.quarantine_id != quarantine_id
        }
        self._event(quarantine_id, "discarded", "governed_abandonment")

    def prepare_deletion(self, source_version_id: str) -> ImportDeletionPlan:
        if source_version_id not in self.store.sources:
            raise E08BoundaryError(E08ErrorCode.DELETION_PLAN_INVALID)
        delete_ids, invalidate_ids = self._deletion_closure(source_version_id)
        plan_id = "delete-" + secrets.token_hex(16)
        plan = ImportDeletionPlan(
            plan_id,
            source_version_id,
            tuple(sorted(delete_ids)),
            tuple(sorted(invalidate_ids)),
            self.store.graph_identity(),
            "DELETE IMPORTED SOURCE",
        )
        self._plans[plan_id] = plan
        return plan

    def execute_deletion(
        self,
        plan: ImportDeletionPlan,
        confirmation: str,
        *,
        inject_failure: bool = False,
        fault_at: str | None = None,
    ) -> ImportDeletionReceipt:
        if self._plans.get(plan.plan_id) is not plan:
            raise E08BoundaryError(E08ErrorCode.DELETION_PLAN_INVALID)
        if confirmation != plan.confirmation:
            raise E08BoundaryError(E08ErrorCode.DELETION_CANCELLED)
        current_delete, current_invalidate = self._deletion_closure(plan.source_version_id)
        if (
            self.store.graph_identity() != plan.graph_identity
            or tuple(sorted(current_delete)) != plan.delete_ids
            or tuple(sorted(current_invalidate)) != plan.invalidate_ids
        ):
            raise E08BoundaryError(E08ErrorCode.DELETION_PLAN_STALE)
        source = self.store.sources[plan.source_version_id]
        receipt = self.store.delete_import(
            plan, fault_at=fault_at or ("C" if inject_failure else None)
        )
        self.quarantine.remove(source.quarantine_id)
        del self._plans[plan.plan_id]
        return receipt

    def _canonical_commit(
        self,
        candidate: ParsedImportCandidate,
        preview: ImportPreview,
        consent: ImportConsent,
        original_bytes: bytes,
        *,
        inject_failure: bool = False,
    ) -> ImportCommitResult:
        source_id = candidate.source_candidate_id
        source_version_id = candidate.source_version_id
        source = CanonicalSource(
            source_id,
            source_version_id,
            candidate.quarantine_id,
            candidate.protected_digest_ref,
            candidate.byte_count,
            self.parser_identity,
            candidate.profile_identity,
            candidate.policy_lineage_id,
            preview.preview_id,
            consent.consent_id,
            preview.correction_of,
            "active",
            original_bytes,
        )
        self.store.sources[source_version_id] = source
        transformation_by_segment = {item.segment_id: item for item in preview.transformations}
        mappings = {item.segment_id: item.mapping for item in preview.mappings}
        segment_ids: list[str] = []
        record_ids: list[str] = []
        for segment in candidate.segments:
            locator = (
                segment.physical_line,
                segment.character_start,
                segment.character_end,
                segment.byte_start,
                segment.byte_end,
                segment.newline,
            )
            segment_node_id = "segment-" + segment.segment_id
            self.store.nodes[segment_node_id] = CanonicalNode(
                segment_node_id,
                segment_node_id + "-v1",
                "source_segment",
                source_version_id,
                (),
                candidate.policy_lineage_id,
                locator,
                "exact-byte-locator-v1",
                "active",
                segment.text,
            )
            segment_ids.append(segment_node_id)
            transformation = transformation_by_segment.get(segment.segment_id)
            if transformation is not None and transformation.kind == "exclude":
                transform_id = "transform-" + identity_digest(asdict(transformation))
                self.store.nodes[transform_id] = CanonicalNode(
                    transform_id,
                    transform_id + "-v1",
                    "exclusion",
                    source_version_id,
                    (segment_node_id,),
                    candidate.policy_lineage_id,
                    locator,
                    transformation.method_version,
                    "active",
                    None,
                )
                self.store.relations.add((segment_node_id, transform_id, "derived_from"))
                continue
            content = segment.text
            parent = segment_node_id
            if transformation is not None:
                transform_id = "transform-" + identity_digest(asdict(transformation))
                content = transformation.replacement or ""
                self.store.nodes[transform_id] = CanonicalNode(
                    transform_id,
                    transform_id + "-v1",
                    "redaction",
                    source_version_id,
                    (segment_node_id,),
                    candidate.policy_lineage_id,
                    locator,
                    transformation.method_version,
                    "active",
                    content,
                )
                self.store.relations.add((segment_node_id, transform_id, "derived_from"))
                parent = transform_id
            mapping = mappings[segment.segment_id]
            record_id = "record-" + identity_digest((candidate.candidate_id, segment.segment_id, mapping))
            kind = (
                "attributed_verbatim_report"
                if mapping == CanonicalMapping.ATTRIBUTED_VERBATIM_REPORT
                else "review_needed_assertion_proposal"
            )
            self.store.nodes[record_id] = CanonicalNode(
                record_id,
                record_id + "-v1",
                kind,
                source_version_id,
                (parent,),
                candidate.policy_lineage_id,
                locator,
                "e08-canonical-mapping-v1",
                "active" if kind == "attributed_verbatim_report" else "review_needed",
                content,
            )
            self.store.relations.add((parent, record_id, "derived_from"))
            record_ids.append(record_id)
        if preview.correction_of is not None:
            old = self.store.sources[preview.correction_of]
            self.store.sources[preview.correction_of] = CanonicalSource(
                old.source_id,
                old.source_version_id,
                old.quarantine_id,
                old.protected_digest_ref,
                old.byte_count,
                old.parser_identity,
                old.profile_identity,
                old.policy_lineage_id,
                old.preview_id,
                old.consent_id,
                old.correction_of,
                "superseded",
                old.original_bytes,
            )
            self.store.relations.add((preview.correction_of, source_version_id, "corrects"))
        self.store.persist_import(
            source,
            policy_record_id=self.policy_record_id,
            inject_failure=inject_failure,
        )
        return ImportCommitResult(
            source_id,
            source_version_id,
            tuple(record_ids),
            tuple(segment_ids),
            preview.correction_of,
        )

    def _final_revalidation(
        self,
        candidate: ParsedImportCandidate,
        preview: ImportPreview,
        consent: ImportConsent,
    ) -> None:
        current_policy = self.store.resolve_policy(self.policy_record_id)[2]
        if candidate.policy_lineage_id != current_policy:
            raise E08BoundaryError(E08ErrorCode.POLICY_STALE)
        if candidate.profile_identity != self.profile.identity or preview.profile_id != self.profile.profile_id:
            raise E08BoundaryError(E08ErrorCode.PARSER_STALE)
        if preview.parser_identity != self.parser_identity:
            raise E08BoundaryError(E08ErrorCode.PARSER_STALE)
        if consent.policy_lineage_id != current_policy:
            raise E08BoundaryError(E08ErrorCode.POLICY_STALE)
        snapshot = self._snapshot(candidate.quarantine_id)
        if not snapshot.source_identity_current:
            raise E08BoundaryError(E08ErrorCode.SOURCE_STALE)
        if snapshot.record.protected_digest_ref != candidate.protected_digest_ref:
            raise E08BoundaryError(E08ErrorCode.SOURCE_STALE)
        try:
            reparsed = PlainTextParser().parse(
                snapshot.bounded_bytes,
                quarantine_id=candidate.quarantine_id,
                source_candidate_id=candidate.source_candidate_id,
                source_version_id=candidate.source_version_id,
                protected_digest_ref=candidate.protected_digest_ref,
                policy_lineage_id=candidate.policy_lineage_id,
                profile=self.profile,
                rejection=self._parser_rejection,
            )
        except Exception:
            raise E08BoundaryError(E08ErrorCode.SOURCE_STALE) from None
        if reparsed != candidate:
            raise E08BoundaryError(E08ErrorCode.SOURCE_STALE)

    def _validate_candidate(
        self, candidate: ParsedImportCandidate, record: QuarantineRecord, bounded_bytes: bytes
    ) -> None:
        if not isinstance(candidate, ParsedImportCandidate):
            raise E08BoundaryError(E08ErrorCode.MALFORMED_CANDIDATE)
        if (
            self.parser.name != PlainTextParser.name
            or self.parser.version != PlainTextParser.version
            or self.parser.config_digest != PlainTextParser.config_digest
        ):
            raise E08BoundaryError(E08ErrorCode.MALFORMED_CANDIDATE)
        try:
            certified = PlainTextParser().parse(
                bounded_bytes,
                quarantine_id=record.quarantine_id,
                source_candidate_id=record.source_candidate_id,
                source_version_id=record.source_version_id,
                protected_digest_ref=record.protected_digest_ref,
                policy_lineage_id=record.policy_lineage_id,
                profile=self.profile,
                rejection=self._parser_rejection,
            )
        except Exception:
            raise E08BoundaryError(E08ErrorCode.MALFORMED_CANDIDATE) from None
        if (
            candidate.quarantine_id != record.quarantine_id
            or candidate.source_version_id != record.source_version_id
            or candidate.protected_digest_ref != record.protected_digest_ref
            or candidate.byte_count != len(bounded_bytes)
            or candidate.profile_identity != self.profile.identity
            or candidate.parser_name != self.parser.name
            or candidate.parser_version != self.parser.version
            or candidate.parser_config_digest != self.parser.config_digest
            or candidate.policy_lineage_id != self.policy_lineage_id
            or not candidate.untrusted_content
            or candidate.segment_count != len(candidate.segments)
            or candidate != certified
        ):
            raise E08BoundaryError(E08ErrorCode.MALFORMED_CANDIDATE)
        for segment in candidate.segments:
            try:
                recovered = bounded_bytes[segment.byte_start : segment.byte_end].decode("utf-8")
            except (UnicodeDecodeError, IndexError):
                raise E08BoundaryError(E08ErrorCode.MALFORMED_CANDIDATE) from None
            if (
                recovered != segment.text
                or segment.source_version_id != candidate.source_version_id
                or segment.byte_start < (3 if candidate.bom else 0)
                or segment.byte_end < segment.byte_start
                or segment.character_end - segment.character_start != len(segment.text)
            ):
                raise E08BoundaryError(E08ErrorCode.MALFORMED_CANDIDATE)

    def _validate_transformations(
        self,
        candidate: ParsedImportCandidate,
        transformations: tuple[ImportTransformation, ...],
    ) -> None:
        segment_ids = {item.segment_id for item in candidate.segments}
        seen: set[str] = set()
        for item in transformations:
            if (
                item.segment_id not in segment_ids
                or item.segment_id in seen
                or item.kind not in {"exclude", "redact"}
                or not item.method_version
                or (item.kind == "exclude" and item.replacement is not None)
                or (item.kind == "redact" and item.replacement is None)
                or (item.replacement is not None and len(item.replacement) > self.profile.maximum_line_code_points)
            ):
                raise E08BoundaryError(E08ErrorCode.INVALID_TRANSFORMATION)
            seen.add(item.segment_id)

    def _deletion_closure(self, source_version_id: str) -> tuple[set[str], set[str]]:
        roots = {
            key for key, node in self.store.nodes.items() if node.source_version_id == source_version_id
        }
        delete_ids = set(roots)
        invalidate_ids: set[str] = set()
        changed = True
        while changed:
            changed = False
            for record_id, node in self.store.nodes.items():
                if record_id in delete_ids or record_id in invalidate_ids or not node.parent_ids:
                    continue
                affected = any(parent in delete_ids or parent in invalidate_ids for parent in node.parent_ids)
                if not affected:
                    continue
                if all(parent in delete_ids for parent in node.parent_ids):
                    delete_ids.add(record_id)
                else:
                    invalidate_ids.add(record_id)
                changed = True
        return delete_ids, invalidate_ids

    def _snapshot(self, quarantine_id: str) -> QuarantineSnapshot:
        try:
            return self.quarantine.snapshot(quarantine_id)
        except FilesystemBoundaryError:
            raise E08BoundaryError(E08ErrorCode.SOURCE_STALE) from None

    def _reject(self, quarantine_id: str, code: E08ErrorCode) -> None:
        self.quarantine.transition(quarantine_id, "rejected", code.value)
        self._event(quarantine_id, "rejected", code.value)
        raise E08BoundaryError(code)

    @staticmethod
    def _encoding(value: str) -> str:
        return value.casefold().replace("-", "").replace("_", "").strip()

    @staticmethod
    def _parser_rejection(code: str) -> E08BoundaryError:
        return E08BoundaryError(_REJECTION_CODES.get(code, E08ErrorCode.MALFORMED_RESOURCE))

    def _event(self, quarantine_id: str, status: str, reason: str) -> None:
        self.events.append(
            {
                "event_code": "e08_import_boundary",
                "opaque_id": quarantine_id,
                "component_version": "e08-import-service-v1",
                "profile": self.profile.profile_id,
                "status": status,
                "reason": reason,
            }
        )
