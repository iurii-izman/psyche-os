# PSYCHE OS — EPIC E00: Minimal Irreversible Secure Core

**Project root:** `C:\Dev\psyche-os`
**Status on entry:** `READY`
**Risk:** `RISK-H`
**Required final gate:** `FULL`
**Required next checkpoint:** focused Codex high-risk review
**Data state:** `REAL_DATA_GATE = CLOSED`

## Role and outcome

You are the primary implementation engineer for E00. Implement only the local Python 3.12+ synthetic-only F0 core and CLI. Prove the semantic, cryptographic, policy-lineage, deletion, migration, recovery, and portability properties that cannot safely be retrofitted after sensitive bytes exist.

Work autonomously through implementation and validation. Do not replace behavior with design prose or mark an unavailable security profile as passing. If SQLCipher, OS wrapping, licensing, or recovery cannot be honestly proved on the target platform, fail closed, complete safe independent layers, record the exact blocker, and report `BLOCKED` or `PARTIAL_SYNTHETIC_ONLY`. Never use plaintext SQLite under an encrypted profile name and never open the data gate.

## Read first

Read these files completely before editing:

1. `AGENTS.md`
2. `CONSTITUTION.md`
3. `docs/development/STATE.yaml`
4. `docs/development/DEVELOPMENT_STRATEGY.md`
5. `docs/development/EPIC_MAP.md` — only E00 and the lifecycle/review notes
6. `docs/prompts/F0_IMPLEMENTATION_PROMPT.md`
7. `docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md` — §§4, 6, 9, 16, 19–20, 22, 24–25, and IC-1–IC-8; inspect adjacent definitions when referenced
8. `docs/architecture/DATA_MODEL.md`
9. `docs/architecture/SYSTEM_ARCHITECTURE.md`
10. `docs/architecture/PRIVACY_SECURITY_MODEL.md`
11. `docs/architecture/THREAT_MODEL.md`
12. `docs/architecture/REAL_DATA_GATE.yaml`
13. `docs/DECISION_LOG.md` — ADR-002–ADR-010, ADR-017, ADR-020 and supersession rules
14. `docs/ROADMAP.md` — Phases 1–2 and exact current state
15. `docs/SCIENTIFIC_GOVERNANCE.md` — §§1, 4–5, 8, 10, 12–13
16. `ontology/psyche_domains.yaml` — registry/version/reference contract, not scientific content expansion

`docs/prompts/F0_IMPLEMENTATION_PROMPT.md` is the binding detailed F0 control catalog. This E00 prompt changes delivery mechanics and removes repeated prose; it does not weaken its technical, semantic, security, privacy, deletion, recovery, export, or evidence requirements. When the old prompt's process wording conflicts with the current development strategy, follow this prompt for workflow. In particular, coverage is diagnostic and no arbitrary percentage is an acceptance condition; the named invariant, security, property, fault, and end-to-end proofs remain mandatory.

Do not load historical v1, the giant research master prompt, the research dossier/source registry, the mental-health AI safety document, or unrelated review reports unless a concrete blocker requires an exact cited decision. F0 has no AI or clinical behavior.

## Inspect and protect the worktree

Before editing run and record in the F0 report:

```powershell
git status --short
git branch --show-current
git log -1 --oneline
rg --files
python --version
```

Read applicable nested `AGENTS.md`, inspect existing package/lock/tests/scripts/CI, preserve unrelated changes, and use `apply_patch` for manual edits. Do not read external user data directories. Do not commit, push, open a PR, rewrite history, or modify frozen research/architecture documents. The only normative file that may receive exact implementation evidence is the existing `docs/architecture/REAL_DATA_GATE.yaml`, which must stay `CLOSED` and must not claim independent review.

## Absolute scope

### Implement

