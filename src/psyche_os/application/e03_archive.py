"""Closed E03 Orchid Station canonical archive application service.

Only operation IDs and choices from the package-owned fixture are accepted.
All persisted content and stable identifiers below are repository-owned,
fictional constants.  No arbitrary renderer text, paths, dates, IDs, table
names, record bodies, or fixture paths cross this boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import secrets
from typing import Any, Final

from psyche_os.storage.migrations import Migrator


PACK_ID: Final = "e03_orchid_station_v1"
OPERATIONS: Final = frozenset({
    "CAPTURE_LAMP_REPORT", "CAPTURE_LAMP_OBSERVATION", "CAPTURE_COUNTERREPORT",
    "ASSEMBLE_EPISTEMIC_SET", "CREATE_BASELINE_SNAPSHOT", "CREATE_REVISED_SNAPSHOT",
    "CORRECT_LAMP_REPORT_TIME", "DELETE_LAMP_SOURCE",
})
CHOICES: Final = {
    "CAPTURE_LAMP_REPORT": {"reported_exact", "occurred_summer_2042"},
    "CAPTURE_LAMP_OBSERVATION": {"observed_interval"},
    "CAPTURE_COUNTERREPORT": {"reported_exact", "occurred_unknown"},
    "ASSEMBLE_EPISTEMIC_SET": {"descriptive_proposed", "pattern_contested", "descriptive_user_accepted"},
    "CREATE_BASELINE_SNAPSHOT": {"baseline"},
    "CREATE_REVISED_SNAPSHOT": {"revised"},
    "CORRECT_LAMP_REPORT_TIME": {"corrected_reported_exact"},
    "DELETE_LAMP_SOURCE": {"dry_run", "confirm"},
}
IDEMPOTENCY_RE: Final = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
NOW: Final = "2042-09-02T10:00:00+00:00"


class E03ArchiveError(Exception):
    """Stable, content-free E03 boundary failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _load_pack() -> str:
    path = Path(__file__).resolve().parents[1] / "fixtures" / "e03_orchid_station_v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if set(payload) != {"fixture_pack_id", "manifest_version", "schema_version", "synthetic_fixture", "scenario", "operations", "digest"}:
        raise E03ArchiveError("FIXTURE_AUTHORITY_INVALID")
    supplied = payload.pop("digest")
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if supplied != digest or payload.get("fixture_pack_id") != PACK_ID or set(payload.get("operations", [])) != OPERATIONS:
        raise E03ArchiveError("FIXTURE_AUTHORITY_INVALID")
    return digest


def _row(connection: Any, sql: str, args: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    cursor = connection.execute(sql, args)
    item = cursor.fetchone()
    if item is None:
        return None
    columns = [column[0] for column in cursor.description]
    return dict(zip(columns, item))


def _rows(connection: Any, sql: str, args: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    cursor = connection.execute(sql, args)
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, item)) for item in cursor.fetchall()]


@dataclass(slots=True)
class DeletionPreview:
    plan_id: str
    counts: dict[str, int]
    selectors: dict[str, tuple[str, tuple[str, ...]]]


