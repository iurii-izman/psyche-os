"""E08 quarantine-to-canonical application authority."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from enum import StrEnum
import html
import secrets
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
            f"CanonicalSource(source_id={self.source_id!r}, "
            f"source_version_id={self.source_version_id!r}, quarantine_id={self.quarantine_id!r}, "
            f"byte_count={self.byte_count!r}, state={self.state!r}, original_bytes=<redacted>)"
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
            f"CanonicalNode(record_id={self.record_id!r}, version_id={self.version_id!r}, "
            f"kind={self.kind!r}, source_version_id={self.source_version_id!r}, "
            f"parent_ids={self.parent_ids!r}, policy_lineage_id={self.policy_lineage_id!r}, "
            f"locator={self.locator!r}, method_version={self.method_version!r}, "
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


@dataclass(frozen=True, slots=True)
class ImportDeletionPlan:
    plan_id: str
    source_version_id: str
    delete_ids: tuple[str, ...]
    invalidate_ids: tuple[str, ...]
    graph_identity: str
    confirmation: str


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


class E08CanonicalStore:
    """Bounded transactional canonical extension using accepted E03 semantics."""

    def __init__(self) -> None:
        self.sources: dict[str, CanonicalSource] = {}
        self.nodes: dict[str, CanonicalNode] = {}
        self.relations: set[tuple[str, str, str]] = set()
        self.receipts: list[ImportDeletionReceipt] = []

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
        return record_id


class E08ImportService:
    """Owns parsing, preview, exact consent, commit, correction and deletion."""

    def __init__(
        self,
        quarantine: FilesystemQuarantine,
        *,
        parser: CandidateParser | None = None,
        profile: PlainTextResourceProfile = PLAIN_TEXT_PROFILE,
        policy_lineage_id: str = "e08-local-never-cloud-v1",
        store: E08CanonicalStore | None = None,
    ) -> None:
        self.quarantine = quarantine
        self.parser = parser or PlainTextParser()
        self.profile = profile
        self.policy_lineage_id = policy_lineage_id
        self.store = store or E08CanonicalStore()
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
        before = deepcopy((self.store.sources, self.store.nodes, self.store.relations))
        try:
            result = self._canonical_commit(
                candidate, preview, consent, snapshot.bounded_bytes
            )
            if inject_failure:
                raise RuntimeError("injected")
        except Exception as exc:
            self.store.sources, self.store.nodes, self.store.relations = before
            if isinstance(exc, E08BoundaryError):
                raise
            raise E08BoundaryError(E08ErrorCode.STORAGE_FAILURE) from None
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
        backup = deepcopy(
            (self.store.sources, self.store.nodes, self.store.relations, self.store.receipts)
        )
        source = self.store.sources[plan.source_version_id]
        try:
            for record_id in plan.delete_ids:
                self.store.nodes.pop(record_id, None)
            for record_id in plan.invalidate_ids:
                node = self.store.nodes[record_id]
                self.store.nodes[record_id] = CanonicalNode(
                    node.record_id,
                    node.version_id,
                    node.kind,
                    node.source_version_id,
                    node.parent_ids,
                    node.policy_lineage_id,
                    node.locator,
                    node.method_version,
                    "invalidated",
                    None,
                )
            self.store.relations = {
                relation
                for relation in self.store.relations
                if relation[0] not in plan.delete_ids
                and relation[1] not in plan.delete_ids
                and relation[0] != plan.source_version_id
                and relation[1] != plan.source_version_id
            }
            self.store.sources.pop(plan.source_version_id)
            if inject_failure:
                raise RuntimeError("injected")
            self.quarantine.remove(source.quarantine_id)
            exported = self.store.export()
            receipt = ImportDeletionReceipt(
                "receipt-" + secrets.token_hex(16),
                plan.plan_id,
                len(plan.delete_ids) + 1,
                len(plan.invalidate_ids),
                not self.quarantine.contains(source.quarantine_id),
                plan.source_version_id not in self.store.sources
                and all(record_id not in self.store.nodes for record_id in plan.delete_ids),
                plan.source_version_id not in exported["source_versions"]
                and all(record_id not in exported["record_ids"] for record_id in plan.delete_ids),
                plan.source_version_id not in self.store.sources,
            )
            self.store.receipts.append(receipt)
        except Exception:
            (
                self.store.sources,
                self.store.nodes,
                self.store.relations,
                self.store.receipts,
            ) = backup
            raise E08BoundaryError(E08ErrorCode.STORAGE_FAILURE) from None
        del self._plans[plan.plan_id]
        return receipt

    def _canonical_commit(
        self,
        candidate: ParsedImportCandidate,
        preview: ImportPreview,
        consent: ImportConsent,
        original_bytes: bytes,
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
        if candidate.policy_lineage_id != self.policy_lineage_id:
            raise E08BoundaryError(E08ErrorCode.POLICY_STALE)
        if candidate.profile_identity != self.profile.identity or preview.profile_id != self.profile.profile_id:
            raise E08BoundaryError(E08ErrorCode.PARSER_STALE)
        if preview.parser_identity != self.parser_identity:
            raise E08BoundaryError(E08ErrorCode.PARSER_STALE)
        if consent.policy_lineage_id != self.policy_lineage_id:
            raise E08BoundaryError(E08ErrorCode.POLICY_STALE)
        snapshot = self._snapshot(candidate.quarantine_id)
        if not snapshot.source_identity_current:
            raise E08BoundaryError(E08ErrorCode.SOURCE_STALE)
        if snapshot.record.protected_digest_ref != candidate.protected_digest_ref:
            raise E08BoundaryError(E08ErrorCode.SOURCE_STALE)
        try:
            reparsed = self.parser.parse(
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
