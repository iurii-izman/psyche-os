# E03 canonical model / V2 migration preflight

**Date:** 2026-08-13  
**Verdict:** `READY_TO_IMPLEMENT`  
**Schema verdict:** `V2_REQUIRED`  
**Risk / gate:** `RISK-H / FULL`  
**REAL_DATA_GATE:** `CLOSED`

## Canonical model matrix

| Concept | Authority | Domain | V1 persistence | Classification | Frozen E03 decision |
| --- | --- | --- | --- | --- | --- |
| `SourceArtifact` | Master Spec §19; Data Model §4.1 | Present | Row exists but canonical intake, rights and correction fields are incomplete and rely on generic metadata | `V1_PARTIAL` | Rebuild table with explicit V2 columns; preserve V1 fields/rows. |
| `SourceLocator` | Data Model §4.3 | Present | Only loose locator IDs; no canonical locator row | `V2_REQUIRED` | Add versioned `source_locators`. |
| `Report` | Data Model §4.4 | Present | Report-shaped aggregate, not authoritative attributed verbatim report | `V1_PARTIAL` | Add explicit report/provenance fields; generic V1 fields become legacy-only. |
| `Observation` | Data Model §4.6 | Present | Partial; construct/context/quality/source locator are missing or generic | `V1_PARTIAL` | Add explicit V2 fields. |
| `Assertion` | Data Model §6.1 | Present | Partial and includes forbidden generic confidence | `V1_PARTIAL` | Add explicit V2 fields; V2 never writes `confidence`. |
| `Claim` | Master Spec §6.3; Data Model §6.2 | Present | Version rows exist but DDL enums contradict authority and semantics are incomplete | `V2_REQUIRED` | Conditional semantic-version constraints; V1 raw values retained, V2 authoritative values only. |
| `EvidenceLink` | Master Spec §9.2; Data Model §6.3 | Present | JSON ID lists/provenance refs cannot preserve typed axes | `V2_REQUIRED` | Add versioned `evidence_links`. |
| `UncertaintyProfile` | Master Spec §6.4; Data Model §6.4 | Present | No canonical table | `V2_REQUIRED` | Add profile plus checked per-dimension rows. |
| `ContradictionSet` | Master Spec §6.5; Data Model §6.5 | Present | Only a claim scalar/JSON; no members/history | `V2_REQUIRED` | Add set and member tables. |
| `Unknown` | Master Spec §6.6; Data Model §6.6 | Present | No canonical table | `V2_REQUIRED` | Add versioned `unknowns` with checked reason. |
| `TemporalAssertion` | Master Spec §9.3; Data Model §5 | Present | Ad hoc timestamps/refs lose clocks, bounds and precision | `V2_REQUIRED` | Add canonical multi-clock version table. |
| `PersonalModelSnapshot` | Constitution purpose; Data Model §7.2 | Missing | No table; `KnowledgeSnapshot` is distinct | `V2_REQUIRED` | Add immutable derived snapshot and typed membership/summary/algorithm tables; add smallest matching domain entity during E03. |
| correction/version history | Constitution C-09; Data Model §§2.2, 12.1 | `VersionRow` present | Partial envelopes and active uniqueness exist | `V1_PARTIAL` | Complete version envelopes on E03 tables; atomic close/insert and stale-version rejection. |
| dependency/deletion relations | Constitution C-14; ADR-009; Data Model §12.2 | Deletion types present | Generic closure machinery cannot enumerate absent E03 relations | `V2_REQUIRED` | Add typed `record_relations`; traverse all direct E03 membership/provenance edges. |
| timeline/explorer/diff read models | Master Spec §21; ADR-018 | Not canonical entities | None | `VIEW_ONLY_E03` | Build deterministic rebuildable views from canonical rows. |
| measurements/assessments/AI/import/search/analytics | E03/E04 boundary | Some skeletons exist | Outside E03 | `DEFERRED` | No schema or behavior expansion. |

No `AUTHORITY_CONFLICT` was found. A Python dataclass was not treated as proof
of persisted support.