class E03ArchiveService:
    """Canonical V2 service for the one closed fictional E03 scenario."""

    def __init__(self, connection: Any) -> None:
        self.connection = connection
        # V1 is applied first and the frozen migration rebuilds its five
        # semantic tables before V2 writes.  Enable direct V2 ownership FKs
        # after that atomic rebuild completes.
        self.connection.execute("PRAGMA foreign_keys=OFF")
        report = Migrator(connection).apply(2)
        if report.errors:
            raise E03ArchiveError("MIGRATION_FAILED")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self._authority_digest = _load_pack()
        self._results: dict[tuple[str, str], dict[str, Any]] = {}
        self._plans: dict[str, DeletionPreview] = {}
        self._bootstrap()

    def _bootstrap(self) -> None:
        with self.connection:
            if not _row(self.connection, "SELECT vault_id FROM vault_config LIMIT 1"):
                self.connection.execute(
                    "INSERT INTO vault_config(vault_id,vault_name,data_mode,created_at,db_key_salt,blob_envelope_key_salt) VALUES(?,?,?,?,?,?)",
                    ("e03-vault", "Orchid Station fictional archive", "synthetic_only", NOW, b"0" * 32, b"1" * 32),
                )
            for record_id, actor_id, label in (
                ("actor-owner-record", "actor-owner", "Fictional station keeper"),
                ("actor-counter-record", "actor-counter", "Fictional maintenance log author"),
                ("actor-system-record", "actor-system", "Deterministic fixture assembler"),
            ):
                self.connection.execute(
                    "INSERT OR IGNORE INTO actors(record_id,actor_id,actor_kind,actor_label,tx_from,is_active,created_at,version_id) VALUES(?,?,?,?,?,1,?,?)",
                    (record_id, actor_id, "system" if actor_id == "actor-system" else "human", label, NOW, NOW, record_id + "-v1"),
                )
            self.connection.execute(
                "INSERT OR IGNORE INTO derivation_runs(derivation_id,method_kind,code_rule_model_tool,code_rule_model_version,parameters_config_digest,environment_profile,actor_id,purpose,validation_outcomes,review_state) VALUES(?,?,?,?,?,?,?,?,?,?)",
                ("derivation-orchid-snapshot", "deterministic_rule", "orchid_fixture_snapshot", "1.0.0", self._authority_digest, "offline", "actor-system", "synthetic_snapshot", "fixture_validated", "not_reviewed"),
            )

    def operate(self, operation: str, choice: str, idempotency_key: str) -> dict[str, Any]:
        if operation not in OPERATIONS or choice not in CHOICES.get(operation, set()):
            raise E03ArchiveError("INVALID_OPERATION_CHOICE")
        if not isinstance(idempotency_key, str) or not IDEMPOTENCY_RE.fullmatch(idempotency_key):
            raise E03ArchiveError("INVALID_IDEMPOTENCY_KEY")
        key = (operation, idempotency_key)
        if key in self._results:
            return {**self._results[key], "idempotent_replay": True}
        handlers = {
            "CAPTURE_LAMP_REPORT": self._capture_report,
            "CAPTURE_LAMP_OBSERVATION": self._capture_observation,
            "CAPTURE_COUNTERREPORT": self._capture_counterreport,
            "ASSEMBLE_EPISTEMIC_SET": self._assemble_epistemic,
            "CREATE_BASELINE_SNAPSHOT": self._baseline_snapshot,
            "CREATE_REVISED_SNAPSHOT": self._revised_snapshot,
            "CORRECT_LAMP_REPORT_TIME": self._correct_report_time,
            "DELETE_LAMP_SOURCE": self._delete_source,
        }
        result = handlers[operation](choice)
        result = {**result, "operation": operation, "fixture_pack": PACK_ID, "idempotent_replay": False}
        self._results[key] = result
        return result

    def _insert_versioned(self, table: str, values: dict[str, Any]) -> None:
        columns = list(values)
        self.connection.execute(
            f"INSERT OR IGNORE INTO {table}({','.join(columns)}) VALUES({','.join('?' for _ in columns)})",
            tuple(values[column] for column in columns),
        )

    def _capture_report(self, choice: str) -> dict[str, Any]:
        with self.connection:
            self._insert_versioned("source_artifacts", {
                "record_id":"source-lamp","artifact_id":"source-lamp","version_id":"source-lamp-v1","source_kind":"fixture_report",
                "source_label":"Orchid Station lamp report","uri_or_path":"","mime_type":"text/plain","source_metadata":"{}",
                "tx_from":NOW,"is_active":1,"created_at":NOW,"semantic_version":2,"schema_version":2,"change_reason_code":"initial",
                "created_by_actor_id":"actor-owner","artifact_kind":"user_note","origin_kind":"user_created","captured_at":NOW,
                "source_actor_id":"actor-owner","language_tags":"[\"en\"]","declared_mime_type":"text/plain","observed_mime_type":"text/plain",
                "byte_size":58,"parser_state":"raw","quarantine_state":"none","rights_note":"Repository-owned fictional fixture"
            })
            self._insert_versioned("source_locators", {"record_id":"locator-lamp","version_id":"locator-lamp-v1","schema_version":2,"tx_from":NOW,"is_active":1,"change_reason_code":"initial","created_by_actor_id":"actor-owner","artifact_record_id":"source-lamp","artifact_version_id":"source-lamp-v1","locator_type":"document_section","locator_value":"fixture:lamp-report","extractor_name":"fixture","extractor_version":"1.0.0"})
            self._insert_versioned("reports", {"record_id":"report-lamp","report_id":"report-lamp","version_id":"report-lamp-v1","title":"Indicator lamp account","summary":"","structured_data":"{}","tx_from":NOW,"is_active":1,"created_at":NOW,"semantic_version":2,"schema_version":2,"change_reason_code":"initial","created_by_actor_id":"actor-owner","report_kind":"event_account","verbatim_content":"The fictional east-bench indicator lamp appeared amber.","reporter_actor_id":"actor-owner","perspective":"first_person","language_tag":"en","elicitation_method":"fixture_capture","source_locator_record_id":"locator-lamp","source_locator_version_id":"locator-lamp-v1"})
            self._insert_versioned("assertions", {"record_id":"assertion-lamp","assertion_id":"assertion-lamp","version_id":"assertion-lamp-v1","assertion_type":"source_near","predicate":"indicator_appearance","support_ids":"[]","contra_ids":"[]","tx_from":NOW,"is_active":1,"created_at":NOW,"provenance_ref":"locator-lamp-v1","semantic_version":2,"schema_version":2,"change_reason_code":"initial","created_by_actor_id":"actor-owner","object_value":"amber","qualifiers":"[\"fictional_station\"]","negation":0,"modality":"reported","scope":"east_bench_indicator","source_locator_record_id":"locator-lamp","source_locator_version_id":"locator-lamp-v1"})
            if choice == "reported_exact":
                temporal = ("reported","instant","2042-09-01T08:30:00+00:00","2042-09-01T08:30:00+00:00","minute","2042-09-01 08:30 UTC",1,"UTC")
            else:
                temporal = ("occurred","calendar_period","2042-06-01","2042-08-31","season","summer 2042",0,None)
            self._insert_temporal("time-report-lamp", "time-report-lamp-v1", "report-lamp", "report-lamp-v1", temporal)
        return {"created_types":["source_artifact","source_locator","report","assertion","temporal_assertion"],"source_near":True,"derived":False}

    def _insert_temporal(self, rid: str, vid: str, target: str, target_version: str, values: tuple[Any,...]) -> None:
        role, kind, lower, upper, precision, literal, tz_known, tz_name = values
        self._insert_versioned("temporal_assertions", {"record_id":rid,"version_id":vid,"schema_version":2,"tx_from":NOW,"is_active":1,"change_reason_code":"initial","created_by_actor_id":"actor-system","target_record_id":target,"target_version_id":target_version,"temporal_role":role,"value_kind":kind,"lower_value":lower,"upper_value":upper,"lower_inclusive":1 if lower else 0,"upper_inclusive":1 if upper else 0,"precision":precision,"original_literal":literal,"timezone_known":tz_known,"timezone_name":tz_name,"calendar":"gregorian","certainty_class":"moderate","certainty_rationale":"Frozen fictional fixture preset"})

    def _capture_observation(self, _choice: str) -> dict[str, Any]:
        with self.connection:
            self._insert_versioned("observations", {"record_id":"observation-lamp","observation_id":"observation-lamp","version_id":"observation-lamp-v1","method":"visual_fixture","raw_value":"amber","structured_data":"{}","tx_from":NOW,"is_active":1,"created_at":NOW,"semantic_version":2,"schema_version":2,"change_reason_code":"initial","created_by_actor_id":"actor-owner","observation_kind":"self_observation","observer_actor_id":"actor-owner","construct_phenomenon":"indicator_appearance","value_or_coded_state":"amber","context":"fictional east bench","quality_flags":"[\"unverified_indicator\"]","source_locator_record_id":"locator-lamp","source_locator_version_id":"locator-lamp-v1"})
            self._insert_temporal("time-observation-lamp","time-observation-lamp-v1","observation-lamp","observation-lamp-v1",("observed","closed_interval","2042-09-01T08:28:00+00:00","2042-09-01T08:32:00+00:00","minute","08:28–08:32 UTC",1,"UTC"))
        return {"created_types":["observation","temporal_assertion"],"clock":"observed"}

    def _capture_counterreport(self, choice: str) -> dict[str, Any]:
        with self.connection:
            self._insert_versioned("reports", {"record_id":"report-counter","report_id":"report-counter","version_id":"report-counter-v1","title":"Maintenance counterreport","summary":"","structured_data":"{}","tx_from":NOW,"is_active":1,"created_at":NOW,"semantic_version":2,"schema_version":2,"change_reason_code":"initial","created_by_actor_id":"actor-counter","report_kind":"event_account","verbatim_content":"The fictional maintenance log records a green indicator.","reporter_actor_id":"actor-counter","perspective":"document_author","language_tag":"en","elicitation_method":"fixture_capture"})
            self._insert_versioned("assertions", {"record_id":"assertion-counter","assertion_id":"assertion-counter","version_id":"assertion-counter-v1","assertion_type":"source_near","predicate":"indicator_appearance","support_ids":"[]","contra_ids":"[]","tx_from":NOW,"is_active":1,"created_at":NOW,"provenance_ref":"source_unavailable","semantic_version":2,"schema_version":2,"change_reason_code":"initial","created_by_actor_id":"actor-counter","object_value":"green","qualifiers":"[\"fictional_station\"]","negation":0,"modality":"reported","scope":"east_bench_indicator","source_unavailable_reason":"fixture counterreport has no separate artifact"})
            temporal = ("reported","instant","2042-09-01T09:00:00+00:00","2042-09-01T09:00:00+00:00","minute","2042-09-01 09:00 UTC",1,"UTC") if choice == "reported_exact" else ("occurred","unknown",None,None,"unknown","unknown",0,None)
            self._insert_temporal("time-report-counter","time-report-counter-v1","report-counter","report-counter-v1",temporal)
        return {"created_types":["report","assertion","temporal_assertion"],"clock":temporal[0]}

    def _assemble_epistemic(self, choice: str) -> dict[str, Any]:
        mapping={"descriptive_proposed":("descriptive","proposed"),"pattern_contested":("pattern","contested"),"descriptive_user_accepted":("descriptive","user_accepted")}
        claim_type,status=mapping[choice]
        with self.connection:
            self._insert_versioned("claims", {"record_id":"claim-lamp","claim_id":"claim-lamp","version_id":"claim-lamp-v1","claim_type":claim_type,"claim_status":status,"claim_origin":"user","claim_body":"Fictional indicator state is unresolved","evidence_ids":"[]","tx_from":NOW,"is_active":1,"created_at":NOW,"provenance_ref":"epistemic-set","semantic_version":2,"schema_version":2,"change_reason_code":"initial","created_by_actor_id":"actor-owner","proposition":"The east-bench indicator state is unresolved.","bounded_wording":"Two fictional reports conflict about one indicator.","population_scope":"one fictional station indicator","window_context":"summer to September 2042","falsification_criteria":"A validated fictional controller log could weaken this claim.","review_trigger":"Review if another fixture record is added.","alternatives":"Different times; source error.","counterfactual_cautions":"Lamp colour does not establish equipment state."})
            self._insert_versioned("uncertainty_profiles", {"record_id":"uncertainty-lamp","version_id":"uncertainty-lamp-v1","schema_version":2,"tx_from":NOW,"is_active":1,"change_reason_code":"initial","created_by_actor_id":"actor-owner","target_record_id":"claim-lamp","target_version_id":"claim-lamp-v1","target_kind":"claim"})
            for dimension,klass in (("source_authenticity","moderate"),("temporal","high"),("interpretation","high"),("missingness","high")):
                self.connection.execute("INSERT OR IGNORE INTO uncertainty_dimensions(profile_record_id,profile_version_id,dimension,class,rationale) VALUES(?,?,?,?,?)",("uncertainty-lamp","uncertainty-lamp-v1",dimension,klass,"Frozen multidimensional fixture appraisal"))
            self._insert_versioned("evidence_links", {"record_id":"evidence-amber","version_id":"evidence-amber-v1","schema_version":2,"tx_from":NOW,"is_active":1,"change_reason_code":"initial","created_by_actor_id":"actor-owner","source_record_id":"assertion-lamp","source_version_id":"assertion-lamp-v1","target_claim_record_id":"claim-lamp","target_claim_version_id":"claim-lamp-v1","relation":"supports","directness":"direct","source_independence_group":"owner-report","scope_match":"match","temporal_match":"partial","strength_class":"moderate","rationale":"Fictional source-near report","author_actor_id":"actor-owner"})
            self._insert_versioned("evidence_links", {"record_id":"evidence-green","version_id":"evidence-green-v1","schema_version":2,"tx_from":NOW,"is_active":1,"change_reason_code":"initial","created_by_actor_id":"actor-counter","source_record_id":"assertion-counter","source_version_id":"assertion-counter-v1","target_claim_record_id":"claim-lamp","target_claim_version_id":"claim-lamp-v1","relation":"contradicts","directness":"direct","source_independence_group":"maintenance-log","scope_match":"match","temporal_match":"unknown","strength_class":"moderate","rationale":"Fictional counterreport","author_actor_id":"actor-counter"})
            self._insert_versioned("contradiction_sets", {"record_id":"contradiction-lamp","version_id":"contradiction-lamp-v1","schema_version":2,"tx_from":NOW,"is_active":1,"change_reason_code":"initial","created_by_actor_id":"actor-owner","conflict_type":"incompatible_values","scope":"east_bench_indicator","time_context":"fuzzy or adjacent times","resolution_status":"unresolved","resolution_rationale":"The fixture does not adjudicate the conflict."})
            for member,version,role in (("assertion-lamp","assertion-lamp-v1","position"),("assertion-counter","assertion-counter-v1","counterposition")):
                self.connection.execute("INSERT OR IGNORE INTO contradiction_members(set_record_id,set_version_id,member_kind,member_record_id,member_version_id,member_role) VALUES(?,?,?,?,?,?)",("contradiction-lamp","contradiction-lamp-v1","assertion",member,version,role))
            self._insert_versioned("unknowns", {"record_id":"unknown-lamp","version_id":"unknown-lamp-v1","schema_version":2,"tx_from":NOW,"is_active":1,"change_reason_code":"initial","created_by_actor_id":"actor-owner","question":"Which fictional indicator state applied at the same clock?","scope":"east_bench_indicator","why_matters":"It controls whether the reports actually conflict.","knowledge_state":"The clocks are not aligned.","attempts":"Compared the two bundled reports.","what_could_reduce":"A fictional timestamped controller log.","burden_or_safety_concern":"No further collection is needed for this fixture.","status":"open","unknown_reason":"ambiguous"})
            # This cross-aggregate dependency has no direct FK: the unknown is
            # derived from the unresolved contradiction and must join its
            # deletion closure.  Other dependencies below are represented by
            # their frozen V2 FK/reference columns.
            self.connection.execute(
                "INSERT OR IGNORE INTO record_relations VALUES(?,?,?,?,?,?,?,?)",
                ("relation-contradiction-unknown", "contradiction-lamp", "contradiction-lamp-v1", "unknown-lamp", "unknown-lamp-v1", "derived_from", None, NOW),
            )
        return {"claim_label":"proposal","fact_label":False,"uncertainty_dimensions":4,"contradiction":"unresolved","unknown_reason":"ambiguous"}

    def _baseline_snapshot(self, _choice: str) -> dict[str, Any]:
        return self._create_snapshot("snapshot-baseline","snapshot-baseline-v1",None,None,"Baseline fixture snapshot","added")

    def _revised_snapshot(self, _choice: str) -> dict[str, Any]:
        return self._create_snapshot("snapshot-revised","snapshot-revised-v1","snapshot-baseline","snapshot-baseline-v1","Revised fixture snapshot preserves unresolved state","changed")

    def _create_snapshot(self,rid: str,vid: str,previous: str|None,previous_version: str|None,summary: str,change: str) -> dict[str,Any]:
        with self.connection:
            self._insert_versioned("personal_model_snapshots", {"record_id":rid,"version_id":vid,"schema_version":2,"tx_from":NOW,"is_active":1,"change_reason_code":"derivation","created_by_actor_id":"actor-system","derivation_id":"derivation-orchid-snapshot","evidence_transaction_cutoff":NOW,"domain_time_lower":"2042-06-01","domain_time_upper":"2042-09-01","domain_time_precision":"season","knowledge_snapshot_id":"fixture-knowledge-v1","previous_snapshot_record_id":previous,"previous_snapshot_version_id":previous_version,"change_summary":summary,"user_review_status":"not_reviewed","generation_derivation_id":"derivation-orchid-snapshot"})
            self.connection.execute("INSERT OR IGNORE INTO personal_model_snapshot_claims(snapshot_record_id,snapshot_version_id,claim_record_id,claim_version_id,inclusion_reason,change_class) VALUES(?,?,?,?,?,?)",(rid,vid,"claim-lamp","claim-lamp-v1","Pinned fixture claim",change))
            self.connection.execute("INSERT OR IGNORE INTO personal_model_snapshot_contradictions VALUES(?,?,?,?,1)",(rid,vid,"contradiction-lamp","contradiction-lamp-v1"))
            self.connection.execute("INSERT OR IGNORE INTO personal_model_snapshot_unknowns VALUES(?,?,?,?)",(rid,vid,"unknown-lamp","unknown-lamp-v1"))
            self.connection.execute("INSERT OR IGNORE INTO personal_model_snapshot_domain_summaries VALUES(?,?,?,?,?)",(rid+"-summary",rid,vid,"evidence_source_provenance",summary))
            self.connection.execute("INSERT OR IGNORE INTO personal_model_snapshot_algorithms VALUES(?,?,?,?,?)",(rid,vid,"orchid_fixture_snapshot","1.0.0",self._authority_digest))
        return {"snapshot_record_id":rid,"immutable":True,"ai_generated":False,"unresolved_contradiction":True,"open_unknown":True}

    def snapshot_diff(self) -> dict[str, Any]:
        baseline={row["claim_record_id"]:row for row in _rows(self.connection,"SELECT * FROM personal_model_snapshot_claims WHERE snapshot_record_id='snapshot-baseline'")}
        revised={row["claim_record_id"]:row for row in _rows(self.connection,"SELECT * FROM personal_model_snapshot_claims WHERE snapshot_record_id='snapshot-revised'")}
        return {"previous_snapshot":"snapshot-baseline-v1","current_snapshot":"snapshot-revised-v1","added":sorted(revised.keys()-baseline.keys()),"removed":sorted(baseline.keys()-revised.keys()),"changed":sorted(key for key in revised.keys()&baseline.keys() if revised[key]["change_class"]=="changed"),"unresolved_contradictions":1,"open_unknowns":1,"completion_percentage":None}

    def _correct_report_time(self, _choice: str) -> dict[str, Any]:
        return self.correct_lamp_report_time("report-lamp-v1")

    def correct_lamp_report_time(self, expected_version: str) -> dict[str, Any]:
        current=_row(self.connection,"SELECT * FROM reports WHERE record_id='report-lamp' AND is_active=1")
        if current is None: raise E03ArchiveError("RECORD_NOT_FOUND")
        if expected_version != current["version_id"]: raise E03ArchiveError("STALE_VERSION")
        correction_time="2042-09-02T10:05:00+00:00"
        successor=dict(current)
        successor.update({"version_id":"report-lamp-v2","previous_version_id":current["version_id"],"tx_from":correction_time,"tx_to":None,"is_active":1,"created_at":correction_time,"change_reason_code":"correction"})
        with self.connection:
            changed=self.connection.execute("UPDATE reports SET tx_to=?,is_active=0 WHERE record_id='report-lamp' AND version_id=? AND is_active=1",(correction_time,expected_version)).rowcount
            if changed != 1: raise E03ArchiveError("STALE_VERSION")
            columns=list(successor)
            self.connection.execute(f"INSERT INTO reports({','.join(columns)}) VALUES({','.join('?' for _ in columns)})",tuple(successor[c] for c in columns))
            self._insert_temporal("time-report-lamp-corrected","time-report-lamp-corrected-v1","report-lamp","report-lamp-v2",("reported","instant","2042-09-01T08:45:00+00:00","2042-09-01T08:45:00+00:00","minute","2042-09-01 08:45 UTC",1,"UTC"))
            self.connection.execute("INSERT INTO record_relations VALUES(?,?,?,?,?,?,?,?)",("relation-report-correction","report-lamp","report-lamp-v1","report-lamp","report-lamp-v2","corrects",None,correction_time))
        return {"record_id":"report-lamp","previous_version":"report-lamp-v1","current_version":"report-lamp-v2","change_reason":"correction","history_preserved":True}

    def timeline(self, temporal_role: str) -> list[dict[str, Any]]:
        if temporal_role not in {"occurred","observed","reported","recorded","asserted"}: raise E03ArchiveError("INVALID_TEMPORAL_ROLE")
        return _rows(self.connection,"SELECT target_record_id,temporal_role,value_kind,lower_value,upper_value,precision,original_literal,timezone_known,certainty_class FROM temporal_assertions WHERE temporal_role=? AND is_active=1 ORDER BY COALESCE(lower_value,''),record_id",(temporal_role,))

    def explorer(self) -> dict[str, Any]:
        return {"sources":_rows(self.connection,"SELECT record_id,artifact_kind,rights_note FROM source_artifacts WHERE semantic_version=2 AND is_active=1"),"reports":_rows(self.connection,"SELECT record_id,report_kind,verbatim_content FROM reports WHERE semantic_version=2 AND is_active=1"),"claims":_rows(self.connection,"SELECT record_id,claim_type,claim_status,proposition,alternatives FROM claims WHERE semantic_version=2 AND is_active=1"),"evidence":_rows(self.connection,"SELECT relation,directness,scope_match,temporal_match,strength_class,rationale FROM evidence_links WHERE is_active=1"),"uncertainty":_rows(self.connection,"SELECT dimension,class,rationale FROM uncertainty_dimensions"),"contradictions":_rows(self.connection,"SELECT conflict_type,resolution_status,resolution_rationale FROM contradiction_sets WHERE is_active=1"),"unknowns":_rows(self.connection,"SELECT question,status,unknown_reason,what_could_reduce FROM unknowns WHERE is_active=1"),"notice":"Claims are proposals, not facts. Evidence and derived state remain distinct."}

    def _delete_source(self, choice: str) -> dict[str, Any]:
        if choice == "dry_run":
            plan_id="orchid-delete-"+secrets.token_hex(6)
            plan=self._dependency_closure(plan_id)
            self._plans[plan_id]=plan
            return {"plan_id":plan_id,"counts":plan.counts,"mutated":False,"confirmation":"DELETE ORCHID LAMP SOURCE","limitations":["Previously exported or externally controlled copies are outside local deletion.","Retained backups expire under their declared policy."]}
        raise E03ArchiveError("PLAN_REQUIRED")

    @staticmethod
    def _placeholders(values: set[str] | tuple[str, ...]) -> str:
        return ",".join("?" for _ in values)

    def _matching_ids(self, table: str, result_column: str, match_column: str, values: set[str]) -> set[str]:
        if not values:
            return set()
        sql = f"SELECT DISTINCT {result_column} FROM {table} WHERE {match_column} IN ({self._placeholders(values)})"
        return {row[0] for row in self.connection.execute(sql, tuple(sorted(values)))}

    def _record_table(self, record_id: str) -> str | None:
        for table in (
            "source_artifacts", "source_locators", "reports", "observations",
            "assertions", "claims", "temporal_assertions", "evidence_links",
            "uncertainty_profiles", "contradiction_sets", "unknowns",
            "personal_model_snapshots",
        ):
            if self.connection.execute(
                f"SELECT 1 FROM {table} WHERE record_id=? LIMIT 1", (record_id,)
            ).fetchone():
                return table
        return None

    def _dependency_closure(self, plan_id: str) -> DeletionPreview:
        """Derive the bounded E03 deletion closure from canonical V2 edges."""
        nodes: dict[str, set[str]] = {
            "source_artifacts": {"source-lamp"},
            "source_locators": set(), "reports": set(), "observations": set(),
            "assertions": set(), "claims": set(), "temporal_assertions": set(),
            "evidence_links": set(), "uncertainty_profiles": set(),
            "contradiction_sets": set(), "unknowns": set(),
            "personal_model_snapshots": set(),
        }

        changed = True
        while changed:
            before = sum(len(values) for values in nodes.values())
            nodes["source_locators"] |= self._matching_ids(
                "source_locators", "record_id", "artifact_record_id", nodes["source_artifacts"]
            )
            for table in ("reports", "observations", "assertions"):
                nodes[table] |= self._matching_ids(
                    table, "record_id", "source_locator_record_id", nodes["source_locators"]
                )

            all_record_ids = set().union(*nodes.values())
            nodes["temporal_assertions"] |= self._matching_ids(
                "temporal_assertions", "record_id", "target_record_id", all_record_ids
            )

            if all_record_ids:
                placeholders = self._placeholders(all_record_ids)
                evidence_rows = self.connection.execute(
                    f"SELECT record_id,source_record_id,target_claim_record_id FROM evidence_links "
                    f"WHERE source_record_id IN ({placeholders}) OR target_claim_record_id IN ({placeholders})",
                    (*sorted(all_record_ids), *sorted(all_record_ids)),
                ).fetchall()
                for record_id, source_id, target_id in evidence_rows:
                    nodes["evidence_links"].add(record_id)
                    if source_id in all_record_ids:
                        nodes["claims"].add(target_id)

            all_record_ids = set().union(*nodes.values())
            nodes["uncertainty_profiles"] |= self._matching_ids(
                "uncertainty_profiles", "record_id", "target_record_id", all_record_ids
            )
            nodes["contradiction_sets"] |= self._matching_ids(
                "contradiction_members", "set_record_id", "member_record_id", all_record_ids
            )

            snapshot_ids = set()
            snapshot_ids |= self._matching_ids(
                "personal_model_snapshot_claims", "snapshot_record_id", "claim_record_id", nodes["claims"]
            )
            snapshot_ids |= self._matching_ids(
                "personal_model_snapshot_contradictions", "snapshot_record_id", "contradiction_record_id", nodes["contradiction_sets"]
            )
            snapshot_ids |= self._matching_ids(
                "personal_model_snapshot_unknowns", "snapshot_record_id", "unknown_record_id", nodes["unknowns"]
            )
            nodes["personal_model_snapshots"] |= snapshot_ids

            # Typed record_relations are directional dependency edges.  Follow
            # parent -> child only; deleting a derived child never deletes an
            # independent parent.
            all_record_ids = set().union(*nodes.values())
            if all_record_ids:
                relation_rows = self.connection.execute(
                    f"SELECT child_record_id FROM record_relations WHERE parent_record_id IN ({self._placeholders(all_record_ids)})",
                    tuple(sorted(all_record_ids)),
                ).fetchall()
                for (child_id,) in relation_rows:
                    table = self._record_table(child_id)
                    if table in nodes:
                        nodes[table].add(child_id)

            changed = sum(len(values) for values in nodes.values()) != before

        all_record_ids = set().union(*nodes.values())
        selectors: dict[str, tuple[str, tuple[str, ...]]] = {
            table: ("record_id", tuple(sorted(ids)))
            for table, ids in nodes.items() if ids
        }
        snapshot_ids = nodes["personal_model_snapshots"]
        for table in (
            "personal_model_snapshot_domain_summaries", "personal_model_snapshot_algorithms",
            "personal_model_snapshot_unknowns", "personal_model_snapshot_contradictions",
            "personal_model_snapshot_claims",
        ):
            if snapshot_ids:
                selectors[table] = ("snapshot_record_id", tuple(sorted(snapshot_ids)))
        if nodes["contradiction_sets"]:
            selectors["contradiction_members"] = ("set_record_id", tuple(sorted(nodes["contradiction_sets"])))
        if nodes["uncertainty_profiles"]:
            selectors["uncertainty_dimensions"] = ("profile_record_id", tuple(sorted(nodes["uncertainty_profiles"])))
        if all_record_ids:
            placeholders = self._placeholders(all_record_ids)
            relation_ids = {
                row[0] for row in self.connection.execute(
                    f"SELECT relation_id FROM record_relations WHERE parent_record_id IN ({placeholders}) OR child_record_id IN ({placeholders})",
                    (*sorted(all_record_ids), *sorted(all_record_ids)),
                )
            }
            if relation_ids:
                selectors["record_relations"] = ("relation_id", tuple(sorted(relation_ids)))

        counts: dict[str, int] = {}
        for table, (column, ids) in selectors.items():
            counts[table] = self.connection.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {column} IN ({self._placeholders(ids)})", ids
            ).fetchone()[0]
        return DeletionPreview(plan_id, counts, selectors)

    def execute_deletion(self, plan_id: str, confirmation: str, *, inject_failure: bool=False) -> dict[str, Any]:
        plan=self._plans.get(plan_id)
        if plan is None: raise E03ArchiveError("PLAN_INVALID")
        if confirmation != "DELETE ORCHID LAMP SOURCE": raise E03ArchiveError("CONFIRMATION_REQUIRED")
        current_plan = self._dependency_closure(plan_id)
        if current_plan.selectors != plan.selectors or current_plan.counts != plan.counts:
            raise E03ArchiveError("PLAN_STALE")
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            deletion_order = (
                "personal_model_snapshot_domain_summaries", "personal_model_snapshot_algorithms",
                "personal_model_snapshot_unknowns", "personal_model_snapshot_contradictions",
                "personal_model_snapshot_claims", "personal_model_snapshots",
                "contradiction_members", "evidence_links", "uncertainty_dimensions",
                "record_relations", "temporal_assertions", "uncertainty_profiles",
                "contradiction_sets", "unknowns", "claims", "observations",
                "assertions", "reports", "source_locators", "source_artifacts",
            )
            for table in deletion_order:
                selector = plan.selectors.get(table)
                if selector:
                    column, ids = selector
                    self.connection.execute(
                        f"DELETE FROM {table} WHERE {column} IN ({self._placeholders(ids)})", ids
                    )
            if inject_failure: raise RuntimeError("injected")
            receipt_id="deletion-receipt-"+secrets.token_hex(8)
            self.connection.execute(
                "INSERT INTO deletion_requests(request_id,actor_id,reason,scope,target_ids,approved_by,approved_at,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                ("orchid-request","actor-owner","deletion","tree","[]","actor-owner",NOW,"completed",NOW),
            )
            self.connection.execute(
                "INSERT INTO deletion_plans(plan_id,request_id,target_record_ids,exclusive_descendant_ids,mixed_descendant_ids,invalidate_ids,recompute_ids,dependency_graph_snapshot,executed_at,receipt_id,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                ("orchid-plan","orchid-request","[]","[]","[]","[]","[]","{}",NOW,receipt_id,"completed",NOW),
            )
            self.connection.execute(
                "INSERT INTO deletion_receipts(receipt_id,request_id,plan_id,records_deleted,records_invalidated,records_recomputed,verification_hash,executed_by,executed_at,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (receipt_id,"orchid-request","orchid-plan",sum(plan.counts.values()),0,1,None,"actor-owner",NOW,NOW),
            )
            self.connection.commit()
        except Exception as exc:
            self.connection.rollback()
            if inject_failure: raise E03ArchiveError("DELETION_FAILED_PRESERVED") from exc
            raise
        self._plans.pop(plan_id,None)
        return {"receipt_id":receipt_id,"counts":plan.counts,"content_in_receipt":False,"stable_content_hash":False,"projection_rebuild":"rebuilt","canonical_absence":self._verify_deleted(plan),"known_exclusions":["External copies remain outside local control.","Backups follow declared expiry."]}

    def _verify_deleted(self, plan: DeletionPreview) -> bool:
        from psyche_os.backup_export.versioned import create_versioned_export

        exported = create_versioned_export(self.connection)
        for table, (column, ids) in plan.selectors.items():
            if self.connection.execute(
                f"SELECT 1 FROM {table} WHERE {column} IN ({self._placeholders(ids)}) LIMIT 1", ids
            ).fetchone():
                return False
            if any(row.get(column) in ids for row in exported["tables"][table]):
                return False
        deleted_ids = {item for _, ids in plan.selectors.values() for item in ids}
        view = json.dumps(self.explorer(), sort_keys=True)
        return not any(record_id in view for record_id in deleted_ids)
