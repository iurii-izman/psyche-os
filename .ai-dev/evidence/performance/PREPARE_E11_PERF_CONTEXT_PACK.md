# PREPARE E11 — AI Dev OS v2 Performance Canary Context Pack

**Status: `E11 NOT IMPLEMENTED` — read-only preparation dry run.**
**`REAL_DATA_GATE`: CLOSED** (`docs/architecture/REAL_DATA_GATE.yaml`, `docs/development/STATE.yaml`).

## Task / goal

Implement the smallest E11 lifetime-operations slice: release manifest + reproducible gates, exact dependency/SBOM/license/build-provenance reconciliation, preservation/migration/recovery drill, source/license/security currentness checks, incident disable/rollback evidence, residual-risk/expiry register, machine-readable gate evidence and explicit signed decision package — all under a closed real-data gate (RISK-H, FULL/RELEASE).

## Authority (exact ranges)

### `docs/development/EPIC_MAP.md:214-229`

```text
## E11 — Lifetime Operations, Release Evidence, and Gate Decision

**Goal:** Make release, migration, preservation, dependency/currentness review, incident closure, and profile-specific real-data decisions repeatable over 1/5/20/40-year horizons.
**Why now:** Lifetime reliability is recurring work, but the first complete release/gate package must integrate evidence from every enabled boundary.
**Dependencies:** All capabilities intended for the candidate profile `ACCEPTED`; exact build/SBOM/evidence; independent reviews; no unresolved Critical/High. Optional rejected/deferred epics need not be implemented.
**Major deliverables:** Release manifest and reproducible gates; exact dependency/SBOM/license/build-provenance reconciliation including negative evidence cases; preservation/migration/recovery drill; source/license/security currentness checks; incident disable/rollback evidence; residual-risk/expiry register; machine-readable gate evidence and explicit signed decision package.
**Out of scope:** Automatic gate opening, marketing security/clinical claims, feature accumulation, hiding failed/expired evidence, real-data ingestion inside the gate-review task.
**Risk level:** `RISK-H`.
**Constitutional invariants touched:** C-01–C-20.
**Primary source documents:** Roadmap Phase 8; Real Data Gate; Master Spec §§20, 22–25; Privacy/Security Model PS-22–PS-26; Threat Model; Scientific Governance update/review; Mental Health AI Safety release/incident sections; Decision Log.
**Acceptance criteria:** Exact build/profile and all enabled trust boundaries are named; required RDG evidence is current and independently reviewed; expiry/regression triggers and rollback/disable paths work; residual risks are explicit; decision record is signed by authorized roles. If any requirement fails, status remains `CLOSED` without workaround.
**Validation level:** `FULL / RELEASE`, including a clean independent rerun of all affected gates and evidence-path validation.
**Codex review required:** yes, focused final review of evidence completeness, contradictions, claims, and gate logic; Codex cannot sign for required independent human authorities.
**REAL_DATA_GATE impact:** This is the only planned epic that may prepare an explicit profile-specific open/keep-closed decision. Opening is never automatic and is not authorized by this map.
**Estimated implementation complexity:** `L`; prompt/context cost `HIGH`.

```

### `docs/ROADMAP.md:120-132`

```text
## Phase 8 — Lifetime maintenance, not feature accumulation

Recurring work:

- quarterly during active development: provider/model/safety/current-law watch;
- at every release: schema/export/migration/deletion/restore and dependency/SBOM gates;
- annually: preservation formats, recovery drill, ontology/instrument/license and threat-model review;
- on source correction/retraction: knowledge impact and explicit reanalysis proposal;
- on platform cryptographic deprecation: staged migration with old-reader/recovery proof;
- on any incident: affected profile gate closes until reviewed.

Success is a smaller trustworthy system that remains interpretable and exit-friendly, not a growing count of integrations or a “complete” ontology.

```

### `docs/architecture/REAL_DATA_GATE.yaml:1-127`

```text
schema_version: "1.0"
gate_id: "PSYCHE-REAL-DATA-GATE"
snapshot_date: "2026-08-11"
status: "CLOSED"
research_converged: true
production_implementation_exists: false
scope:
  profiles: ["all"]
  data_classes:
    - "real_personal"
    - "psychological"
    - "medical_or_health"
    - "sexual_or_trauma"
    - "legal_or_financial_sensitive"
    - "messages_calendar_wearables_life_archive"
    - "third_party_personal"
  synthetic_fixtures_allowed: true
authority:
  constitution: "CONSTITUTION.md"
  master_spec: "docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md"
  privacy_security: "docs/architecture/PRIVACY_SECURITY_MODEL.md"
  threat_model: "docs/architecture/THREAT_MODEL.md"
  frozen_f0_contract: "docs/prompts/F0_IMPLEMENTATION_PROMPT.md"
  next_implementation_contract: "docs/prompts/deepseek/E02_SECURE_DESKTOP_SHELL.md"
  e00_rebaseline: "docs/development/E00_REBASELINE_DECISION.md"
opening_rule:
  automatic_opening_forbidden: true
  exact_build_and_profile_required: true
  independent_review_required: true
  unresolved_critical_or_high_findings_allowed: false
... [97 more lines]
```