- A local single-user Python package and CLI with no listener or network path.
- Opaque random 128-bit identifiers, immutable version rows, half-open transaction-time intervals, optimistic version conflict, and explicit rich domain time (`exact`, interval, fuzzy, unknown; precision and timezone known/assumed).
- Separate source/verbatim, report/observation/assertion, and derived claim layers; typed provenance/derivation/evidence; multidimensional uncertainty; contradiction and unknown as entities.
- Versioned orthogonal `DataPolicy`, deterministic fail-closed composition, and transitive `NEVER_CLOUD` inheritance for reconstructive descendants.
- A standard-library-or-maintained-library envelope/key design: 256-bit VMK, domain-separated keys, verified OS convenience wrap, independent Argon2id recovery wrap, lifecycle/rotation states, and secret input outside argv/env/logs.
- A fail-closed SQLCipher profile proven by runtime/build/license/wrong-key/header/plaintext-artifact/integrity/backup probes. Ordinary SQLite may exist only as an explicitly unsafe ephemeral synthetic test adapter unreachable from normal CLI.
- Independently authenticated encrypted blob envelopes and a restartable stage/verify/register/activate/reconcile protocol with named filesystem/database fault points.
- Content-free allowlisted operational audit; distinct correction, supersession, rejection, invalidation, and hard-deletion operations; dependency traversal and receipts.
- Checksummed/versioned migrations; authenticated encrypted backup; recovery-only isolated restore; versioned JSONL/JSON Schema/Markdown logical export inside an authenticated encrypted package; synthetic semantic round trip.
- Knowledge/source/snapshot, ontology, and assessment registries only as metadata skeletons. Assessment state defaults blocked; no item/scoring/content fields.
- Package-owned fictional fixtures, typed CLI/JSON errors, automated validators, SBOM/license review, threat-test evidence, and compact implementation reports.

### Never implement in E00

- Real personal, psychological, medical, sexual/trauma, family, legal/financial, message/calendar/wearable/life-archive, or third-party data.
- Arbitrary note/free-text/stdin/file/JSON capture, general import, or a switch that enables real data.
- Desktop/web/mobile UI, webview, HTTP/RPC/localhost server, daemon, remote access, telemetry, network client, cloud, sync, sharing, or collaboration.
- LLM/provider SDK, prompt execution, embeddings, tools/agents/MCP, graph/vector/full-text/analytics projection engine.
- Assessment items/manuals/translations/scoring/norms/cutoffs, diagnosis, triage, therapy, crisis behavior, treatment, clinical or causal conclusion.
- Email/message/calendar/wearable/document parsers, FHIR/clinician export, N-of-1/interventions/reminders, multi-user/mobile/sync scaffolding, custom cryptographic primitives, plaintext fallback, or secrets in code/config/CLI/log/tests.

The normal `src/` dependency list and imports must contain no network/provider/web framework. A future enum/interface is not permission to add an adapter.

## Non-negotiable implementation contracts

Use the detailed requirements and stable section numbers in the original F0 prompt. At minimum the implementation and tests must enforce all contracts below.

### Synthetic-only capability

Every vault has immutable `data_mode = synthetic_only`. The only content-writing path loads an allowlisted built-in package-resource fixture pack with manifest, schema/version, `synthetic_fixture = true`, and digest. A `SyntheticFixtureCapability` is issued only after manifest verification and cannot be obtained through flag/env/file/direct repository call. Restore, migration, backup, and export preserve and verify the marker. Negative tests cover unknown pack, altered digest/manifest, direct repository bypass, restore/export, and migration. CLI accepts no arbitrary content.

### Dependency direction and canonical semantics

Implement or preserve `domain`, `temporal`, `provenance`, `policy`, `application`, `crypto`, `storage`, `backup_export`, `knowledge`, `adapters`, and `interfaces` boundaries described in original F0 §5. Pure layers import no infrastructure; application uses typed ports and one unit of work; interfaces never use SQL/files directly. Inject clock, randomness, secrets, wrappers, crypto, database, blob store, and faults. Add an architecture import test. Do not create a catch-all utility or generic JSON entity that bypasses types/policy/provenance.

Implement the canonical minimum in original F0 §6 and Data Model §16. Version rows have stable record ID, distinct version ID, schema version, transaction interval, change reason, actor, and supersession/derivation links. At most one active non-overlapping version exists. Never invent timestamps or a generic truth/confidence flag. Derived records require a valid `DerivationRun` and typed inputs; source-near assertions require a locator or typed unavailable reason; causal/diagnostic claim creation fails closed.

### Policy and privacy

Implement all policy axes and `NEVER_CLOUD` rules in original F0 §7/PS-01–PS-03. Missing/unknown/contradictory policy, unknown derivation edge, or lineage cycle fails closed. The effective derivative is the most restrictive parent on every axis; declassification does not exist. Property tests cover arbitrary DAG order, monotonicity, transitive closure, commutativity/idempotence where applicable, cycles, and unknown types. Local export still needs explicit audience/export permission.

Audit schema allows only stable codes, UTC time, opaque IDs/types, policy/rule/schema versions, correlation ID, and coarse buckets. It never accepts content, paths, search terms, responses/prompts, diagnosis-like state, names, secrets, exception dumps, or stable content hashes, including debug/failure paths.

