"""E09 unit tests: tokenizer, deterministic ranking and result hygiene."""

from __future__ import annotations

from psyche_os.projections.e09_lexical import (
    BUILDER_VERSION,
    PROJECTION_TYPE,
    IndexedRecord,
    LexicalConfig,
    LexicalProjection,
    ProjectionManifest,
    retrieve,
    tokenize,
)


def _projection(docs: list[tuple[str, str]], config: LexicalConfig) -> LexicalProjection:
    records: list[IndexedRecord] = []
    inverted: dict[str, list[int]] = {}
    for record_id, text in docs:
        counts: dict[str, int] = {}
        for token in tokenize(text, config):
            counts[token] = counts.get(token, 0) + 1
        idx = len(records)
        records.append(IndexedRecord(record_id, record_id + "-v1", "report", counts))
        for token in counts:
            inverted.setdefault(token, []).append(idx)
    manifest = ProjectionManifest(
        projection_id="test-proj",
        projection_type=PROJECTION_TYPE,
        builder_version=BUILDER_VERSION,
        config_digest=config.digest,
        canonical_schema_version=5,
        canonical_cutoff=None,
        canonical_input_identity="",
        policy_identity="",
        projection_digest="",
        status="ready",
    )
    return LexicalProjection(manifest, tuple(records), {t: tuple(xs) for t, xs in inverted.items()})


def test_tokenize_normalizes_case_unicode_and_punctuation() -> None:
    config = LexicalConfig()
    assert tokenize("AMBER amber Amber!", config) == ("amber", "amber", "amber")
    assert tokenize("east-bench / indicator_lamp", config) == ("east", "bench", "indicator_lamp")
    assert tokenize("  ", config) == ()


def test_retrieve_ranks_by_term_frequency_then_matched_terms() -> None:
    config = LexicalConfig()
    proj = _projection(
        [("low", "amber"), ("high", "amber amber"), ("mid", "amber lamp lamp")], config
    )
    results = retrieve(proj, "amber lamp", config)
    order = [(r.record_id, r.score, r.matched_terms) for r in results]
    assert order == [
        ("mid", 3, 2),   # amber(1) + lamp(2)
        ("high", 2, 1),  # amber(2)
        ("low", 1, 1),   # amber(1)
    ]


def test_retrieve_ties_break_deterministically_by_record_id() -> None:
    config = LexicalConfig()
    proj = _projection([("zzz", "amber"), ("aaa", "amber")], config)
    results = retrieve(proj, "amber", config)
    assert [r.record_id for r in results] == ["aaa", "zzz"]


def test_retrieve_respects_max_results() -> None:
    config = LexicalConfig(max_results=1)
    proj = _projection([("a", "amber"), ("b", "amber")], config)
    assert [r.record_id for r in retrieve(proj, "amber", config)] == ["a"]


def test_result_and_manifest_repr_hide_content() -> None:
    config = LexicalConfig()
    proj = _projection([("secret", "very private content")], config)
    (result,) = retrieve(proj, "private", config)
    assert "private" not in repr(result)
    assert "content" not in repr(proj)
