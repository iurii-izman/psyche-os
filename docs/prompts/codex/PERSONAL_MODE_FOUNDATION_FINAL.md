# PSYCHE OS — Personal Mode foundation and admission readiness

**Repository:** `C:\Dev\psyche-os`
**Canonical branch:** `main`
**Expected orientation SHA:** `44129765e05cb6f6c69c115a3718e09efc1a58e2`
**Candidate branch:** `codex/personal-mode-foundation`
**Task Contract:** `.ai-dev/contracts/personal-mode-foundation.yaml`
**Risk:** `CRITICAL`
**Current authorization mode:** `FOUNDATION_ONLY`
**Current real-data state:** `CLOSED / LOCAL_PERSONAL NOT_ADMITTED`

This prompt supersedes the attached “PERSONAL MODE ADMISSION OVERDRIVE” text
for execution. The attached text remains an input, not authority. Current
repository truth and the Task Contract win over its dynamic claims.

## 1. Outcome

Deliver the strongest truthful product state allowed by current authority:

1. preserve a reliable, field-usable `SYNTHETIC_LAB`;
2. close all confirmed product-truth, authorization, packaging, response-bound,
   and E11 review-integrity defects in this prompt;
3. enforce requested/effective profile and capability decisions below the
   renderer;
4. make a requested but unadmitted `LOCAL_PERSONAL` visibly and structurally
   unable to open a Personal store, accept content, construct an AI provider,
   receive provider credentials, or inherit excluded workflows;
5. prepare an exact, reviewed design for the remaining Personal persistence
   work;
6. create candidate-bound machine evidence and legitimate human-review intake
   only after the product source is frozen;
7. never manufacture a human review, owner attestation, or `OPEN` result.

`FOUNDATION_COMPLETE_PERSONAL_WRITE_BLOCKED` is a legitimate successful result
for the current authorization mode. It means all unblocked defects are closed
and Personal content remains disabled pending the separately approved schema
and key-rotation work. Do not rename it `READY_FOR_HUMAN_REVIEWS`.

## 2. Authority

Resolve conflicts in this order:

1. `CONSTITUTION.md`;
2. `docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md`;
3. accepted ADRs, especially ADR-003/004/005/007/008/009/010/018/019/020/021/
   022/023;
4. `docs/architecture/REAL_DATA_GATE.yaml`;
5. `docs/architecture/REAL_DATA_GATE_PROFILE.yaml`;
6. `docs/development/STATE.yaml` for current progress truth;
7. `docs/ROADMAP.md` and `docs/development/EPIC_MAP.md` for accepted delivery
   direction, ignoring stale “current” prose when STATE contradicts it;
8. `.ai-dev/contracts/personal-mode-foundation.yaml`;
9. exact source/tests and live `.ai-dev` policy/routing/verification;
10. exact candidate-bound evidence.

Never edit the Constitution, stable gate policy, or stable profile to fit the
implementation. A material conflict requires a focused architecture decision
or deviation; it is not resolved silently by code.

## 3. Non-negotiable safety and integrity

- Synthetic fixtures only. Never enter or copy real personal, psychological,
  medical, sexual/trauma, legal/financial, third-party, message, calendar,
  wearable, or life-archive data.
- `REAL_DATA_GATE` and `docs/development/STATE.yaml.real_data_gate.state` remain
  `CLOSED` in this run.
- A requested profile is not an admitted profile.
- Do not silently fall back from requested `LOCAL_PERSONAL` to
  `SYNTHETIC_LAB`.
- No model may create or complete a human review, impersonate a reviewer or
  repository owner, create a live attestation, select an owner decision, or
  declare `OPEN`.
- LLM output is proposal, not evidence. Screening is not diagnosis;
  correlation is not causation; uncertainty and unknowns remain explicit.
- `NEVER_CLOUD` and reconstructive derivatives cannot reach a provider path.
- Do not change algorithms, Argon2 parameters, HKDF labels/semantics, AES-GCM
  semantics, or invent a second key hierarchy.
- No production dependency, force push, history rewrite, destructive
  migration, or destructive existing-data operation.