### Cryptography, storage, and recovery

Use only maintained pinned crypto libraries and document exact versions, algorithms, nonce/AAD canonicalization, license, residual risks, and Python zeroization limits. Recovery material is not a database key and is never embedded in backup. Unknown key/envelope versions fail closed; rotation is restartable and retired keys cannot write.

The SQLCipher profile is enabled only after all eight probes in original F0 §8.3 pass on the actual driver/build. If they fail, normal vault creation returns `SQLCIPHER_PROFILE_UNAVAILABLE` with no fallback. Independently authenticated blob AAD includes the original required identity/version/length fields. Tamper/integrity/schema failure stops writes with a non-content error.

Correction writes a new version and invalidates descendants without rewriting source bytes. Hard deletion implements the plan/traverse/delete-or-recompute/blob/history/receipt/retry/absence contract in original F0 §10. Do not promise physical erasure of SSD/OS or external copies.

Migrations, backup/restore, and export implement every requirement and negative case in original F0 §11. Restore never mutates the active vault until an isolated target passes authentication, inventory, database/blob, migration, domain/policy/derivation, and rebuild/no-op validation. Outputs never overwrite existing targets. Export contains open versioned formats after authorized decryption, not plaintext-on-disk by default.

### CLI and artifacts

Implement the exact command surface in original F0 §12. Secret entry uses masked TTY with injected test composition only. Commands expose IDs/counts/status/versions and stable content-free JSON/error schemas. `doctor` reports exact profile blockers. `gate status --json` always reports `CLOSED` in E00.

Create/adapt every deliverable in original F0 §13, including:

- `pyproject.toml`, `uv.lock`, `src/psyche_os/**`, versioned migrations and export schemas;
- focused `tests/unit`, `property`, `integration`, `security`, `faults`, `contracts`, and manifest-declared synthetic fixtures;
- `scripts/validate_f0_scope.py` and `scripts/validate_f0_artifacts.py`;
- `docs/implementation/F0_IMPLEMENTATION_REPORT.md`, threat-test matrix, license/crypto review, and machine-readable test evidence;
- `artifacts/f0/sbom.cdx.json` without local paths or secrets.

Do not create another gate file. In the existing gate, `status` remains `CLOSED`, `production_implementation_exists` remains `false` for the reviewed production profile, independent/Phase 2 requirements remain `UNSATISFIED`, and evidence claims distinguish synthetic implementation from authorization.

## Implementation sequence and targeted validation

Work in bounded slices; after each slice run only the owning tests before continuing:

1. Discovery, dependency/license/target-profile feasibility, threat-to-test matrix.
2. Package boundaries, synthetic capability, architecture/scope tests.
3. Pure IDs/version/time/provenance/claim invariants.
4. Policy and arbitrary-lineage property tests.
5. Key envelopes, OS/recovery wraps, blob AEAD known-answer/tamper tests.
6. SQLCipher probe, storage/migrations, unit of work, crash-safe blob protocol.
7. Audit, correction, deletion closure and fault recovery.
8. Backup/restore/export, corruption/rollback cases and semantic round trip.
9. Restricted CLI and stable JSON/error contracts.
10. Threat/fault/supply-chain/plaintext/secret/scope evidence, reports, final diff.

Do not introduce a temporary plaintext or secret shortcut. When an infrastructure profile is blocked, keep it unavailable and continue safe pure-layer work.

The deterministic threat/fault suite must cover the relevant `TM-*` mappings and every minimum scenario in original F0 §§15 and 17: wrong keys/recovery, clean recovery without OS wrap, unlocked-endpoint residual risk, unique plaintext canary scans across all artifacts, opaque IDs, arbitrary policy DAG, backup tamper/rollback/poisoning, crash points, deletion/history/derivative closure, content-free logging on error, locked dependencies/SBOM/license/secret checks, bit-flip/swap/truncation, synthetic-capability bypass, and absence of forbidden infrastructure. A mock that never crosses the real boundary is not proof.

## Exact validation

During development run the narrow test directories/modules that own the changed layer. After they pass, run this final gate once from the repository root, using the accepted locked workflow:

```powershell
uv sync --frozen --all-groups
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests scripts
uv run coverage run -m pytest -q
uv run coverage report
uv run python scripts/validate_f0_scope.py
uv run python scripts/validate_f0_artifacts.py
uv run python -m psyche_os doctor --json
uv run python -m psyche_os gate status --json
python scripts/dev/validate_orchestration.py
python scripts/validate_research_foundation.py
git diff --check
git status --short
```

