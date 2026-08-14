"""E09 local lexical retrieval application service with typed manifests.

The service owns one disposable projection, staleness/invalidation detection,
corruption checks and the no-projection fallback.  Retrieval never becomes
canonical authority and cannot bypass policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from psyche_os.projections.e09_lexical import (
    LexicalConfig,
    LexicalProjection,
    ProjectionManifest,
    RetrievalResult,
    _digest,
    build_lexical_projection,
    canonical_input_identity,
    policy_identity,
    projection_is_intact,
    relation_expansion,
    retrieve,
    tokenize,
)

RETRIEVER_VERSION: str = "e09-lexical-retriever-v1"


class RetrievalStatus(StrEnum):
    OK = "ok"
    UNAVAILABLE = "unavailable"


class RetrievalUnavailableReason(StrEnum):
    NO_PROJECTION = "no_projection"
    PROJECTION_STALE = "projection_stale"
    PROJECTION_BLOCKED = "projection_blocked"
    PROJECTION_CORRUPT = "projection_corrupt"


@dataclass(frozen=True, slots=True)
class RetrievalManifest:
    """Typed retrieval manifest; forward-compatible with a future ContextManifest."""

    query_id: str
    purpose: str
    query_text: str
    query_representation: str
    query_version: str
    projection_manifest_id: str | None
    canonical_cutoff: str | None
    selected_ids: tuple[tuple[str, str], ...]
    scores: tuple[int, ...]
    policy_identity: str
    retriever_version: str

    def __repr__(self) -> str:
        return (
            f"RetrievalManifest(query_id={self.query_id!r}, purpose={self.purpose!r}, "
            f"selected_count={len(self.selected_ids)!r})"
        )


@dataclass(frozen=True, slots=True)
class RetrievalOutcome:
    """Truthful retrieval outcome; unavailable never fabricates results."""

    status: str
    reason: str | None
    manifest: RetrievalManifest | None
    results: tuple[RetrievalResult, ...]

    @property
    def ok(self) -> bool:
        return self.status == RetrievalStatus.OK.value


class E09RetrievalService:
    """Builds, rebuilds and queries a disposable lexical projection."""

    def __init__(self, connection: Any, config: LexicalConfig | None = None) -> None:
        self.connection = connection
        self.config = config or LexicalConfig()
        self.projection: LexicalProjection | None = None

    def build(self) -> ProjectionManifest:
        """Build (or rebuild) the projection from current canonical data."""
        self.projection = build_lexical_projection(self.connection, self.config)
        return self.projection.manifest

    def rebuild(self) -> ProjectionManifest:
        return self.build()

    def drop(self) -> None:
        """Delete the disposable projection; canonical data is untouched."""
        self.projection = None

    def is_stale(self) -> bool:
        if self.projection is None:
            return True
        m = self.projection.manifest
        return (
            canonical_input_identity(self.connection) != m.canonical_input_identity
            or policy_identity(self.connection) != m.policy_identity
        )

    def is_corrupt(self) -> bool:
        return self.projection is not None and not projection_is_intact(self.projection)

    def retrieve(self, query: str, purpose: str = "local_lexical_retrieval") -> RetrievalOutcome:
        query_tokens = " ".join(tokenize(query, self.config))
        query_id = "e09-q-" + _digest((purpose, query, RETRIEVER_VERSION))[:12]

        def unavailable(reason: RetrievalUnavailableReason) -> RetrievalOutcome:
            return RetrievalOutcome(
                status=RetrievalStatus.UNAVAILABLE.value,
                reason=reason.value,
                manifest=RetrievalManifest(
                    query_id=query_id,
                    purpose=purpose,
                    query_text=query,
                    query_representation="lexical_tokens_v1",
                    query_version=query_tokens,
                    projection_manifest_id=(
                        self.projection.manifest.projection_id if self.projection else None
                    ),
                    canonical_cutoff=(
                        self.projection.manifest.canonical_cutoff if self.projection else None
                    ),
                    selected_ids=(),
                    scores=(),
                    policy_identity=(
                        self.projection.manifest.policy_identity if self.projection else ""
                    ),
                    retriever_version=RETRIEVER_VERSION,
                ),
                results=(),
            )

        if self.projection is None:
            return unavailable(RetrievalUnavailableReason.NO_PROJECTION)
        if self.projection.manifest.status != "ready":
            return unavailable(RetrievalUnavailableReason.PROJECTION_BLOCKED)
        if self.is_corrupt():
            return unavailable(RetrievalUnavailableReason.PROJECTION_CORRUPT)
        if self.is_stale():
            return unavailable(RetrievalUnavailableReason.PROJECTION_STALE)

        raw = retrieve(self.projection, query, self.config)
        expansions = relation_expansion(self.connection, [r.record_id for r in raw])
        results = tuple(
            RetrievalResult(
                record_id=r.record_id,
                version_id=r.version_id,
                kind=r.kind,
                score=r.score,
                matched_terms=r.matched_terms,
                relation_expansion=expansions.get(r.record_id, ()),
            )
            for r in raw
        )
        manifest = RetrievalManifest(
            query_id=query_id,
            purpose=purpose,
            query_text=query,
            query_representation="lexical_tokens_v1",
            query_version=query_tokens,
            projection_manifest_id=self.projection.manifest.projection_id,
            canonical_cutoff=self.projection.manifest.canonical_cutoff,
            selected_ids=tuple((r.record_id, r.version_id) for r in results),
            scores=tuple(r.score for r in results),
            policy_identity=self.projection.manifest.policy_identity,
            retriever_version=RETRIEVER_VERSION,
        )
        return RetrievalOutcome(RetrievalStatus.OK.value, None, manifest, results)