- Never weaken a test, scanner, evaluator, profile, assertion, review rule, or
  acceptance criterion to obtain green evidence.
- Preserve `docs/development/proposals/` and `docs/sources/` as unrelated
  user-owned untracked content.
- The current E11 schema/evaluator proves a candidate with synthetic fixtures;
  it does not contain an accepted semantic transition from that proof class to
  admission of `REAL_PERSONAL`. Never treat its current `OPEN` token as Personal
  runtime authority.

## 4. Permission boundary and mandatory approval checkpoint

The current Task Contract authorizes product repairs, fail-closed profile
foundation, E11 integrity repairs, docs, tests, builds, and synthetic probes. It
does **not** authorize schema migration or new crypto/key-rotation lifecycle
design.

Current source makes a working Personal writer impossible without both:

1. compatibility-preserving schema evolution because canonical and Reflection
   `data_mode` constraints permit only `synthetic_only`; and
2. a reviewed crash-safe VMK/database-key rotation design because no accepted
   executable rotation primitive exists.

Therefore this run MUST keep every Personal content write disabled. Before
implementing either item, require all of the following:

- an explicit repository-owner approval that names the migration and
  key-lifecycle scope;
- a focused accepted ADR/design that specifies one VMK, domain-separated keys,
  rotation states, interruption recovery, old-read-key retirement, envelope
  publication, rollback, and loss semantics;
- a successor/amended CRITICAL Task Contract with `migrations: true`, exact
  expected scope, old-schema fixtures, rollback/restore, backward-reader,
  deletion, export, and recovery proof;
- fresh independent review of that design before implementation.

Approval may authorize a non-destructive migration for a fresh isolated
Personal store. It must not authorize destructive conversion or copying of the
existing Synthetic workspace.

The only safe bootstrap option before a separately accepted migration/rekey
design is a brand-new, empty Personal root. Do not open, rekey, envelope,
convert, copy, or import the existing DPAPI-only Reflection workspace. Any
partially created Personal root is a failed bootstrap artifact: quarantine it
without overwriting key/recovery material and keep it unreachable until an
owner-authorized recovery or deletion action.

## 5. Exact profile interpretation

Supported product profiles are exactly:

- `SYNTHETIC_LAB`;
- `LOCAL_PERSONAL`.

Runtime state contains separate:

- `requested_profile`;
- `admission_state`;
- `effective_profile`;
- `data_mode`;
- `capabilities`.

With the gate closed:

```text
requested_profile = LOCAL_PERSONAL
admission_state = NOT_ADMITTED
effective_profile = NONE
data_mode = NONE
personal_content_commands = DISABLED
```

Do not create a third security profile.

`LOCAL_PERSONAL` enables only the boundaries named `ENABLED` in
`REAL_DATA_GATE_PROFILE.yaml`. It excludes attachment/blob writes,
import/parser/untrusted rendering, provider/model/network/cloud/telemetry,
assessment/scoring, longitudinal/N-of-1/intervention workflows, and
professional/external handoff.

Use the stricter Personal route classification:

- allow deterministic Search and session list/open/resume only after valid
  admission and storage readiness;
- disable current Review Hub and Dynamics/Longitudinal;
- disable current Return/Follow-up composition because it is assembled from
  cross-session aggregation; a future narrower façade needs its own proof;
- allow no AI route or command;
- treat user-authored free-text next-step/outcome as reflection only if it has
  no recommendation, protocol, schedule, cross-session comparison, causal or
  effectiveness inference;
- allow only owner portability/preservation export, never E10-style
  professional/audience handoff.

An excluded boundary that is reachable or lacks exclusion proof invalidates the
candidate. It does not become `APPLICABLE` inside this stable profile, and
extra review cannot cure the mismatch.

## 6. Stage 0 — exact orientation and contract

Before editing:

1. `git fetch origin`;
2. record `HEAD`, `main`, and `origin/main`;
3. preserve unrelated work; never reset it;
4. read AGENTS, live `.ai-dev` policy/verification/routing, STATE, stable gate/
   profile, exact ADR/spec ranges, and affected source/tests;
