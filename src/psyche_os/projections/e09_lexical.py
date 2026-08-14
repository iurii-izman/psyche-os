"""E09 rebuildable local lexical projection over synthetic canonical records.

This module builds a process-local deterministic inverted index over accepted
canonical text-bearing records (source artifacts, reports, observations,
assertions, claims, unknowns).  It is a disposable derivative:

- Canonical V5 (and its V2 semantic tables) remains the sole authority.
- A projection is never evidence, source, report, assertion, claim, policy or
  canonical state.  It can be deleted completely and rebuilt from canonical
  data at any time.
- Ranking is deterministic and lexical only.  A returned record means exactly
  ``retrieved_by_e09_lexical_algorithm`` — never psychologically important,
  true, causal or diagnostic.
- No AI, network, embeddings, external service or new runtime dependency.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Any, Literal
import unicodedata

BUILDER_VERSION: str = "e09-lexical-builder-v1"
PROJECTION_TYPE: str = "lexical_inverted_index"

# Frozen canonical text-bearing tables.  Each entry is
# (table, active-row filter, text columns, kind label).  Imported E08 text is
# already projected into reports/assertions, so e08_import_nodes is not indexed
# separately (that would double-index the same canonical record ids).
_TEXT_SOURCES: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    ("source_artifacts", "is_active=1 AND semantic_version=2", ("source_label", "rights_note"), "source_artifact"),
    ("reports", "is_active=1 AND semantic_version=2", ("title", "verbatim_content", "report_kind"), "report"),
    ("observations", "is_active=1 AND semantic_version=2", ("value_or_coded_state", "construct_phenomenon", "context", "observation_kind"), "observation"),
    ("assertions", "is_active=1 AND semantic_version=2", ("predicate", "object_value", "scope", "modality"), "assertion"),
    ("claims", "is_active=1 AND semantic_version=2", ("claim_type", "claim_status", "proposition", "bounded_wording", "claim_body"), "claim"),
    ("unknowns", "is_active=1", ("question", "scope", "why_matters", "status"), "unknown"),
)

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _digest(value: Any) -> str:
    """Deterministic identity digest over non-secret metadata, not content."""
    encoded = json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class LexicalConfig:
    """Frozen lexical retrieval configuration; its digest is part of the manifest."""

    max_results: int = 20
    unicode_normalization: Literal["NFC", "NFD", "NFKC", "NFKD"] = "NFKC"
    case_fold: bool = True

    @property
    def digest(self) -> str:
        return _digest({"max_results": self.max_results, "unicode_normalization": self.unicode_normalization, "case_fold": self.case_fold})


@dataclass(frozen=True, slots=True)
class ProjectionManifest:
    """Typed manifest naming every input, builder and config of one projection."""

    projection_id: str
    projection_type: str
    builder_version: str
    config_digest: str
    canonical_schema_version: int
    canonical_cutoff: str | None
    canonical_input_identity: str
    policy_identity: str
    projection_digest: str
    status: str  # "ready" | "blocked"; staleness is derived lazily by the service

    def __repr__(self) -> str:
        return (
            f"ProjectionManifest(projection_id={self.projection_id!r}, "
            f"projection_type={self.projection_type!r}, status={self.status!r}, "
            f"canonical_schema_version={self.canonical_schema_version!r})"
        )


@dataclass(frozen=True, slots=True)
class IndexedRecord:
    """One indexed canonical record.  Raw text is never retained in full."""

    record_id: str
    version_id: str
    kind: str
    token_counts: dict[str, int] = field(repr=False)

    def __repr__(self) -> str:
        return (
            f"IndexedRecord(record_id={self.record_id!r}, version_id={self.version_id!r}, "
            f"kind={self.kind!r}, token_count={sum(self.token_counts.values())!r})"
        )


@dataclass(frozen=True, slots=True)
class RelationRef:
    """Typed reference to an existing canonical relationship, never a new claim."""

    role: str
    related_record_id: str


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """A ranked canonical record/version hit plus preserved relation metadata."""

    record_id: str
    version_id: str
    kind: str
    score: int
    matched_terms: int
    relation_expansion: tuple[RelationRef, ...] = ()

    def __repr__(self) -> str:
        return (
            f"RetrievalResult(record_id={self.record_id!r}, version_id={self.version_id!r}, "
            f"kind={self.kind!r}, score={self.score!r}, matched_terms={self.matched_terms!r})"
        )


@dataclass(frozen=True, slots=True)
class LexicalProjection:
    """Process-local disposable projection: manifest plus inverted index."""

    manifest: ProjectionManifest
    records: tuple[IndexedRecord, ...]
    inverted: dict[str, tuple[int, ...]] = field(repr=False)

    def __repr__(self) -> str:
        return (
            f"LexicalProjection(record_count={len(self.records)!r}, "
            f"token_count={len(self.inverted)!r}, status={self.manifest.status!r})"
        )


def tokenize(text: str, config: LexicalConfig) -> tuple[str, ...]:
    """Normalize and split text into deterministic word tokens.

    Unicode normalization (NFKC by default) then case folding then word-boundary
    splitting.  Punctuation is dropped; no stemming, stopwords or NLP.
    """
    normalized = unicodedata.normalize(config.unicode_normalization, text)
    if config.case_fold:
        normalized = normalized.casefold()
    return tuple(_TOKEN_RE.findall(normalized))


def _count_tokens(text: str, config: LexicalConfig) -> dict[str, int]:
    counts: dict[str, int] = {}
    for token in tokenize(text, config):
        counts[token] = counts.get(token, 0) + 1
    return counts


def _current_schema_version(connection: Any) -> int:
    try:
        row = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
    except Exception:
        return 0
    return int(row[0]) if row and row[0] is not None else 0


def canonical_input_identity(connection: Any) -> str:
    """Digest over the active canonical record/version set the projection indexes.

    A correction (new version id), deletion (row removed or is_active=0) or new
    record changes this identity, marking the projection stale.
    """
    entries: list[tuple[str, str, str]] = []
    for table, where, _cols, _kind in _TEXT_SOURCES:
        for record_id, version_id in connection.execute(
            f"SELECT record_id, version_id FROM {table} WHERE {where} ORDER BY record_id, version_id"
        ):
            entries.append((table, str(record_id), str(version_id)))
    return _digest(sorted(entries))


def policy_identity(connection: Any) -> str:
    """Digest over active canonical policies, so a policy change marks stale."""
    rows = connection.execute(
        "SELECT record_id, policy_id, version_id, sensitivity, processing_location, "
        "cloud_policy, purpose, third_party_scope, retention_policy_id, export_rule, "
        "export_audience, lineage_rule FROM data_policies WHERE is_active=1 ORDER BY record_id"
    ).fetchall()
    return _digest([tuple(str(value) for value in row) for row in rows])


def _policy_allows_local_retrieval(connection: Any) -> bool:
    row = connection.execute(
        "SELECT 1 FROM data_policies WHERE is_active=1 AND "
        "(processing_location != 'local_only' OR cloud_policy != 'never_cloud') LIMIT 1"
    ).fetchone()
    return row is None


def _iter_text_records(connection: Any) -> Iterator[tuple[str, str, str, str]]:
    """Yield (record_id, version_id, kind, text) for active canonical records."""
    for table, where, text_cols, kind in _TEXT_SOURCES:
        columns = "record_id, version_id, " + ", ".join(text_cols)
        for row in connection.execute(f"SELECT {columns} FROM {table} WHERE {where}"):
            record_id, version_id = str(row[0]), str(row[1])
            text = " ".join(str(value) for value in row[2:] if value)
            if text.strip():
                yield record_id, version_id, kind, text


def _canonical_cutoff(connection: Any) -> str | None:
    cutoff: str | None = None
    for table, where, _cols, _kind in _TEXT_SOURCES:
        for (tx_from,) in connection.execute(
            f"SELECT tx_from FROM {table} WHERE {where} AND tx_from IS NOT NULL"
        ):
            if tx_from is not None and (cutoff is None or str(tx_from) > cutoff):
                cutoff = str(tx_from)
    return cutoff


def _projection_digest(
    records: tuple[IndexedRecord, ...],
    inverted: dict[str, tuple[int, ...]],
    builder_version: str,
    config_digest: str,
    canonical_schema_version: int,
    canonical_input_identity: str,
    policy_identity: str,
) -> str:
    return _digest({
        "builder_version": builder_version,
        "config_digest": config_digest,
        "canonical_schema_version": canonical_schema_version,
        "canonical_input_identity": canonical_input_identity,
        "policy_identity": policy_identity,
        "records": [(r.record_id, r.version_id, r.kind, sorted(r.token_counts.items())) for r in records],
        "inverted": {token: list(indices) for token, indices in sorted(inverted.items())},
    })


def build_lexical_projection(
    connection: Any, config: LexicalConfig | None = None
) -> LexicalProjection:
    """Build a disposable projection.  Deterministic for identical inputs/config."""
    config = config or LexicalConfig()
    input_identity = canonical_input_identity(connection)
    policy = policy_identity(connection)
    schema_version = _current_schema_version(connection)
    local_only = _policy_allows_local_retrieval(connection)

    records: list[IndexedRecord] = []
    inverted: dict[str, list[int]] = {}
    if local_only:
        for record_id, version_id, kind, text in _iter_text_records(connection):
            counts = _count_tokens(text, config)
            idx = len(records)
            records.append(IndexedRecord(record_id, version_id, kind, counts))
            for token in counts:
                inverted.setdefault(token, []).append(idx)
    frozen_inverted = {token: tuple(indices) for token, indices in inverted.items()}

    digest = _projection_digest(
        tuple(records), frozen_inverted, BUILDER_VERSION, config.digest,
        schema_version, input_identity, policy,
    )
    projection_id = "e09-proj-" + _digest(
        (BUILDER_VERSION, config.digest, schema_version, input_identity, policy)
    )[:12]
    manifest = ProjectionManifest(
        projection_id=projection_id,
        projection_type=PROJECTION_TYPE,
        builder_version=BUILDER_VERSION,
        config_digest=config.digest,
        canonical_schema_version=schema_version,
        canonical_cutoff=_canonical_cutoff(connection),
        canonical_input_identity=input_identity,
        policy_identity=policy,
        projection_digest=digest,
        status="blocked" if not local_only else "ready",
    )
    return LexicalProjection(manifest, tuple(records), frozen_inverted)


def projection_is_intact(projection: LexicalProjection) -> bool:
    """Return False if in-memory records/inverted were tampered with."""
    m = projection.manifest
    return _projection_digest(
        projection.records, projection.inverted, m.builder_version, m.config_digest,
        m.canonical_schema_version, m.canonical_input_identity, m.policy_identity,
    ) == m.projection_digest


def retrieve(
    projection: LexicalProjection, query: str, config: LexicalConfig | None = None
) -> tuple[RetrievalResult, ...]:
    """Deterministic lexical ranking over one projection.

    Score = total occurrence count of matched query tokens in the record.
    Order = (score desc, matched_terms desc, record_id asc).  Ties are broken
    deterministically by record id.
    """
    config = config or LexicalConfig()
    if projection.manifest.status != "ready":
        return ()
    query_tokens = set(tokenize(query, config))
    if not query_tokens:
        return ()

    acc: dict[int, list[int]] = {}  # record index -> [score, matched_terms]
    for token in query_tokens:
        for idx in projection.inverted.get(token, ()):
            term_frequency = projection.records[idx].token_counts.get(token, 0)
            if idx in acc:
                acc[idx][0] += term_frequency
                acc[idx][1] += 1
            else:
                acc[idx] = [term_frequency, 1]

    ranked = sorted(
        acc.items(),
        key=lambda item: (-item[1][0], -item[1][1], projection.records[item[0]].record_id),
    )[: config.max_results]
    return tuple(
        RetrievalResult(
            record_id=projection.records[idx].record_id,
            version_id=projection.records[idx].version_id,
            kind=projection.records[idx].kind,
            score=score,
            matched_terms=matched,
        )
        for idx, (score, matched) in ranked
    )


def relation_expansion(
    connection: Any, record_ids: Iterable[str]
) -> dict[str, tuple[RelationRef, ...]]:
    """Expose existing canonical relationships for selected records.

    Only accepted typed canonical relations are surfaced: record_relations,
    evidence_links and contradiction membership.  No new claim, contradiction or
    similarity-derived relation is created.
    """
    ids = sorted(set(record_ids))
    if not ids:
        return {}
    placeholders = ",".join("?" for _ in ids)
    args = tuple(ids)
    gathered: dict[str, set[RelationRef]] = {rid: set() for rid in ids}

    for parent, child, kind in connection.execute(
        f"SELECT parent_record_id, child_record_id, relation_kind FROM record_relations "
        f"WHERE parent_record_id IN ({placeholders}) OR child_record_id IN ({placeholders})",
        (*args, *args),
    ):
        parent, child, kind = str(parent), str(child), str(kind)
        if parent in gathered and child != parent:
            gathered[parent].add(RelationRef(kind, child))
        if child in gathered and parent != child:
            gathered[child].add(RelationRef(kind, parent))

    for source, target, relation in connection.execute(
        f"SELECT source_record_id, target_claim_record_id, relation FROM evidence_links "
        f"WHERE source_record_id IN ({placeholders}) OR target_claim_record_id IN ({placeholders})",
        (*args, *args),
    ):
        source, target, relation = str(source), str(target), str(relation)
        if source in gathered:
            gathered[source].add(RelationRef(relation, target))
        if target in gathered:
            gathered[target].add(RelationRef(relation, source))

    for set_id, member_id in connection.execute(
        f"SELECT set_record_id, member_record_id FROM contradiction_members "
        f"WHERE member_record_id IN ({placeholders})",
        args,
    ):
        set_id, member_id = str(set_id), str(member_id)
        if member_id in gathered:
            gathered[member_id].add(RelationRef("contradiction_set", set_id))

    return {
        rid: tuple(sorted(refs, key=lambda ref: (ref.role, ref.related_record_id)))
        for rid, refs in gathered.items()
    }
