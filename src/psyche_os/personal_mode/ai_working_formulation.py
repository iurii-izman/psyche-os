"""Bounded, opt-in OpenAI working-formulation vertical for Personal Mode.

This is deliberately not a generic AI facility.  It permits one selected
reflection's USER turns to leave the device only after a renderer-visible
preview has been confirmed by a short-lived, one-use authorization.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
import secrets
from typing import Any, Callable

from psyche_os.crypto.envelope import OSKeyWrapper, OSKeyWrapError
from psyche_os.domain.ids import generate_id
from psyche_os.application.guided_exploration import GuidedExplorationService

MAX_TURNS = 8
MAX_CHARS = 20_000
AUTHORIZATION_LIFETIME = timedelta(minutes=5)
OPENAI_ENDPOINT = "https://api.openai.com/v1/responses"
MODEL = "gpt-5.6-luna"
CONFIG_ID = "personal-working-formulation-v1-low-500"


class PersonalAIError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


class OpenAIKeyStore:
    """Fixed DPAPI-only secret store with no read-back operation."""

    def __init__(self, root: Path, wrapper_factory: Callable[[], OSKeyWrapper] = OSKeyWrapper) -> None:
        self._path = root / "secrets" / "openai.dpapi"
        self._wrapper_factory = wrapper_factory

    def configured(self) -> bool:
        return self._path.is_file() and self._path.stat().st_size > 0

    def configure(self, key: str) -> None:
        if not isinstance(key, str) or not key.startswith("sk-") or len(key) > 512:
            raise PersonalAIError("AI_KEY_REJECTED")
        try:
            protected = self._wrapper_factory().protect(key.encode("utf-8"), "PSYCHE OS OpenAI working formulation")
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_bytes(protected)
        except (OSError, OSKeyWrapError) as exc:
            raise PersonalAIError("AI_KEY_STORAGE_FAILED") from exc

    def delete(self) -> None:
        try:
            if self._path.exists():
                self._path.unlink()
        except OSError as exc:
            raise PersonalAIError("AI_KEY_STORAGE_FAILED") from exc

    def _consume_for_request(self) -> str:
        """Trusted-only internal use immediately before the HTTPS invocation."""
        try:
            value = self._wrapper_factory().unprotect(self._path.read_bytes()).decode("utf-8")
        except (OSError, UnicodeDecodeError, OSKeyWrapError) as exc:
            raise PersonalAIError("AI_KEY_UNAVAILABLE") from exc
        if not value.startswith("sk-") or len(value) > 512:
            raise PersonalAIError("AI_KEY_UNAVAILABLE")
        return value


@dataclass(frozen=True, slots=True)
class PreparedPreview:
    interaction_id: str
    preview_id: str
    session_id: str
    turns: tuple[dict[str, Any], ...]
    manifest: dict[str, Any]


class PersonalWorkingFormulationService:
    """Owns preview, authorization, revalidation, local validation and persistence."""

    def __init__(self, reflection: Any, key_store: OpenAIKeyStore, provider: Any) -> None:
        self._reflection, self._keys, self._provider = reflection, key_store, provider
        self._pending: dict[str, PreparedPreview] = {}
        self._authorizations: dict[str, tuple[PreparedPreview, datetime]] = {}
        self._consumed: set[str] = set()

    def status(self) -> dict[str, Any]:
        return {"provider": "OpenAI", "configured": self._keys.configured(), "model": MODEL, "config_id": CONFIG_ID}

    def prepare(self, session_id: Any, selected_turn_ids: Any) -> dict[str, Any]:
        if not isinstance(session_id, str) or not isinstance(selected_turn_ids, list) or not selected_turn_ids:
            raise PersonalAIError("INVALID_AI_PREVIEW")
        if len(selected_turn_ids) > MAX_TURNS or len(selected_turn_ids) != len(set(selected_turn_ids)) or not all(isinstance(v, str) for v in selected_turn_ids):
            raise PersonalAIError("AI_CONTEXT_SELECTION_REQUIRED")
        session = self._reflection.get_session(session_id)
        turns = [turn for turn in session["turns"] if turn["turn_id"] in set(selected_turn_ids)]
        if len(turns) != len(selected_turn_ids) or any(turn["actor"] != "USER" for turn in turns):
            raise PersonalAIError("AI_CONTEXT_SELECTION_REQUIRED")
        turns.sort(key=lambda turn: turn["sequence"])
        if sum(len(turn["content"]) for turn in turns) > MAX_CHARS:
            raise PersonalAIError("AI_CONTEXT_SELECTION_REQUIRED")
        material = [{"turn_id": turn["turn_id"], "digest": _digest(turn["content"]), "sequence": turn["sequence"]} for turn in turns]
        interaction_id = generate_id()
        manifest = {"schema_version": "personal-ai-disclosure-manifest-v1", "interaction_id": interaction_id, "session_id": session_id, "selected_turn_ids": [item["turn_id"] for item in material], "content_digests": material, "provider": "openai", "model": MODEL, "config_id": CONFIG_ID, "purpose": "working_formulation", "max_turns": MAX_TURNS, "max_chars": MAX_CHARS, "expires_at": (datetime.now(UTC) + AUTHORIZATION_LIFETIME).isoformat()}
        preview = PreparedPreview(interaction_id, _digest(manifest), session_id, tuple(turns), manifest)
        self._pending[interaction_id] = preview
        return {"interaction_id": interaction_id, "preview_id": preview.preview_id, "provider": "OpenAI", "purpose": "рабочая формулировка", "turns": [{"turn_id": t["turn_id"], "sequence": t["sequence"], "content": t["content"]} for t in turns], "one_time": True, "ai_is_proposal": True, "expires_at": manifest["expires_at"]}

    def authorize_execute(self, interaction_id: Any, preview_id: Any) -> dict[str, Any]:
        if not isinstance(interaction_id, str) or not isinstance(preview_id, str):
            raise PersonalAIError("INVALID_AI_AUTHORIZATION")
        prepared = self._pending.pop(interaction_id, None)
        if prepared is None or not secrets.compare_digest(prepared.preview_id, preview_id):
            raise PersonalAIError("AI_AUTHORIZATION_INVALID")
        expires = datetime.fromisoformat(prepared.manifest["expires_at"])
        authorization_id = generate_id()
        self._authorizations[authorization_id] = (prepared, expires)
        return self._execute(authorization_id)

    def _execute(self, authorization_id: str) -> dict[str, Any]:
        if authorization_id in self._consumed:
            raise PersonalAIError("AI_AUTHORIZATION_CONSUMED")
        issued = self._authorizations.pop(authorization_id, None)
        self._consumed.add(authorization_id)
        if issued is None or datetime.now(UTC) > issued[1]:
            raise PersonalAIError("AI_AUTHORIZATION_EXPIRED")
        prepared = issued[0]
        # Re-read selected rows so deleted/changed source cannot be disclosed.
        session = self._reflection.get_session(prepared.session_id)
        selected_ids = [turn["turn_id"] for turn in prepared.turns]
        turns = [turn for turn in session["turns"] if turn["turn_id"] in set(selected_ids)]
        turns.sort(key=lambda turn: turn["sequence"])
        expected = [(turn["turn_id"], turn["sequence"], _digest(turn["content"])) for turn in prepared.turns]
        actual = [(turn["turn_id"], turn["sequence"], _digest(turn["content"])) for turn in turns]
        if expected != actual:
            raise PersonalAIError("AI_CONTEXT_STALE")
        key = self._keys._consume_for_request()
        try:
            raw, actual_model = self._provider.invoke_working_formulation(prepared.manifest, prepared.turns, key)
        finally:
            key = ""
        if actual_model != MODEL:
            raise PersonalAIError("AI_MODEL_MISMATCH")
        proposal = validate_working_formulation(raw, {turn["turn_id"] for turn in prepared.turns})
        provenance = {"origin": "AI", "authority": "proposal_only", "is_evidence": False, "provider": "openai", "requested_model": MODEL, "actual_model": actual_model, "config_digest": _digest({"model": MODEL, "config": CONFIG_ID}), "manifest_id": prepared.preview_id, "disclosure_receipt_id": _digest({"authorization_id": authorization_id, "preview": prepared.preview_id}), "created_at": datetime.now(UTC).isoformat()}
        return {"proposal": proposal, "provenance": provenance, "formulation": self._persist(prepared.session_id, proposal, provenance)}

    def _persist(self, session_id: str, proposal: dict[str, Any], provenance: dict[str, Any]) -> dict[str, Any]:
        exploration = GuidedExplorationService(self._reflection)
        exploration.start(session_id)
        db = self._reflection.connection
        snapshot = db.execute("SELECT latest_snapshot_id FROM reflection_explorations WHERE session_id=?", (session_id,)).fetchone()
        version = db.execute("SELECT COALESCE(MAX(version),0)+1 FROM reflection_formulations WHERE session_id=?", (session_id,)).fetchone()[0]
        if snapshot is None or not snapshot[0]:
            raise PersonalAIError("AI_PERSISTENCE_FAILED")
        formulation_id, created_at = generate_id(), provenance["created_at"]
        value = proposal["formulation"]
        summary = f"AI-derived proposal, not fact. {value['text']}\n\nUncertainty: {value['uncertainty']}"
        try:
            with db:
                db.execute("INSERT INTO reflection_formulations VALUES(?,?,?,?,?,?,?,?,?,?,?)", (formulation_id, session_id, version, None, snapshot[0], "PROPOSED", summary, None, "personal-ai-working-formulation-v1", created_at, created_at))
                db.execute("INSERT INTO reflection_ai_provenance VALUES(?,?,?,?,?,?,?,?,?,?)", (formulation_id, "AI", "openai", provenance["requested_model"], provenance["actual_model"], provenance["config_digest"], CONFIG_ID, provenance["manifest_id"], provenance["disclosure_receipt_id"], created_at))
                for turn_id in value["supporting_turn_ids"]:
                    db.execute("INSERT INTO reflection_ai_provenance_sources VALUES(?,?)", (formulation_id, turn_id))
        except Exception as exc:
            raise PersonalAIError("AI_PERSISTENCE_FAILED") from exc
        return {"formulation_id": formulation_id, "session_id": session_id, "version": version, "status": "PROPOSED", "summary": summary, "origin": "AI", "authority": "proposal_only", "is_evidence": False, "supporting_turn_ids": value["supporting_turn_ids"], "uncertainty": value["uncertainty"]}


def validate_working_formulation(raw: Any, disclosed_turn_ids: set[str]) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != {"schema_version", "proposal_id", "status", "formulation"}:
        raise PersonalAIError("AI_OUTPUT_REJECTED")
    formulation = raw.get("formulation")
    if raw.get("schema_version") != "personal-working-formulation-v1" or raw.get("status") != "PROPOSED" or not isinstance(raw.get("proposal_id"), str) or not isinstance(formulation, dict) or set(formulation) != {"text", "supporting_turn_ids", "uncertainty"}:
        raise PersonalAIError("AI_OUTPUT_REJECTED")
    text, sources, uncertainty = formulation["text"], formulation["supporting_turn_ids"], formulation["uncertainty"]
    if not isinstance(text, str) or not text.strip() or len(text) > 2400 or not isinstance(uncertainty, str) or not uncertainty.strip() or len(uncertainty) > 480 or not isinstance(sources, list) or not sources or len(sources) > MAX_TURNS or len(sources) != len(set(sources)) or not all(isinstance(item, str) and item in disclosed_turn_ids for item in sources):
        raise PersonalAIError("AI_OUTPUT_REJECTED")
    prohibited = ("у вас диагноз", "диагноз:", "диагностировано", "назначаю", "принимайте лекар", "дозировк", "это психоз", "это бред", "это паранойя", "у вас параной", "скрытые мотивы", "это доказывает вытеснен", "ты должен", "вам следует", "you have a diagnosis", "diagnosis:", "take medication", "you should", "hidden motive", "repressed memory")
    joined = f"{text} {uncertainty}".casefold()
    if any(term in joined for term in prohibited):
        raise PersonalAIError("AI_OUTPUT_UNSAFE")
    return {"schema_version": raw["schema_version"], "proposal_id": raw["proposal_id"], "status": "PROPOSED", "formulation": {"text": text.strip(), "supporting_turn_ids": sources, "uncertainty": uncertainty.strip()}}