5. use `rg`, then `ast-grep`, then exact ranges;
6. run `uv run python scripts/ai_dev_doctor.py`;
7. create/update the bounded Context Pack and Task Contract;
8. classify repository gates, contract-required proof, and supplemental
   evidence separately before running them.

If canonical main moved, re-ground on the new accepted main and report the
identity change. Never reuse the expected SHA as a claim after it becomes
stale.

## 7. Stage 1 — required product repairs

Close each defect with focused failure-driven tests.

### 7.1 Truthful connectivity and privacy status

Replace ambiguous `network`/`privacy.cloud` with orthogonal fields:

- `inbound_network`;
- `outbound_provider`;
- `cloud_storage`;
- `cloud_disclosure`;
- `telemetry`.

Expected states:

| Runtime | inbound | outbound provider | cloud storage | cloud disclosure | telemetry |
| --- | --- | --- | --- | --- | --- |
| Synthetic + key | `NONE` | `READY_EXPLICIT_E07` | `DISABLED` | `SYNTHETIC_EXPLICIT_E07_ONLY` | `OFF` |
| Synthetic, no key | `NONE` | `NOT_CONFIGURED` | `DISABLED` | `DISABLED` | `OFF` |
| Personal requested/not admitted | `NONE` | `DISABLED_BY_PROFILE` | `DISABLED` | `DISABLED_BY_PROFILE` | `OFF` |

Russian UX must not say “Без сети” when explicit outbound provider use is
available.

### 7.2 Launcher and native smoke

- Launch `psyche-os-desktop.exe`, not `psyche-os.exe`.
- Missing build produces an actionable command.
- Synthetic launcher alone may load `.env.local`; never print the key.
- Personal launcher never reads `.env.local`, forwards no provider credential,
  and only requests `LOCAL_PERSONAL`.
- Use the executable directory as working directory.
- Update stale UIA waits to the durable current Home marker
  `МОЁ ПРОСТРАНСТВО`. Do not alter UI to satisfy a stale oracle.

### 7.3 Tauri command surface and Unicode contracts

- Reconcile Rust handlers, `build.rs`, Tauri capability allowlist, and the TS
  API for Search and AI commands used by Synthetic Lab.
- Apply the correct serde casing to nested AI selection fields.
- Validate source/build/capability/API command-set parity deterministically.
- Use Unicode character counts for user-facing limits where Python/TS define
  character limits; do not reject valid Cyrillic/emoji by Rust byte length.
- Personal capability enforcement remains authoritative even when the command
  exists for Synthetic Lab.

### 7.4 AI proposal semantics

Preserve structured E07 response fields:

```text
status
reflections[]: statement_id, text, supporting_evidence_ids,
               uncertainty, claim_level
counterevidence[]
unknowns[]: unknown_id, uncertainty
questions[]: question_id, unknown_id, text
```

Renderer order:

1. `Наблюдения / рабочие предложения` with text, uncertainty, and supporting
   evidence IDs;
2. `Контраргументы`;
3. `Что остаётся неизвестным` exactly once;
4. `Вопросы`.

No accept-as-truth, apply, automatic save, score, diagnosis, recommendation,
or duplicated unknown uncertainty. Proposal persistence remains none.

### 7.5 Match-centred search excerpt

Use a deterministic, bounded, Unicode-safe excerpt around the first actual
case-insensitive match. Add ellipses truthfully, retain a maximum of 200 Unicode
code points, and add tests for late match, boundaries, repeated match,
Cyrillic, and emoji. No ranking, FTS, vector, embedding, or LLM.

### 7.6 Session authorization and bounded responses

- Replace the misleading “state-changing command” set with one explicit
  command policy covering capability and required session authority.
- `reflection_exploration.get` and every other content-bearing read require a
  valid unlocked session before handler/data load.
- Do not allow renderer composition of a Personal-excluded cross-session
  workflow through generic reads.
- Add bounded pagination/summary responses so a legitimate large session
  cannot exceed the frame limit and terminate the sidecar.
- Oversized output returns a stable content-free error and the process remains
  usable for the next request.

### 7.7 Reflection first-start key publication

