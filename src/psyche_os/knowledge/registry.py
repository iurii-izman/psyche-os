"""Knowledge layer — ontology and assessment registry metadata skeletons.

F0 is a skeleton: ontology entries exist but assessment state is
default blocked. No assessment item/scoring/content fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from psyche_os.domain.ids import generate_id

# ---------------------------------------------------------------------------
# Ontology registry entry skeleton
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class OntologyRegistryEntry:
    """A registered ontology with version and schema metadata."""

    entry_id: str = field(default_factory=lambda: generate_id())
    name: str = ""
    version: str = ""
    description: str = ""
    schema_uri: str = ""
    schema_hash: str = ""
    registered_at: str = ""
    registered_by: str = ""
    is_active: bool = True


# ---------------------------------------------------------------------------
# Assessment registry entry skeleton
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AssessmentRegistryEntry:
    """A registered assessment — BLOCKED in F0.

    No items, scoring, or content fields. Only metadata skeleton.
    """

    entry_id: str = field(default_factory=lambda: generate_id())
    name: str = ""
    version: str = ""
    description: str = ""
    blocked: bool = True  # Always blocked in F0
    blocked_reason: str = "Assessment state default-blocked in F0"
    registered_at: str = ""
    registered_by: str = ""


# ---------------------------------------------------------------------------
# Knowledge snapshot skeleton
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class KnowledgeSnapshot:
    """A point-in-time snapshot of registered knowledge."""

    snapshot_id: str = field(default_factory=lambda: generate_id())
    created_at: str = ""
    vault_id: str = ""
    ontology_count: int = 0
    assessment_count: int = 0
    summary: str = ""
    blocked: bool = True


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class OntologyRegistry:
    """In-memory ontology registry for F0."""

    def __init__(self) -> None:
        self._entries: dict[str, OntologyRegistryEntry] = {}

    def register(self, entry: OntologyRegistryEntry) -> None:
        self._entries[str(entry.entry_id)] = entry

    def get(self, entry_id: str) -> OntologyRegistryEntry | None:
        return self._entries.get(entry_id)

    def list_active(self) -> list[OntologyRegistryEntry]:
        return [e for e in self._entries.values() if e.is_active]

    def count(self) -> int:
        return len(self._entries)


class AssessmentRegistry:
    """In-memory assessment registry — blocked in F0."""

    def __init__(self) -> None:
        self._entries: dict[str, AssessmentRegistryEntry] = {}

    def register(self, entry: AssessmentRegistryEntry) -> None:
        self._entries[str(entry.entry_id)] = entry

    def get(self, entry_id: str) -> AssessmentRegistryEntry | None:
        return self._entries.get(entry_id)

    def list_all(self) -> list[AssessmentRegistryEntry]:
        return list(self._entries.values())

    def count(self) -> int:
        return len(self._entries)
