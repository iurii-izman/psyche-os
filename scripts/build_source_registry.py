"""Build the canonical research source registry from reviewed workstream fragments.

This is a documentation build helper, not PSYCHE OS production code. It preserves
every stable source ID because workstream citations depend on those IDs. If two
records intentionally describe the same URL, both remain and receive
``same_source_as`` aliases; the unique-source count is reported separately.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
INPUTS = (
    ROOT / "docs/research/workstreams/SOURCES_CLINICAL.yaml",
    ROOT / "docs/research/workstreams/SOURCES_MEASUREMENT.yaml",
    ROOT / "docs/research/workstreams/SOURCES_SECURITY_ARCHITECTURE.yaml",
)
OUTPUT = ROOT / "docs/research/SOURCE_REGISTRY.yaml"
SNAPSHOT_DATE = "2026-08-10"


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def normalize(raw: dict[str, Any]) -> dict[str, Any]:
    publication_date = str(raw.get("publication_date") or raw.get("year") or "unknown")
    currentness = raw.get("currentness") or (
        f"Reviewed on {SNAPSHOT_DATE}; review again by {raw.get('review_due', 'the next release')} and on correction/retraction."
    )
    source_type = raw.get("type") or raw.get("source_type") or "unspecified"
    organization = raw.get("authors_or_organization") or raw.get("authors_or_body") or "unknown"
    implications = raw.get("project_implications") or raw.get("project_implication")
    rights = (
        raw.get("rights_notes")
        or raw.get("rights")
        or "Citation/link only; rights require review before reuse."
    )

    return {
        "id": str(raw["id"]),
        "title": str(raw["title"]),
        "authors_or_organization": str(organization),
        "type": str(source_type),
        "publication": str(raw.get("publication") or organization),
        "publication_date": publication_date,
        "url": str(raw["url"]),
        "accessed_at": str(raw.get("accessed_at") or raw.get("accessed") or SNAPSHOT_DATE),
        "evidence_tier": str(raw.get("evidence_tier") or "unclassified"),
        "domains": as_list(raw.get("domains")),
        "currentness": str(currentness),
        "project_implications": as_list(implications),
        "limitations": as_list(raw.get("limitations")),
        "rights_notes": str(rights),
        "superseded": bool(raw.get("superseded", False)),
        "review_due": str(raw.get("review_due") or "2027-02-10"),
    }


def main() -> None:
    records: list[dict[str, Any]] = []
    for path in INPUTS:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("sources"), list):
            raise ValueError(f"Invalid source fragment: {path}")
        records.extend(normalize(item) for item in payload["sources"])

    records.sort(key=lambda item: item["id"])
    ids = [item["id"] for item in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate stable source IDs")

    by_url: dict[str, list[str]] = defaultdict(list)
    for item in records:
        by_url[item["url"]].append(item["id"])
    for item in records:
        aliases = [source_id for source_id in by_url[item["url"]] if source_id != item["id"]]
        if aliases:
            item["same_source_as"] = aliases

    output = {
        "schema_version": "2.0",
        "snapshot_date": SNAPSHOT_DATE,
        "registry_status": "research_final",
        "source_record_count": len(records),
        "unique_source_count": len(by_url),
        "source_files": [path.relative_to(ROOT).as_posix() for path in INPUTS],
        "normalization_note": (
            "Stable workstream IDs are preserved. Evidence tiers are source-workstream classifications and are not a universal numeric truth score. "
            "Each source must be appraised for relevance, independence, population, method, currentness, limitations and rights in context."
        ),
        "sources": records,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        yaml.safe_dump(output, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"Wrote {len(records)} records / {len(by_url)} unique sources to {OUTPUT.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