The current `exists` then `write_bytes` key path has a concurrent-start race.
Make initial wrapped-key publication exclusive and atomic using existing
filesystem primitives. One durable key wins; a loser either reopens with that
key or fails closed. Never overwrite existing key material silently. This is a
Synthetic daily-driver repair, not Personal recovery readiness.

### 7.8 Export truth

An export that skipped requested tables or exported zero records after a query
failure must not verify as successful. Fail closed on unsupported schema/table,
missing required columns, query failure, count mismatch, or empty output when
the selected source is non-empty. Do not claim this fixes Personal v9
portability; that remains approval-gated.

## 8. Stage 2 — E11 authority and review-integrity repair

Fix the accepted evaluator before generating a successor candidate:

1. `RDG-09`, `RDG-10`, `RDG-11`, and `RDG-12` are always applicable and reject
   `NOT_APPLICABLE_EXCLUDED`.
2. RDG-10 cannot be proved without legitimate independent technical/threat/
   crypto/privacy/deletion reviews required by the enabled boundaries.
3. RDG-11 cannot be proved without a substantive qualified intended-use,
   privacy, legal, and regulatory human review for the actual deployment.
4. A review declaration inside an evaluation is insufficient. Bind every
   completed review to a separately schema-validated result artifact with
   exact boundary/class/source/build/platform, digest, timestamps, expiry,
   reviewer kind, conclusion, findings, and qualification statement where
   required.
5. `CODING_MODEL`, `MODEL_PRE_REVIEW`, `REVIEW_TEMPLATE`, `PENDING`, missing,
   expired, digest-mismatched, candidate-mismatched, or unqualified results do
   not satisfy human review.
6. A repository-native intake tool validates external results and normalizes
   them without upgrading state, inventing reviewer identity, or inventing
   findings.
7. Pre-seal validation refuses missing human results, unresolved Critical/High
   findings/risks, stale evidence, identity mismatch, or unproved always-
   applicable controls.

The mandatory review matrix is exact, not advisory:

| boundary or gate control | required review class |
| --- | --- |
| `canonical_encrypted_store_and_key_recovery` | `independent_crypto_key_recovery` |
| `canonical_encrypted_store_and_key_recovery` | `independent_privacy_deletion` |
| `backup_restore_and_scoped_filesystem` | `independent_recovery` |
| `backup_restore_and_scoped_filesystem` | `independent_privacy_deletion` |
| `desktop_renderer_and_typed_ipc` | `independent_technical_security` |
| `local_archive_and_disposable_retrieval_projection` | `independent_privacy_deletion` |
| `RDG-11 deployment review` | `qualified_intended_use_privacy_legal_regulatory` |

Excluded boundaries require exact exclusion evidence, not substitute reviews.
The final RDG-11 deployment review is mandatory even when every RDG-11 feature
boundary is excluded. A schema that cannot express this matrix truthfully is a
blocking schema defect, not permission to weaken the matrix.

Human provenance is a procedural authority boundary, not something software
can prove from a self-declared string. The validator proves schema, binding,
digest, timestamps, declared reviewer kind/qualification/independence and
finding state. It must not claim to prove that a human authored the record.
Live result files must originate outside the agent run, in an owner-controlled
intake location, and be read back; authenticity/qualification remains an owner
and reviewer responsibility.

Tests may use clearly fictional human fixtures and fictional attestations to
exercise positive logic. No such test object becomes a live artifact.

## 9. Stage 3 — fail-closed runtime profile foundation

Create one repository-owned capability resolver below the renderer. It owns
command authorization and must run before sensitive load, persistence, model
context, provider construction/use, network, or filesystem mutation.

At minimum:

- Synthetic Lab retains accepted current capabilities.
- `LOCAL_PERSONAL/NOT_ADMITTED` exposes status and an explicit action to launch
  Synthetic Lab, but no content entry or content read.
- Python sidecar does not open Reflection/Personal databases, create synthetic
  archive state, seed AI Lab, construct `OpenAIReflectionProvider`, or register
  AI commands for unadmitted Personal.
- Rust validates only enumerated trusted profile intent and repository/evidence
  bindings; renderer cannot supply profile, attestation, repository root,
  filesystem path, environment variable, or provider credential.