If the existing repository standardizes a different single frozen package workflow during implementation, use it consistently and record the exact justified replacement in both reports; do not keep two drifting lock flows. Run target-platform SQLCipher/OS-wrap/recovery integration tests. A security skip is a blocker for that profile, not a pass. Coverage output is diagnostic: inspect untested high-risk branches, but do not add low-value tests to reach a number.

`F0_TEST_EVIDENCE.json` records UTC time, commit/worktree identity, OS/Python/dependency/SQLCipher/crypto versions, commands/exit codes/test counts/skips/xfails, artifact digests, gate state and blockers without username/home/vault/content/secrets.

## Acceptance criteria

E00 may be reported `SYNTHETIC_TARGET_IMPLEMENTED` only when all are true:

- [ ] Scope validator proves no arbitrary input, forbidden module/dependency/command, network/listener/provider/import/scoring path, or real-data capability.
- [ ] Version/time/provenance/claim/evidence/uncertainty/contradiction/unknown and database invariants have executable positive/negative tests.
- [ ] Arbitrary `NEVER_CLOUD` lineage property tests pass, including unknown/cycle fail-closed cases.
- [ ] Actual SQLCipher, wrong-key/header/plaintext scans and target dependency/build/license proof pass without fallback.
- [ ] OS wrap and independent recovery wrap both pass; loss/corruption/rotation faults do not mutate data.
- [ ] Blob/database crash reconciliation and tamper/integrity write-stop tests pass.
- [ ] Correction and hard deletion cover every implemented entity, historical versions, blobs, exclusive/mixed descendants, export/rebuild, and retry.
- [ ] Audit/log/error/debug paths remain content-free and canary-free.
- [ ] Encrypted backup → recovery-only isolated restore → all invariants passes; corrupt/stale/extra/missing packages never activate.
- [ ] Versioned export validates and performs synthetic semantic round trip without secrets/internal paths.
- [ ] At least one old synthetic schema upgrades safely; migration failure leaves no partial active state.
- [ ] Lock/SBOM/license/crypto/secret/synthetic-data/artifact validators and exact final commands pass.
- [ ] Threat matrix maps each implemented control to real evidence and has no unresolved Critical/High implementation finding.
- [ ] One end-to-end test verifies `synthetic create → correct → derive → competing/contradicting evidence → unknown → selective hard deletion → export → encrypted backup → independent-recovery restore → invariant rerun`, including IDs, versions, transaction cutoffs, policy, provenance, and absence—not only exit codes.
- [ ] Frozen historical/research/architecture inputs and unrelated changes are preserved.
- [ ] `REAL_DATA_GATE.status = CLOSED`, automatic opening remains forbidden, and CLI confirms it.
- [ ] Reports distinguish implemented/tested, planned, blocked, residual, and independently unreviewed claims.

If any cryptographic, storage, deletion, migration, backup/restore/export, supply-chain, or threat evidence is not proved, report `BLOCKED` or `PARTIAL_SYNTHETIC_ONLY`; do not soften the criterion. Completion never means production-ready or real-data-safe. Independent cryptographic/key/recovery, threat, privacy-lineage/deletion, and clean-restore reviews belong to E01 and cannot be self-awarded.

## Report and state boundary

Create the detailed F0 artifacts required above and a compact orchestration report at `docs/development/reports/E00.md` from `docs/development/EPIC_REPORT_TEMPLATE.md`. Include exact status, layers implemented, key decisions/deviations with repo requirement links, target versions, commands/results/test counts/skips/failures, Critical/High findings/blockers, material files, branch/HEAD/dirty state, `REAL_DATA_GATE = CLOSED`, and the independent reviews needed next. Do not include chain-of-thought, secrets, recovery material, keys, synthetic content bodies, or absolute home paths.

If implementation and mandatory local validation pass, change only `current_epic.status` in `docs/development/STATE.yaml` from `READY`/`IN_PROGRESS` to `IMPLEMENTED`. If materially blocked, set it to `BLOCKED`. Do not set `ACCEPTED`, append accepted epics, advance E01, commit, or push. E00 acceptance occurs only after the focused Codex checkpoint and any validated fixes.

End with: `F0_STATUS`, concise implemented areas, exact validation summary, blockers/residual risks, state recommendation, and the next action: focused E00 review—not UI, real data, LLM, or feature expansion.