## Schema verdict

`V2_REQUIRED`

V1 cannot encode E03 without unrelated JSON catch-alls, enum weakening,
source/derived conflation, temporal precision loss and incomplete
provenance/deletion closure.

## Exact V2 delta

Rebuild, without changing any V1 value, these five tables to retain all legacy
columns and add explicit V2 semantics: `source_artifacts`, `reports`,
`observations`, `assertions`, and `claims`. Each gains `semantic_version`,
`schema_version`, change reason and creating actor while reusing the accepted
`record_id`/`version_id`/`tx_from`/`tx_to`/`is_active`/`previous_version_id`
envelope; source artifacts and reports also gain the derivation field already
present on the other three. Their canonical field groups are frozen in the
corrected E03 prompt.

Add exactly these fifteen tables:

1. `source_locators`
2. `temporal_assertions`
3. `evidence_links`
4. `uncertainty_profiles`
5. `uncertainty_dimensions`
6. `contradiction_sets`
7. `contradiction_members`
8. `unknowns`
9. `personal_model_snapshots`
10. `personal_model_snapshot_claims`
11. `personal_model_snapshot_contradictions`
12. `personal_model_snapshot_unknowns`
13. `personal_model_snapshot_domain_summaries`
14. `personal_model_snapshot_algorithms`
15. `record_relations`

Versioned records use stable opaque `record_id`, distinct `version_id`,
half-open transaction time and one-active-version uniqueness. Direct ownership
and membership use FKs; polymorphic cross-aggregate edges use checked typed
relations. Correctness indexes cover active uniqueness, locator artifact,
temporal target/role, evidence target/source, uncertainty target,
contradiction membership, snapshot membership and relation parent/child only.
The normative per-column, FK, check, provenance, temporal, deletion and index
contract for every rebuilt/added table is frozen in the corrected E03 prompt's
“Frozen preflight decision and implementation contract” section; this report
and that prompt form one preimplementation contract and may not be weakened by
implementation convenience.

## Enum compatibility

Authoritative V2 values are exactly the current domain `ClaimType`,
`ClaimStatus` and `ClaimOrigin` enums.

V1 rows retain `semantic_version=1` and their raw strings. Only `descriptive`,
`proposed` and `superseded` are identical across the relevant V1/V2 domains.
`causal`→`causal_hypothesis` and `predictive`→`prediction` are review
suggestions, not deterministic migration. All other V1 type/status values and
all V1 origins are ambiguous and remain namespaced legacy meanings. V2 writes
use `semantic_version=2` and only authoritative enum values. Backup, restore
and export preserve raw legacy values byte-for-byte at the logical-row level.

## PersonalModelSnapshot decision

`PersonalModelSnapshot` is canonical persisted state and an immutable derived
record, not a rebuildable projection. It pins evidence transaction/domain-time
cut-offs, exact claim/contradiction/unknown versions, knowledge snapshot,
algorithm versions, exclusions, previous snapshot, review state and the
generating deterministic derivation. Timeline and diff are rebuildable views.
It is distinct from `KnowledgeSnapshot`. E03 must add the smallest domain type
matching Data Model §7.2 plus the frozen persistence tables; it must not add AI
generation semantics.

## Backup/restore compatibility

`V1_INVENTORY` remains exactly:

`vault_config`, `actors`, `subjects`, `source_artifacts`, `blobs`, `reports`,
`observations`, `assertions`, `claims`, `data_policies`, `policy_lineage`,
`derivation_runs`, `derivation_io`, `audit_events`, `deletion_requests`,
`deletion_plans`, `deletion_receipts`, `backup_manifests`, `export_manifests`,
`schema_migrations`.

`V2_INVENTORY` is that exact 20-table set plus the exact fifteen-table list in
the previous section. Operations select inventory by declared schema version;
exact-set, uniqueness and checksum checks remain mandatory. V1 stays readable,
verifiable and restorable through its frozen reader. V2 restore validates the
exact V2 set in isolation before activation. V2 logical export declares its
format/schema and exact per-table schemas/checksums. No downgrade is promised;
rollback is restoration/activation of the retained verified pre-migration V1
vault or backup.