- Rust retains `env_clear()` and omits `OPENAI_API_KEY` completely for a
  Personal request regardless of admission result.
- A Personal subdirectory is not created while unadmitted. Synthetic storage
  remains at its existing location.
- Disabled commands return `CAPABILITY_DISABLED` before handler invocation.
- UI renders a dedicated truthful `NOT_ADMITTED` surface and does not mount AI,
  Review, Dynamics, Return/Follow-up, or other content routes.

The current E11 evaluator is **not** a production Personal admission provider:
`candidate.requested_data_class: SYNTHETIC_ONLY` describes fixture execution,
while `REAL_PERSONAL` admission is a different authority claim. Production
Personal must remain `NOT_ADMITTED` until an accepted architecture/evaluator
revision represents both `validation_fixture_class: SYNTHETIC_ONLY` and
`admitted_data_class: REAL_PERSONAL` (or an accepted semantic equivalent) and
binds that decision to the installed build. Never add a weaker boolean “open”
file. A test-only injected admission decision may exercise future capability
transitions with synthetic content, but it must be impossible to select in a
production build and cannot create production authority.

## 10. Stage 4 — package composition and exclusion proof

- Produce a deterministic sidecar composition manifest.
- Explicitly exclude E08 importer/parser/application/adapter modules from the
  Personal-capable package path. Inert migration schema definitions are not an
  enabled importer workflow but must be classified explicitly.
- Prove no importer command/route, assessment workflow, professional handoff,
  attachment write, Personal AI/provider, or Personal longitudinal workflow is
  reachable.
- For a shared binary, code presence alone is not sufficient proof of an
  enabled boundary; constructor/command/credential/transport sentinels must
  prove non-initialization and non-reachability. Where the stable profile says
  “not shipped”, use a profile-specific sidecar/package or fail the candidate.

## 11. Stage 5 — approval-gated Personal persistence work

Do not execute this stage in `FOUNDATION_ONLY` mode.

After the approval checkpoint in section 4, the successor contract must prove:

- one random vault master key;
- DPAPI convenience wrap plus independent existing Argon2id RecoveryWrapper;
- domain-separated database/backup/export keys using accepted labels;
- no secret in persistence, argv, env, logs, renderer storage, telemetry, or
  artifact metadata;
- recovery setup and confirmation before first synthetic Personal-profile
  fixture write;
- compatibility-preserving schema evolution for `real_personal` in a fresh
  isolated Personal root, with no copying/migration of existing Synthetic data;
- exact current-schema encrypted backup, isolated restore, explicit activation,
  failed-restore preservation, wrong-secret failure, and lost-DPAPI recovery;
- owner-only open export round trip for every supported Personal record class;
- deletion dependency closure, non-reconstructive receipt, projection rebuild,
  and truthful backup-expiry/external-copy limitations;
- crash-safe VMK/database-key rotation and restart/fault recovery;
- candidate-scoped plaintext probes across DB/WAL/journal/temp/log/crash/
  package/projection/IPC artifacts.

If any item requires unreviewed cryptographic or migration design, stop this
stage and preserve the fail-closed foundation.

## 12. Stage 6 — Evidence Notebook decision

`DEFER` the Evidence Notebook in this foundation contract. It is a separate
product capability with provenance, versioning, deletion, backup/recovery and
export consequences, not an admission prerequisite. Do not create a new entity
schema merely for it. Existing canonical Source/Report/Observation/Assertion/
Unknown/policy/provenance/version concepts may be reused only in a successor
accepted scope after the Personal persistence stage is authorized and green.

User-facing types are:

- `Запись / сообщение` → attributed Report/source-near record;
- `Наблюдение` → Observation;
- `Рабочее утверждение` → Assertion only on explicit selection;
- `Неизвестное / вопрос` → Unknown.

Never infer an Assertion from a Report. Corrections create successor versions.
Notebook cannot ship without real deletion, export, backup/recovery, and
`NEVER_CLOUD`; Personal Notebook records are never AI-selectable. If the
required authorized write path is absent, defer Notebook explicitly.

