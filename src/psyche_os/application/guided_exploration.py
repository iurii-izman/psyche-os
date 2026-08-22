"""Deterministic, local V3-A1 Guided Exploration proposals only."""
# ruff: noqa: RUF001
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from psyche_os.application.reflection_sessions import (
    ReflectionSessionError,
    ReflectionSessionService,
    _text,
)
from psyche_os.domain.ids import generate_id

METHOD_VERSION = "guided-exploration-v1"
MAX_TEXT = 12_000
UNKNOWN_TEMPLATES = (
    ("time_course", "Пока неизвестно, когда это началось или как менялось со временем.", "Когда вы впервые заметили эту ситуацию или изменение?"),
    ("context", "Пока неизвестно, в каких ситуациях это заметнее или слабее.", "В каких ситуациях это заметнее, а в каких — слабее или не проявляется?"),
    ("impact", "Пока неизвестно, как это влияет на повседневность.", "Как это сейчас влияет на ваши обычные дела или самочувствие, если влияет?"),
    ("concurrent_changes", "Пока неизвестно, какие изменения происходили рядом по времени.", "Какие изменения в обстоятельствах происходили примерно в это же время, если были?"),
)
HYPOTHESES = (
    ("contextual", "Возможно, ситуация связана с конкретным контекстом или условиями; это рабочая альтернатива, не факт.", "Пока недостаточно данных о ситуациях и исключениях.", "Сравнение ситуаций, где это заметнее и слабее."),
    ("concurrent", "Возможно, одновременно происходящие изменения или нагрузка имеют значение; это рабочая альтернатива, не факт.", "Связь и направление влияния неизвестны.", "Описание того, что менялось рядом по времени."),
    ("mixed_unknown", "Возможно, влияет сочетание факторов или пока неописанный фактор; это рабочая альтернатива, не факт.", "Доступных ответов недостаточно для более узкого вывода.", "Новые примеры, исключения или уточнение контекста."),
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


class GuidedExplorationService:
    def __init__(self, sessions: ReflectionSessionService) -> None:
        self.sessions, self.db = sessions, sessions.connection

    def _session(self, session_id: Any, mutable: bool) -> str:
        sid = _text(session_id, 64)
        row = self.db.execute("SELECT state FROM reflection_sessions WHERE session_id=?", (sid,)).fetchone()
        if not row:
            raise ReflectionSessionError("SESSION_NOT_FOUND")
        if mutable and row[0] != "ACTIVE":
            raise ReflectionSessionError("SESSION_CLOSED")
        return sid

    def start(self, session_id: Any) -> dict[str, Any]:
        sid = self._session(session_id, True)
        turns = self.db.execute("SELECT turn_id,content FROM reflection_turns WHERE session_id=? ORDER BY sequence", (sid,)).fetchall()
        if not turns:
            raise ReflectionSessionError("EXPLORATION_REQUIRES_TURN")
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO reflection_explorations VALUES(?,NULL,?,?)", (sid, _now(), _now()))
            if not self.db.execute("SELECT 1 FROM reflection_context_items WHERE session_id=?", (sid,)).fetchone():
                known = generate_id()
                self.db.execute("INSERT INTO reflection_context_items VALUES(?,?,?,?,?,?,?)", (known, sid, "user_report", "KNOWN", turns[0][1], "RESOLVED", _now()))
                self.db.execute("INSERT INTO reflection_context_sources VALUES(?,?)", (known, turns[0][0]))
                for dimension, text, _question in UNKNOWN_TEMPLATES:
                    self.db.execute("INSERT INTO reflection_context_items VALUES(?,?,?,?,?,?,?)", (generate_id(), sid, dimension, "UNKNOWN", text, "OPEN", _now()))
                for template_id, proposal, uncertainty, discriminator in HYPOTHESES:
                    self.db.execute("INSERT INTO reflection_hypotheses VALUES(?,?,?,?,?,?,?)", (generate_id(), sid, template_id, proposal, uncertainty, discriminator, _now()))
            if not self._latest(sid):
                self._snapshot(sid)
            self._question(sid)
        return self.get(sid)

    def _latest(self, sid: str) -> Any:
        return self.db.execute("SELECT snapshot_id,version,method_version,created_at FROM reflection_exploration_snapshots WHERE session_id=? ORDER BY version DESC LIMIT 1", (sid,)).fetchone()

    def _snapshot(self, sid: str) -> str:
        version = self.db.execute("SELECT COALESCE(MAX(version),0)+1 FROM reflection_exploration_snapshots WHERE session_id=?", (sid,)).fetchone()[0]
        snapshot_id = generate_id()
        self.db.execute("INSERT INTO reflection_exploration_snapshots VALUES(?,?,?,?,?)", (snapshot_id, sid, version, METHOD_VERSION, _now()))
        self.db.execute("UPDATE reflection_explorations SET latest_snapshot_id=?,updated_at=? WHERE session_id=?", (snapshot_id, _now(), sid))
        return snapshot_id

    def _question(self, sid: str) -> None:
        if self.db.execute("SELECT 1 FROM reflection_questions WHERE session_id=? AND status='PROPOSED'", (sid,)).fetchone():
            return
        row = self.db.execute("SELECT dimension FROM reflection_context_items WHERE session_id=? AND kind='UNKNOWN' AND state='OPEN' ORDER BY created_at LIMIT 1", (sid,)).fetchone()
        if not row:
            return
        question = next(q for dim, _text_value, q in UNKNOWN_TEMPLATES if dim == row[0])
        self.db.execute("INSERT INTO reflection_questions VALUES(?,?,?,?,?,?,?,NULL)", (generate_id(), sid, self._latest(sid)[0], row[0], question, "PROPOSED", _now()))

    def answer(self, question_id: Any, answer_text: Any) -> dict[str, Any]:
        qid = _text(question_id, 64)
        row = self.db.execute("SELECT session_id,dimension,status FROM reflection_questions WHERE question_id=?", (qid,)).fetchone()
        if not row:
            raise ReflectionSessionError("QUESTION_NOT_FOUND")
        sid = self._session(row[0], True)
        if row[2] != "PROPOSED":
            raise ReflectionSessionError("QUESTION_NOT_AVAILABLE")
        turn = self.sessions.add_user_turn(sid, _text(answer_text, MAX_TEXT))
        with self.db:
            previous = self.db.execute("SELECT context_item_id,text FROM reflection_context_items WHERE session_id=? AND dimension=? AND kind='KNOWN' ORDER BY created_at", (sid, row[1])).fetchall()
            item = generate_id()
            self.db.execute("INSERT INTO reflection_context_items VALUES(?,?,?,?,?,?,?)", (item, sid, row[1], "KNOWN", turn["content"], "RESOLVED", _now()))
            self.db.execute("INSERT INTO reflection_context_sources VALUES(?,?)", (item, turn["turn_id"]))
            self.db.execute("UPDATE reflection_context_items SET state='RESOLVED' WHERE session_id=? AND dimension=? AND kind='UNKNOWN' AND state='OPEN'", (sid, row[1]))
            self.db.execute("UPDATE reflection_questions SET status='ANSWERED',answered_turn_id=? WHERE question_id=?", (turn["turn_id"], qid))
            if previous and previous[-1][1].strip().casefold() != turn["content"].strip().casefold():
                contradiction = generate_id()
                self.db.execute("INSERT INTO reflection_context_items VALUES(?,?,?,?,?,?,?)", (contradiction, sid, row[1], "CONTRADICTION", "Есть разные ответы по одному вопросу; различие остаётся неразрешённым.", "UNRESOLVED", _now()))
                for source_item in (previous[-1][0], item):
                    for (turn_id,) in self.db.execute("SELECT turn_id FROM reflection_context_sources WHERE context_item_id=?", (source_item,)):
                        self.db.execute("INSERT OR IGNORE INTO reflection_context_sources VALUES(?,?)", (contradiction, turn_id))
            self._snapshot(sid)
            self._question(sid)
        return self.get(sid)

    def skip(self, question_id: Any) -> dict[str, Any]:
        qid = _text(question_id, 64)
        row = self.db.execute("SELECT session_id,dimension,status FROM reflection_questions WHERE question_id=?", (qid,)).fetchone()
        if not row:
            raise ReflectionSessionError("QUESTION_NOT_FOUND")
        sid = self._session(row[0], True)
        if row[2] != "PROPOSED":
            raise ReflectionSessionError("QUESTION_NOT_AVAILABLE")
        with self.db:
            self.db.execute("UPDATE reflection_questions SET status='SKIPPED' WHERE question_id=?", (qid,))
            self.db.execute("UPDATE reflection_context_items SET state='SKIPPED' WHERE session_id=? AND dimension=? AND kind='UNKNOWN' AND state='OPEN'", (sid, row[1]))
            self._snapshot(sid)
            self._question(sid)
        return self.get(sid)

    def propose_formulation(self, session_id: Any) -> dict[str, Any]:
        sid = self._session(session_id, True)
        snapshot = self._latest(sid)
        if not snapshot:
            raise ReflectionSessionError("EXPLORATION_REQUIRES_TURN")
        version = self.db.execute("SELECT COALESCE(MAX(version),0)+1 FROM reflection_formulations WHERE session_id=?", (sid,)).fetchone()[0]
        reports = self.db.execute("SELECT text FROM reflection_context_items WHERE session_id=? AND kind='KNOWN' ORDER BY created_at LIMIT 2", (sid,)).fetchall()
        result = {"formulation_id": generate_id(), "session_id": sid, "version": version, "parent_formulation_id": None, "snapshot_id": snapshot[0], "status": "PROPOSED", "summary": "Рабочее предложение, не диагноз и не установленный факт. " + " ".join(x[0] for x in reports) + " Неизвестное и альтернативные объяснения остаются открытыми.", "correction_text": None, "method_version": METHOD_VERSION, "created_at": _now(), "updated_at": _now()}
        with self.db:
            self.db.execute("INSERT INTO reflection_formulations VALUES(:formulation_id,:session_id,:version,:parent_formulation_id,:snapshot_id,:status,:summary,:correction_text,:method_version,:created_at,:updated_at)", result)
        return result

    def _formulation(self, formulation_id: Any, mutable: bool) -> dict[str, Any]:
        fid = _text(formulation_id, 64)
        columns = "formulation_id,session_id,version,parent_formulation_id,snapshot_id,status,summary,correction_text,method_version,created_at,updated_at"
        row = self.db.execute(f"SELECT {columns} FROM reflection_formulations WHERE formulation_id=?", (fid,)).fetchone()
        if not row:
            raise ReflectionSessionError("FORMULATION_NOT_FOUND")
        result = dict(zip(columns.split(","), row, strict=True))
        self._session(result["session_id"], mutable)
        return result

    def correct_formulation(self, formulation_id: Any, correction_text: Any) -> dict[str, Any]:
        parent = self._formulation(formulation_id, True)
        correction = _text(correction_text, MAX_TEXT)
        version = self.db.execute("SELECT COALESCE(MAX(version),0)+1 FROM reflection_formulations WHERE session_id=?", (parent["session_id"],)).fetchone()[0]
        result = {**parent, "formulation_id": generate_id(), "version": version, "parent_formulation_id": parent["formulation_id"], "status": "PROPOSED", "summary": parent["summary"] + "\n\nУточнение пользователя: " + correction, "correction_text": correction, "created_at": _now(), "updated_at": _now()}
        with self.db:
            self.db.execute("INSERT INTO reflection_formulations VALUES(:formulation_id,:session_id,:version,:parent_formulation_id,:snapshot_id,:status,:summary,:correction_text,:method_version,:created_at,:updated_at)", result)
        return result

    def set_formulation_status(self, formulation_id: Any, status: str) -> dict[str, Any]:
        result = self._formulation(formulation_id, True)
        if result["status"] != "PROPOSED":
            raise ReflectionSessionError("FORMULATION_NOT_PROPOSED")
        with self.db:
            if status == "ACCEPTED":
                self.db.execute("UPDATE reflection_formulations SET status='SUPERSEDED',updated_at=? WHERE session_id=? AND status='ACCEPTED'", (_now(), result["session_id"]))
            self.db.execute("UPDATE reflection_formulations SET status=?,updated_at=? WHERE formulation_id=?", (status, _now(), result["formulation_id"]))
        result["status"] = status
        return result

    def get(self, session_id: Any) -> dict[str, Any]:
        sid = self._session(session_id, False)
        context = []
        for row in self.db.execute("SELECT context_item_id,dimension,kind,text,state,created_at FROM reflection_context_items WHERE session_id=? ORDER BY created_at", (sid,)):
            item = dict(zip(("context_item_id","dimension","kind","text","state","created_at"), row, strict=True))
            item["source_turn_ids"] = [value[0] for value in self.db.execute("SELECT turn_id FROM reflection_context_sources WHERE context_item_id=?", (row[0],))]
            context.append(item)
        hypotheses = [dict(zip(("hypothesis_id","template_id","proposal_text","uncertainty_text","discriminator_text","created_at"), row, strict=True)) for row in self.db.execute("SELECT hypothesis_id,template_id,proposal_text,uncertainty_text,discriminator_text,created_at FROM reflection_hypotheses WHERE session_id=?", (sid,))]
        question = self.db.execute("SELECT question_id,dimension,text,status,snapshot_id FROM reflection_questions WHERE session_id=? AND status='PROPOSED' ORDER BY created_at LIMIT 1", (sid,)).fetchone()
        snapshots = [dict(zip(("snapshot_id","version","method_version","created_at"), row, strict=True)) for row in self.db.execute("SELECT snapshot_id,version,method_version,created_at FROM reflection_exploration_snapshots WHERE session_id=? ORDER BY version DESC", (sid,))]
        formulations = [dict(zip(("formulation_id","version","parent_formulation_id","snapshot_id","status","summary","correction_text","method_version","created_at","updated_at"), row, strict=True)) for row in self.db.execute("SELECT formulation_id,version,parent_formulation_id,snapshot_id,status,summary,correction_text,method_version,created_at,updated_at FROM reflection_formulations WHERE session_id=? ORDER BY version DESC", (sid,))]
        return {"context": context, "hypotheses": hypotheses, "next_question": dict(zip(("question_id","dimension","text","status","snapshot_id"), question, strict=True)) if question else None, "snapshots": snapshots, "formulations": formulations}
