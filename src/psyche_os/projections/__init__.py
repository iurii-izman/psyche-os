"""Disposable, rebuildable, local projections derived from canonical records.

Projections are never evidence, source, authority or canonical state.  They can
be deleted at any time and rebuilt deterministically from canonical data.
"""

from psyche_os.projections.e09_lexical import (
    BUILDER_VERSION,
    PROJECTION_TYPE,
    LexicalConfig,
    LexicalProjection,
    ProjectionManifest,
    RelationRef,
    RetrievalResult,
    build_lexical_projection,
    canonical_input_identity,
    policy_identity,
    projection_is_intact,
    relation_expansion,
    retrieve,
    tokenize,
)

__all__ = [
    "BUILDER_VERSION",
    "PROJECTION_TYPE",
    "LexicalConfig",
    "LexicalProjection",
    "ProjectionManifest",
    "RelationRef",
    "RetrievalResult",
    "build_lexical_projection",
    "canonical_input_identity",
    "policy_identity",
    "projection_is_intact",
    "relation_expansion",
    "retrieve",
    "tokenize",
]