## 13. Verification order

Use the smallest tests covering each named failure during edits. Do not run the
full suite after every change. Before product acceptance, run the current
Task-Contract repository gates once, including Python, TypeScript, Rust,
orchestration, research, secret scan, diff hygiene, profile sentinels, E11
negative tests, package composition, launcher probe, and the bounded native
smoke appropriate to the changed risk.

For every failure record:

- proof class: repository-required, contract-required, or supplemental;
- classification: product, test, oracle, environment, or tool/harness;
- exact next action and whether acceptance remains blocked.

Repository-required and contract-required failures cannot be relabelled after
failure. One bounded repair cycle is allowed after independent review; any code
repair invalidates previously generated candidate evidence.

Stop the affected product candidate, rather than merging a partial security
foundation, on any of: authority/evaluator semantic conflict; missing explicit
migration or gate-schema authority; tracked dirty or out-of-scope diff; main
moving after freeze; source/build provenance mismatch; a required schema being
unable to express review truth; unverifiable required human provenance; any
failed required gate; unresolved Critical/High; post-merge regression; or the
same deterministic product failure twice. An unrelated blocked optional item
may be deferred only when it is outside every acceptance criterion and trust
boundary.

Rollback is explicit: preserve `base_sha`, branch/worktree identity, changed
paths, and a checkpoint diff hash; never reset or rewrite shared history. Before
merge, abandon only the candidate branch/worktree while preserving evidence.
After merge, use a reviewed `git revert`, not reset. Never auto-delete a partial
Personal root or overwrite recovery material.

## 14. Product review, publication, and freeze lifecycle

There is exactly one product merge/freeze transition. Keep these identities
distinct:

- `BASE_COMMIT`: accepted starting main;
- `CANDIDATE_COMMIT`: reviewed branch tip containing the immutable product
  tree;
- `MERGE_COMMIT`: final main commit whose product tree must equal the candidate
  product tree (allowing only explicitly identified merge metadata);
- later evidence/report commits, which never redefine the product source.

The lifecycle is:

1. implement on `codex/personal-mode-foundation`;
2. run targeted checks and the final product gate;
3. create a candidate commit;
4. run fresh independent CRITICAL diff/product review against exact base,
   contract, source, tests, and profile authority;
5. one bounded repair is allowed; rerun affected checks and review;
6. only an `ACCEPT` or `ACCEPT_WITH_OPTIONAL_ITEMS` verdict permits commit/push/
   PR and merge under the owner authorization;
7. merge once to current `main`, prove candidate/merged product-tree
   equivalence, and run post-merge validation;
8. freeze that exact `MERGE_COMMIT`; no optional fix, refactor, prompt tweak,
   dependency change, or UI polish to its product tree afterward;
9. build and generate candidate evidence against `MERGE_COMMIT`, never current
   `HEAD`, an obsolete branch SHA, or a later report commit.

If a post-freeze defect is found, invalidate the candidate, create a successor
branch/evaluation, repair, review, merge, rebuild, and regenerate affected
evidence. Never edit a SEALED record.

## 15. Candidate build and RDG evidence lifecycle

Only after final-main freeze:

1. build from a clean detached worktree at exact `MERGE_COMMIT` and produce
   exact Windows executable, sidecar, installer, lock/SBOM/license/dependency/
   secret/build-provenance identities and hashes;
2. hash binary artifacts over raw bytes; text canonicalization such as CRLF
   normalization is forbidden for executable, installer, archive, database,
   image, signature, or other binary identity;
3. satisfy the repository's actual reproducibility policy; one build is not
   `REPRODUCED` if policy requires independent clean builds, and the independent
   build must also start at exact `MERGE_COMMIT`;
4. generate schema-valid candidate-bound deterministic proofs and exact
   exclusion proofs with source/build/platform/path/digest/expiry;
5. keep RDG-01 through RDG-12 statuses exact; RDG-09 through RDG-12 remain
   applicable;
6. generate a new DRAFT evaluation, never mutate the accepted E11 draft;
7. use `requested_data_class: SYNTHETIC_ONLY` for proof execution; no real data
   is needed;