### `CONSTITUTION.md:6-6`

```text
**Real personal data:** prohibited until `REAL_DATA_GATE = OPEN`.
```

### `CONSTITUTION.md:90-92`

```text
### C-20 — Synthetic-first gate

Research, implementation and verification use synthetic fixtures. `RESEARCH_CONVERGED = true` does not open the real-data gate. Only evidence that every gate control passes can change `REAL_DATA_GATE` from `CLOSED` to `OPEN`.
```

### `docs/development/STATE.yaml:7-11`

```text
real_data_gate:
  state: "CLOSED"
  authority: "docs/architecture/REAL_DATA_GATE.yaml"

current_epic:
```

### `docs/development/STATE.yaml:93-93`

```text
  instruction: "E10 is ACCEPTED and merged; E11 remains PLANNED; keep REAL_DATA_GATE CLOSED."
```

## Existing implementation context (V2 exact ranges)

- Terms: e09_retrieval, e08_filesystem, e10_professional_handoff, storage/schema, migrations

### src/psyche_os/adapters/e08_filesystem.py:1-1  [source=index-module]

```text
"""Outer E08 filesystem and application-owned quarantine boundary."""
```

### src/psyche_os/adapters/e08_filesystem.py:17-17  [source=index-symbol]

```text
REPARSE_POINT: Final = 0x400
```

### src/psyche_os/adapters/e08_filesystem.py:18-18  [source=index-symbol]

```text
READ_CHUNK: Final = 64 * 1024
```

### src/psyche_os/adapters/e08_filesystem.py:22-28  [source=index-symbol]

```text
class FileIdentity:
    device: int
    inode: int
    size: int
    modified_ns: int
    changed_ns: int
    mode: int
```

### src/psyche_os/adapters/e08_filesystem.py:32-50  [source=index-symbol]

```text
class QuarantineRecord:
    quarantine_id: str
    source_candidate_id: str
    source_version_id: str
    protected_digest_ref: str
    byte_count: int
    profile_id: str
    parser_identity: str
    policy_lineage_id: str
    declared_mime: str | None
    declared_encoding: str | None
    processing_state: str
    rejection_reason: str | None = None

    def __repr__(self) -> str:
        return (
            f"QuarantineRecord(quarantine_id={self.quarantine_id!r}, "
            f"byte_count={self.byte_count!r}, processing_state={self.processing_state!r})"
        )
```

### src/psyche_os/adapters/e08_filesystem.py:54-60  [source=index-symbol]

```text
class QuarantineSnapshot:
    record: QuarantineRecord
    bounded_bytes: bytes
    source_identity_current: bool

    def __repr__(self) -> str:
        return f"QuarantineSnapshot(record={self.record!r}, bounded_bytes=<redacted>, source_identity_current={self.source_identity_current!r})"
```

### src/psyche_os/adapters/e08_filesystem.py:63-68  [source=index-symbol]

```text
class FilesystemBoundaryError(RuntimeError):
    """Content-free typed outer-boundary error."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)
```

### src/psyche_os/adapters/e08_filesystem.py:72-79  [source=index-symbol]

```text
class _StoredObject:
    record: QuarantineRecord
    bounded_bytes: bytes
    path: Path
    identity: FileIdentity

    def __repr__(self) -> str:
        return "_StoredObject(record=<redacted>, bounded_bytes=<redacted>, path=<redacted>)"
```

- … and 63 more exact ranges; full volume in `prepare-e11.json`.

## Dependency / impact (deterministic)

- changed/resolved modules: adapters/e08_filesystem.py, application/e09_retrieval.py, application/e10_professional_handoff.py, storage/migrations.py, storage/schema.py
- affected modules (reverse-dep closure): 18 — __main__.py, adapters/e08_filesystem.py, application/desktop_service.py, application/e03_archive.py, application/e05_longitudinal.py, application/e06_experiments.py, application/e08_imports.py, application/e09_retrieval.py …
- classification: HIGH — storage/migrations.py is in a high-risk boundary; storage/schema.py is in a high-risk boundary
- affected tests: 30 mapped

## Likely verification surface

- targeted: `uv run pytest tests/contracts/test_cli_contracts.py tests/integration/test_e00_portability_smoke.py tests/integration/test_e00_rebaseline_gate.py tests/integration/test_e01_backup_faults.py tests/integration/test_e01_backup_restore.py tests/integration/test_e01_recovery_drill.py tests/integration/test_e01_windows_boundary.py tests/integration/test_e02_sidecar_protocol.py tests/integration/test_e03_canonical_archive.py tests/integration/test_e03_migration.py tests/integration/test_e05_longitudinal_analysis.py tests/integration/test_e05_migration.py tests/integration/test_e06_migration.py tests/integration/test_e06_n_of_1_protocols.py tests/integration/test_e07_bounded_ai_proposal.py tests/integration/test_e08_import_lifecycle.py tests/integration/test_e08_migration.py tests/integration/test_e09_retrieval.py tests/integration/test_e10_professional_handoff.py tests/integration/test_storage_integration.py tests/regression/test_regression_proofs.py tests/security/test_e08_review_repairs.py tests/security/test_e08_untrusted_import.py tests/unit/test_ai_dev_perf.py tests/unit/test_e02_desktop_service.py tests/unit/test_e03_archive_service.py tests/unit/test_e05_longitudinal_analysis.py tests/unit/test_e06_n_of_1_protocols.py tests/unit/test_e08_import_core.py tests/unit/test_e08_plain_text_parser.py -q --tb=short --no-header`  (gate: V1/V2 targeted, 30 test file(s))
- final gate (once): `uv run pytest -q` + `scripts/dev/validate_orchestration.py` + `scripts/validate_research_foundation.py`

