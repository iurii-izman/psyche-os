"""Read-only local retrieval over the existing Personal V11 reflection records.

The projection deliberately has no index, cache, provider, or write path.  It
keeps source turns, deterministic derived records, and AI proposals visibly
separate while exposing only stored provenance relationships.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
import re
from typing import Any, Protocol

from psyche_os.application.reflection_sessions import (
    MAX_SEARCH_QUERY,
    SEARCH_DEFAULT_LIMIT,
    SEARCH_MAX_LIMIT,
    ReflectionSessionError,
)

CONTENT_FILTERS = frozenset({"ALL", "SOURCE", "UNKNOWN", "CONTRADICTION", "FORMULATION"})
PERIOD_FILTERS = frozenset({"7D", "30D", "ALL"})
FORMULATION_FILTERS = frozenset({"ALL", "CURRENT", "PROPOSED", "REJECTED", "SUPERSEDED"})
REFLECTION_FILTERS = frozenset({"ALL", "ACTIVE", "CLOSED"})
MAX_RELATED = 6
_WHITESPACE = re.compile(r"\s+")


class _ReflectionStore(Protocol):
    @property
    def connection(self) -> Any: ...


def _normalise(value: str) -> str:
    return _WHITESPACE.sub(" ", value).strip().casefold()


def _tokens(value: str) -> tuple[str, ...]:
    return tuple(token for token in _normalise(value).split(" ") if token)


def _matches(value: str, query_tokens: tuple[str, ...]) -> bool:
    text = _normalise(value)
    return all(token in text for token in query_tokens)


def _date(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _within_period(value: str, period: str, now: datetime) -> bool:
    if period == "ALL":
        return True
    parsed = _date(value)
    if parsed is None:
        return False
    days = 7 if period == "7D" else 30
    return now - timedelta(days=days) <= parsed <= now


def _source_phrase(count: int) -> str:
    return "одной вашей записи" if count == 1 else f"{count} ваших записях"


class PersonalContextRetrievalService:
    """A bounded, deterministic V11 retrieval projection.

    All queries are SELECT-only.  IDs remain internal navigation anchors and
    are never intended for display by the renderer.
    """

    def __init__(self, reflection: _ReflectionStore) -> None:
        self._reflection = reflection
        self._db = reflection.connection

    @staticmethod
    def _validate(
        query: Any,
        state: Any,
        content: Any,
        period: Any,
        formulation_status: Any,
        limit: Any,
        offset: Any,
    ) -> tuple[str, tuple[str, ...]]:
        if not isinstance(query, str):
            raise ReflectionSessionError("INVALID_SEARCH")
        query = _normalise(query)
        if not query or len(query) > MAX_SEARCH_QUERY:
            raise ReflectionSessionError("INVALID_SEARCH")
        if (
            state not in REFLECTION_FILTERS
            or content not in CONTENT_FILTERS
            or period not in PERIOD_FILTERS
            or formulation_status not in FORMULATION_FILTERS
            or not isinstance(limit, int)
            or not isinstance(offset, int)
            or not 1 <= limit <= SEARCH_MAX_LIMIT
            or offset < 0
        ):
            raise ReflectionSessionError("INVALID_SEARCH")
        return query, _tokens(query)

    def search(
        self,
        query: Any,
        state: Any = "ALL",
        content: Any = "ALL",
        period: Any = "ALL",
        formulation_status: Any = "ALL",
        limit: Any = SEARCH_DEFAULT_LIMIT,
        offset: Any = 0,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        query, query_tokens = self._validate(
            query, state, content, period, formulation_status, limit, offset
        )
        current_time = now or datetime.now(UTC)
        sessions = {
            row[0]: {
                "session_id": row[0],
                "session_title": row[1],
                "session_state": row[2],
                "created_at": row[3],
                "updated_at": row[4],
            }
            for row in self._db.execute(
                "SELECT session_id,title,state,created_at,updated_at FROM reflection_sessions"
            )
        }
        turns_by_session: dict[str, list[dict[str, Any]]] = defaultdict(list)
        turns_by_id: dict[str, dict[str, Any]] = {}
        for row in self._db.execute(
            "SELECT turn_id,session_id,sequence,created_at,content FROM reflection_turns "
            "WHERE actor='USER' ORDER BY session_id,sequence,turn_id"
        ):
            item = dict(
                zip(
                    ("turn_id", "session_id", "sequence", "created_at", "content"), row, strict=True
                )
            )
            turns_by_session[item["session_id"]].append(item)
            turns_by_id[item["turn_id"]] = item

        context_sources: dict[str, list[str]] = defaultdict(list)
        for context_id, turn_id in self._db.execute(
            "SELECT context_item_id,turn_id FROM reflection_context_sources ORDER BY context_item_id,turn_id"
        ):
            context_sources[context_id].append(turn_id)

        snapshot_sources: dict[str, list[str]] = defaultdict(list)
        for snapshot_id, turn_id in self._db.execute(
            "SELECT DISTINCT snapshot.snapshot_id,source.turn_id "
            "FROM reflection_snapshot_context_items snapshot "
            "JOIN reflection_context_sources source ON source.context_item_id=snapshot.context_item_id "
            "JOIN reflection_turns turn ON turn.turn_id=source.turn_id "
            "WHERE snapshot.kind='KNOWN' ORDER BY snapshot.snapshot_id,turn.sequence,turn.turn_id"
        ):
            snapshot_sources[snapshot_id].append(turn_id)

        ai_sources: dict[str, list[str]] = defaultdict(list)
        ai_provenance: dict[str, dict[str, str]] = {}
        has_ai = bool(
            self._db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='reflection_ai_provenance'"
            ).fetchone()
        )
        if has_ai:
            for row in self._db.execute(
                "SELECT formulation_id,provider,actual_model FROM reflection_ai_provenance"
            ):
                ai_provenance[row[0]] = {"provider": row[1], "actual_model": row[2]}
            for formulation_id, turn_id in self._db.execute(
                "SELECT formulation_id,turn_id FROM reflection_ai_provenance_sources "
                "ORDER BY formulation_id,turn_id"
            ):
                ai_sources[formulation_id].append(turn_id)

        def sources(ids: list[str]) -> list[dict[str, Any]]:
            return [
                {
                    "turn_id": turn["turn_id"],
                    "sequence": turn["sequence"],
                    "created_at": turn["created_at"],
                    "content": turn["content"],
                }
                for turn_id in ids
                if (turn := turns_by_id.get(turn_id)) is not None
            ]

        results: list[dict[str, Any]] = []

        def allowed(session: dict[str, Any], at: str) -> bool:
            return (state == "ALL" or session["session_state"] == state) and _within_period(
                at, period, current_time
            )

        def append(
            result_id: str,
            result_type: str,
            session: dict[str, Any],
            text: str,
            at: str,
            source_turn_ids: list[str],
            *,
            status_value: str | None = None,
            provider: dict[str, str] | None = None,
            parent_id: str | None = None,
            sequence: int | None = None,
            searchable_text: str | None = None,
            correction_text: str | None = None,
        ) -> None:
            if not allowed(session, at) or not _matches(searchable_text or text, query_tokens):
                return
            source_rows = sources(source_turn_ids)
            if result_type == "UNKNOWN":
                why = f"Эта неясность основана на {_source_phrase(len(source_rows))}."
            elif result_type == "CONTRADICTION":
                why = f"Это противоречие связано с {_source_phrase(len(source_rows))}."  # noqa: RUF001 - intentional Russian owner-visible provenance
            elif result_type in {"FORMULATION", "AI_PROPOSAL"}:
                why = f"Формулировка опирается на {_source_phrase(len(source_rows))}."
            elif result_type == "USER_SOURCE":
                why = "Это точный текст вашей записи."
            else:
                why = "Это название размышления."
            results.append(
                {
                    "result_id": result_id,
                    "result_type": result_type,
                    "session_id": session["session_id"],
                    "session_title": session["session_title"],
                    "session_state": session["session_state"],
                    "at": at,
                    "text": text,
                    "excerpt": text[:400],
                    "turn_id": source_turn_ids[0]
                    if result_type == "USER_SOURCE" and source_turn_ids
                    else None,
                    "turn_sequence": sequence,
                    "status": status_value,
                    "source_turns": source_rows,
                    "why_here": why,
                    "parent_result_id": parent_id,
                    "ai_provenance": provider,
                    "correction_text": correction_text,
                }
            )

        if content in {"ALL", "SOURCE"}:
            for session in sessions.values():
                append(
                    f"reflection:{session['session_id']}",
                    "REFLECTION",
                    session,
                    session["session_title"],
                    session["updated_at"],
                    [],
                )
            for turn in turns_by_id.values():
                append(
                    f"turn:{turn['turn_id']}",
                    "USER_SOURCE",
                    sessions[turn["session_id"]],
                    turn["content"],
                    turn["created_at"],
                    [turn["turn_id"]],
                    sequence=turn["sequence"],
                )

        if content in {"ALL", "UNKNOWN", "CONTRADICTION"}:
            for row in self._db.execute(
                "SELECT context_item_id,session_id,kind,text,state,created_at FROM reflection_context_items "
                "WHERE kind IN ('UNKNOWN','CONTRADICTION')"
            ):
                context_id, session_id, kind, text, status_value, at = row
                if content != "ALL" and content != kind:
                    continue
                append(
                    f"context:{context_id}",
                    kind,
                    sessions[session_id],
                    text,
                    at,
                    context_sources[context_id],
                    status_value=status_value,
                )

        formulations: dict[str, dict[str, Any]] = {}
        if content in {"ALL", "FORMULATION"}:
            for row in self._db.execute(
                "SELECT formulation_id,session_id,version,parent_formulation_id,snapshot_id,status,summary,correction_text,created_at,updated_at "
                "FROM reflection_formulations"
            ):
                formulation = dict(
                    zip(
                        (
                            "formulation_id",
                            "session_id",
                            "version",
                            "parent_formulation_id",
                            "snapshot_id",
                            "status",
                            "summary",
                            "correction_text",
                            "created_at",
                            "updated_at",
                        ),
                        row,
                        strict=True,
                    )
                )
                formulations[formulation["formulation_id"]] = formulation
                if formulation_status != "ALL" and formulation["status"] != formulation_status:
                    continue
                source_ids = (
                    ai_sources[formulation["formulation_id"]]
                    or snapshot_sources[formulation["snapshot_id"]]
                )
                provenance = ai_provenance.get(formulation["formulation_id"])
                result_type = "AI_PROPOSAL" if provenance else "FORMULATION"
                append(
                    f"formulation:{formulation['formulation_id']}",
                    result_type,
                    sessions[formulation["session_id"]],
                    formulation["summary"],
                    formulation["updated_at"],
                    source_ids,
                    status_value=formulation["status"],
                    provider=provenance,
                    parent_id=(
                        f"formulation:{formulation['parent_formulation_id']}"
                        if formulation["parent_formulation_id"]
                        else None
                    ),
                    searchable_text="\n".join(
                        text
                        for text in (formulation["summary"], formulation["correction_text"])
                        if text
                    ),
                    correction_text=formulation["correction_text"],
                )

        for item in results:
            item["related_context"] = self._related(item, results, turns_by_session, formulations)
        results.sort(
            key=lambda item: (item["at"], item["session_title"], item["result_id"]), reverse=True
        )
        total = len(results)
        window = results[offset : offset + limit]
        return {
            "query": query,
            "state": state,
            "content": content,
            "period": period,
            "formulation_status": formulation_status,
            "total_matches": total,
            "returned_count": len(window),
            "offset": offset,
            "limit": limit,
            "truncated": offset + len(window) < total,
            "has_more": offset + len(window) < total,
            "results": window,
        }

    def _related(
        self,
        item: dict[str, Any],
        results: list[dict[str, Any]],
        turns_by_session: dict[str, list[dict[str, Any]]],
        formulations: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        related: list[dict[str, Any]] = []
        seen = {item["result_id"]}

        def add(candidate: dict[str, Any], label: str, why: str) -> None:
            if candidate["result_id"] in seen or len(related) >= MAX_RELATED:
                return
            seen.add(candidate["result_id"])
            related.append(
                {
                    "label": label,
                    "why_related": why,
                    "result_id": candidate["result_id"],
                    "result_type": candidate["result_type"],
                    "session_id": candidate["session_id"],
                    "session_title": candidate["session_title"],
                    "turn_id": candidate["turn_id"],
                    "turn_sequence": candidate["turn_sequence"],
                    "text": candidate["excerpt"],
                }
            )

        # Lineage is an explicit stored parent relationship, never inferred similarity.
        if item["result_type"] in {"FORMULATION", "AI_PROPOSAL"}:
            formulation_id = item["result_id"].split(":", 1)[1]
            formulation = formulations.get(formulation_id)
            if formulation:
                parent = formulation.get("parent_formulation_id")
                if parent:
                    candidate = next(
                        (row for row in results if row["result_id"] == f"formulation:{parent}"),
                        None,
                    )
                    if candidate is None and (parent_formulation := formulations.get(parent)):
                        candidate = {
                            "result_id": f"formulation:{parent}",
                            "result_type": "FORMULATION",
                            "session_id": item["session_id"],
                            "session_title": item["session_title"],
                            "turn_id": None,
                            "turn_sequence": None,
                            "excerpt": parent_formulation["summary"],
                        }
                    if candidate:
                        add(
                            candidate,
                            "Предыдущая версия",
                            "Это сохранённая предыдущая версия формулировки.",
                        )
                for child in formulations.values():
                    if child.get("parent_formulation_id") == formulation_id:
                        candidate = next(
                            (
                                row
                                for row in results
                                if row["result_id"] == f"formulation:{child['formulation_id']}"
                            ),
                            None,
                        )
                        if candidate is None:
                            candidate = {
                                "result_id": f"formulation:{child['formulation_id']}",
                                "result_type": "FORMULATION",
                                "session_id": item["session_id"],
                                "session_title": item["session_title"],
                                "turn_id": None,
                                "turn_sequence": None,
                                "excerpt": child["summary"],
                            }
                        add(
                            candidate,
                            "Следующая версия",
                            "Это следующая версия рабочей формулировки.",
                        )

        # Direct evidence edges: related derived records share stored turn IDs.
        item_sources = {source["turn_id"] for source in item["source_turns"]}
        for candidate in results:
            if item_sources and item_sources.intersection(
                source["turn_id"] for source in candidate["source_turns"]
            ):
                if candidate["result_type"] == "UNKNOWN":
                    add(
                        candidate, "Связанная неясность", "Основано на одной и той же вашей записи."
                    )
                elif candidate["result_type"] == "CONTRADICTION":
                    add(candidate, "Связанное противоречие", "Связано с той же вашей записью.")  # noqa: RUF001 - intentional Russian owner-visible relation
                else:
                    add(
                        candidate,
                        "Связано с этой записью",  # noqa: RUF001 - intentional Russian owner-visible relation
                        "Использует тот же сохранённый источник.",
                    )

        # Same-reflection turns are a compact, transparent local neighbourhood.
        for turn in turns_by_session.get(item["session_id"], []):
            candidate = next(
                (row for row in results if row["result_id"] == f"turn:{turn['turn_id']}"), None
            )
            if candidate is None:
                candidate = {
                    "result_id": f"turn:{turn['turn_id']}",
                    "result_type": "USER_SOURCE",
                    "session_id": item["session_id"],
                    "session_title": item["session_title"],
                    "turn_id": turn["turn_id"],
                    "turn_sequence": turn["sequence"],
                    "excerpt": turn["content"],
                }
            add(candidate, "Из того же размышления", "Это другая ваша запись в том же размышлении.")
        return related