8. classify remaining reasons as machine-fixable, human-review-required,
   owner-attestation-required, authority-blocker, expired, or candidate-
   invalidated.

Evidence/report commits after freeze may add only candidate-bound evidence and
reports. Their `HEAD` is not the source identity. Any product, dependency,
build-script, packaging, schema, evaluator, or prompt change affecting the
candidate returns to implementation, creates a new candidate/merge identity,
and invalidates builds, evidence and reviews.

Machine pre-review is useful but always
`NON_AUTHORITATIVE_MODEL_PRE_REVIEW`. A known Critical/High defect invalidates
the candidate before human review.

## 16. Human review, sealing, and owner decision

Generate candidate-bound packets for every row of the exact matrix in section
8. Inferred equivalence and optional substitution are not allowed.

Templates are `PENDING` intake objects and contain no reviewer identity,
signature, conclusion, or findings. An externally completed human result is
created outside this agent run in an owner-controlled location, then read back
and validated by the intake tool. Distinguish exactly:

- `REVIEW_TEMPLATE`;
- `HUMAN_COMPLETED_REVIEW`;
- `NONAUTHORITATIVE_MODEL_PRE_REVIEW`.

Do not seal while any required review is absent, expired, mismatched,
unqualified, incomplete, or has unresolved Critical/High findings. When all
machine and legitimate human evidence is current, pre-seal validation may call
the repository-owned `seal_evaluation()` to create a new immutable SEALED
record.

A code/build/schema-impacting human finding returns to implementation and
invalidates the candidate lifecycle. Human-result validation can establish
binding and declared provenance, not prove human authorship, independence, or
professional qualification; those remain procedural owner obligations.

Evaluate that SEALED record without attestation. Owner-attestation readiness
requires `CLOSED` with the **only** reason `missing_human_attestation`. Only then
prepare an owner package and an unset template or separate OPEN/CLOSED examples
bound to evaluation ID and sealed digest. Never create the live attestation or
choose the owner's decision.

## 17. Field behavior

Until a legitimate runtime evaluation returns `OPEN`:

- the user may use `SYNTHETIC_LAB` only with fictional/synthetic scenarios;
- the user must not enter any real personal or sensitive information;
- requested Personal mode must show `NOT_ADMITTED` and accept no content.

Even after a future valid Personal `OPEN`, v1 still does not permit AI/provider/
network, Longitudinal/N-of-1, importer, assessments, professional handoff, or
arbitrary blobs.

## 18. Required report

Report exact facts, not aspirations:

```text
STATUS:
  COMPLETE | FOUNDATION_COMPLETE_PERSONAL_WRITE_BLOCKED |
  READY_FOR_HUMAN_REVIEWS | READY_FOR_OWNER_ATTESTATION | BLOCKED

STARTING MAIN / FINAL MAIN
CHANGED FILES / COMMITS / PR / MERGE

PRODUCT REPAIRS
  connectivity truth
  launcher/native ACL/UIA
  session authorization/frame bounds
  AI semantics
  search excerpt
  key publication
  export fail-closed

RUNTIME PROFILE
  requested/admission/effective/data mode
  Python/Rust/renderer/package enforcement
  production bypass: NONE or exact blocker

PERSONAL BYTE LIFECYCLE
  store/encryption/key/backup/recovery/deletion/export/projections per class
  uncovered bytes
  migration/rotation decision

E11 / RDG
  always-applicable enforcement
  review artifact/intake integrity
  RDG-01 through RDG-12 status and exact evidence

VERIFICATION
  exact command, exit code, result, failure classification

CANDIDATE / EVALUATION / HUMAN REVIEW / OWNER GATE
  exact identities and hashes
  DRAFT/SEALED status
  missing legitimate reviews
  REAL_DATA_GATE outcome

FIELD USE
  exact launch commands
  whether real personal information may be entered: YES or NO

NEXT HUMAN ACTION: one concrete action
NEXT ENGINEERING ACTION: one concrete action
```

If any Personal lifecycle or human-authority requirement is missing, the answer
to “may real personal information be entered?” is unambiguously `NO`.