## Unknowns

- exact release manifest / SBOM / license provenance toolchain not yet selected;
- preservation formats and dependency/currentness source list not frozen;
- independent-review inputs and signed decision package not gathered;
- profile-specific `REAL_DATA_GATE` open/keep-closed decision is never automatic and is not authorized by `EPIC_MAP.md`.

## Metrics — V1 vs V2 on the current tree

| metric | V1 | V2 |
|---|---|---|
| selected context bytes | 3,169 | 74,676 |
| estimated context tokens | 792 | 18,669 |
| targeted context tokens (target untruncated) | 792 | 18,669 |
| raw tool-output bytes | 21,534 | 0 |
| bytes searched (rg scan volume) | 4,164,755 | 0 |
| local tool calls | 10 | 0 |
| exact ranges selected | 41 | 71 |
| files selected | 13 | 5 |
| full-file inclusions | 0 | 0 |
| retrieval wall ms (warm) | 413.2 | 29.5 |
- V2 index: one-time local build cached on disk (amortized across repeated prep work).

## V1 retrieval equivalent

- files selected (13): `src/psyche_os/application/desktop_service.py`, `src/psyche_os/application/e03_archive.py`, `src/psyche_os/application/e05_longitudinal.py`, `src/psyche_os/application/e06_experiments.py`, `src/psyche_os/application/e08_imports.py`, `src/psyche_os/backup_export/operations.py`, `src/psyche_os/backup_export/versioned.py`, `src/psyche_os/interfaces/cli.py`, `src/psyche_os/projections/e09_lexical.py`, `src/psyche_os/storage/__init__.py`, `src/psyche_os/storage/e03_schema.py`, `src/psyche_os/storage/migrations.py`, `src/psyche_os/storage/schema.py`
- tests discovered (18): `tests/integration/test_e00_portability_smoke.py`, `tests/integration/test_e00_rebaseline_gate.py`, `tests/integration/test_e01_backup_faults.py`, `tests/integration/test_e01_backup_restore.py`, `tests/integration/test_e01_recovery_drill.py`, `tests/integration/test_e01_windows_boundary.py`, `tests/integration/test_e03_migration.py`, `tests/integration/test_e05_migration.py`, `tests/integration/test_e06_migration.py`, `tests/integration/test_e08_import_lifecycle.py`, `tests/integration/test_e08_migration.py`, `tests/integration/test_e09_retrieval.py`, `tests/integration/test_e10_professional_handoff.py`, `tests/integration/test_storage_integration.py`, `tests/regression/test_regression_proofs.py`, `tests/security/test_e08_review_repairs.py`, `tests/security/test_e08_untrusted_import.py`, `tests/unit/test_e08_import_core.py`

## V2 retrieval equivalent

- files selected (5): `src/psyche_os/adapters/e08_filesystem.py`, `src/psyche_os/application/e09_retrieval.py`, `src/psyche_os/application/e10_professional_handoff.py`, `src/psyche_os/storage/migrations.py`, `src/psyche_os/storage/schema.py`
- tests mapped (18): `tests/integration/test_e00_portability_smoke.py`, `tests/integration/test_e00_rebaseline_gate.py`, `tests/integration/test_e01_backup_faults.py`, `tests/integration/test_e01_backup_restore.py`, `tests/integration/test_e01_recovery_drill.py`, `tests/integration/test_e01_windows_boundary.py`, `tests/integration/test_e03_migration.py`, `tests/integration/test_e05_migration.py`, `tests/integration/test_e06_migration.py`, `tests/integration/test_e08_import_lifecycle.py`, `tests/integration/test_e08_migration.py`, `tests/integration/test_e09_retrieval.py`, `tests/integration/test_e10_professional_handoff.py`, `tests/integration/test_storage_integration.py`, `tests/regression/test_regression_proofs.py`, `tests/security/test_e08_review_repairs.py`, `tests/security/test_e08_untrusted_import.py`, `tests/unit/test_e08_import_core.py`
- term resolutions: e09_retrieval=module, e08_filesystem=module, e10_professional_handoff=module, storage/schema=module, migrations=module

---

_`E11 NOT IMPLEMENTED`. `REAL_DATA_GATE CLOSED`. Read-only pack generated by `scripts/ai_dev_perf.py prepare-e11` (2026-08-16T20:33:52.047581+00:00)._