The V1→V2 migration is forward-only, checksummed and one-transaction. It
requires exact/checksummed V1, a verified backup and export, integrity/FK
success and no pending deletion/migration. It preserves V1 rows and legacy
enums, validates counts/digests, temporal intervals, links, deletion closure
and V2 inventory, and fails closed on any mismatch or interruption. A rerun
after success is a verified no-op.

## Deletion impact

Closure adds locator→artifact, temporal→target, evidence→source/claim,
uncertainty→target, contradiction→member, snapshot→all members/summaries/
algorithms/derivation and typed correction/replacement/provenance relations.
Exclusive descendants are deleted; mixed non-reconstructive derivations are
invalidated. A snapshot or summary that could reconstruct a deleted input is
deleted. Views/projections rebuild, receipts contain no content or stable
content hash, and canonical/raw/rebuilt-view/export absence is verified.

## Synthetic capture boundary

The only E03 pack is repository-owned `e03_orchid_station_v1`, a fictional
greenhouse-maintenance scenario. The renderer may submit only an operation ID,
an allowlisted temporal preset/enum choice for that operation and an
idempotency key. All persisted strings and IDs come from the signed/bundled
pack; renderer labels are selectable display text and are never persisted.

| Operation | Fixed canonical effect | Allowed choices |
| --- | --- | --- |
| `CAPTURE_LAMP_REPORT` | Fixed source artifact, locator, report and source-near assertion about a fictional indicator lamp | IDs from the pack; report kind `event_account`; reported exact or occurred `summer_2042` preset. |
| `CAPTURE_LAMP_OBSERVATION` | Fixed self-observation and observed interval | Observation kind `self_observation`; fixed exact/interval preset only. |
| `CAPTURE_COUNTERREPORT` | Fixed second source/report/assertion | Fixed actor/source IDs; reported exact or occurred unknown preset. |
| `ASSEMBLE_EPISTEMIC_SET` | Fixed claim, evidence links, uncertainty dimensions, contradiction and unknown | Claim type `descriptive` or `pattern`; status `proposed`, `user_accepted` or `contested`; origin `user`; relation values `supports`, `contradicts`, `qualifies`, `cannot_discriminate`. |
| `CREATE_BASELINE_SNAPSHOT` | Fixed deterministic immutable baseline snapshot | Fixed evidence cut-off and algorithm/version. |
| `CREATE_REVISED_SNAPSHOT` | Fixed deterministic successor and diff inputs | Fixed prior snapshot; only pack-defined membership change. |
| `CORRECT_LAMP_REPORT_TIME` | Fixed correction/version reason and temporal replacement | Fixed target/base version; reason `correction`; pack-defined time preset. |
| `DELETE_LAMP_SOURCE` | Fixed source-and-derivatives dry-run/confirmed deletion | Fixed root ID/scope; exact pack confirmation ID. |

No arbitrary text, paths, table names, record bodies, IDs, dates, enum strings,
fixture paths or general synthetic-write tokens are accepted. The authority is
bound to this exact pack identity and digest.

## Risk decision

`RISK-H / FULL`: E03 introduces V2 canonical persistence, conditional enum
compatibility, new deletion closure and a 15-table exact backup/restore
inventory extension.

## Residual uncertainties

None blocks implementation. The implementation must prove SQLite table-rebuild
atomicity, exact V1 reader retention and the frozen failure cases; failure of
any proof is a gate failure, not permission to relax this contract.

## Verdict

`READY_TO_IMPLEMENT`

Frozen targets remain exactly:

- T1 Canonical synthetic capture
- T2 Fuzzy and multi-clock time
- T3 Evidence/claims/contradictions/unknowns
- T4 Snapshot change
- T5 Canonical correction
- T6 Dependency-aware deletion
- T7 Accessible offline UX

E03 remains `READY / NOT_STARTED`; E04 remains `PLANNED`; `REAL_DATA_GATE`
remains `CLOSED`.
