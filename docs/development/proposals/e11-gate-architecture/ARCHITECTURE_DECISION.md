# E11 Candidate Profile and REAL_DATA_GATE Architecture

**Status:** `PROPOSED` / `HUMAN_ACCEPTANCE_REQUIRED`
**Scope:** Architecture only; no gate decision, release decision, or real-data admission is made by this proposal.
**Grounded main:** `39c36e365e9bc0228651747304a8a612af9ae4ab` (also `origin/main` when inspected on 2026-08-21)

## Model observability

No configured/requested/effective runtime-model evidence is asserted for this
review.  The repository and task environment inspected here do not supply a
verifiable effective-model attestation.  This proposal is therefore a coding-model
proposal only and cannot satisfy an independent-review or human-signature role.

## Problem

`docs/architecture/REAL_DATA_GATE.yaml` currently places durable control policy,
an old repository snapshot, candidate scope, historical blockers, requirement
states, and a former next action in one document.  Its `scope.profiles: ["all"]`
does not identify a security/operational configuration, and the document cannot
say which exact build/platform/evidence package a future decision concerns.
This is incompatible with the Master Spec requirement that the gate be evaluated
for an exact build/platform/profile and that an opening be dated, signed, and
expiring.

The necessary correction is semantic, not an assertion that E02--E10 acceptance
satisfies any real-data control.  The gate remains `CLOSED` until a later,
authorized evaluation proves every applicable requirement for one exact candidate.

## Authorities and verified conflicts

- Constitution C-13 and C-20 prohibit real-data admission until encryption,
  recovery, integrity, and every gate control pass.
- Master Spec §25 and Privacy/Security Model §16 require an exact
  build/platform/profile, dated evidence, review, signature, and expiry.
- E11's accepted plan requires exact build/profile, enabled boundaries, current
  independently reviewed evidence, and a signed authorized decision; it rejects
  automatic opening and hidden expired/failed evidence.
- `STATE.yaml` is current for epic progression (`E10 ACCEPTED`, `E11 PLANNED`),
  whereas the gate file still says that production implementation does not exist
  and points to E02 as the next implementation contract.  This is a material
  freshness conflict, not a reason to discard either source: `STATE.yaml` owns
  accepted-epic progression; the gate file remains the policy owner until an
  accepted reconciliation.
- E01 accepted evidence is for the `synthetic-database-only` Windows profile and
  its accepted/repair commits, not the current candidate.  It is useful source
  material only.  It cannot prove a later candidate, even while its own dated
  evidence is unexpired.
- E07 is an accepted *synthetic-only* optional provider slice; E08 is an accepted
  bounded importer implementation; E10's professional handoff retains
  `PENDING_QUALIFIED_REVIEW` items.  Acceptance of those epics does not enable
  them in a real-data candidate or complete RDG review.

No higher authority contradicts a profile definition or an exact evaluation
record.  Authority does not name a particular human gate signer or prescribe a
cryptographic signature scheme.  This proposal therefore makes an identifiable,
authorized human decision record mandatory and fail-closed, without inventing a
person, a PKI, or a new service.

## Options evaluated

| Option | Authority and binding | Staleness/fail-closed result | Cost | Decision |
| --- | --- | --- | --- | --- |
| A. Extend `REAL_DATA_GATE.yaml` only | One file would hold policy, profile, exact build, evidence and decision. | Possible, but its current mixed lifecycle already caused stale operational claims; a reusable profile would be rewritten for every build. | Fewest paths, but poor audit separation. | Rejected. |
| B. Stable policy + one versioned profile definition + one exact evaluation instance | Policy stays in `REAL_DATA_GATE.yaml`; the profile is versioned in one architecture file; a release evidence file binds all volatile facts. | Exact profile/build binding is mandatory; stale/unknown evidence cannot become green by editing policy. | Two small new artifact types; no runtime dependency. | **Chosen.** |
| C. Registry/service/attestation platform | Could automate more workflow. | Does not improve the governing evidence and creates new operational trust boundaries. | Disproportionate for a solo/local project. | Rejected. |

## Chosen architecture

Use three distinct concepts with deliberately narrow owners:

1. **Stable gate policy** defines controls, opening invariants, status vocabulary,
   applicability rules, expiry and invalidation rules.  Its stable semantics are
   `fail_closed_default: CLOSED`, `automatic_opening_forbidden: true`, and
   `research_convergence_required: true`; it never asserts a current
   profile/candidate decision or a live research-convergence fact.
2. **Stable profile definition** defines one explicit, versioned operational
   scope.  It states what is enabled, disabled, excluded, or unavailable and
   which trust boundaries and RDG predicates are applicable.  It contains no
   build SHA, artifact digest, PASS claim, signature, or mutable evidence state.
3. **Exact candidate evaluation/decision instance** starts as a mutable `DRAFT`
   release-evidence record and is immutable only after it is `SEALED`.  It binds
   one profile definition version and digest to an exact source and
   build/platform/artifact/evidence/review tuple.  Its sealed identity and any
   human decision bound to that identity are the only location allowed to claim
   a `CLOSED`/`OPEN` decision for that candidate.

This is intentionally not a profile registry, database, daemon, remote
attestation system, or production dependency.  A future accepted change adds
one stable profile file and a versioned evaluation artifact only when a candidate
exists.  Git history plus the recorded content digest preserves old definitions.

### Canonical owners after acceptance

| Subject | Canonical owner | Rule |
| --- | --- | --- |
| Stable gate policy and global fail-closed default | `docs/architecture/REAL_DATA_GATE.yaml` | Owns RDG control definitions, vocabulary, invalidation rules, `fail_closed_default: CLOSED`, `automatic_opening_forbidden: true`, and `research_convergence_required: true`; no current candidate decision or candidate PASS fields. |
| Stable profile definition | `docs/architecture/REAL_DATA_GATE_PROFILE.yaml` | Owns one versioned profile's intended use, platform envelope, capability/boundary inventory, exclusions, and RDG applicability predicates. |
| Exact candidate/build evaluation | `artifacts/e11/gate-evaluations/<evaluation-id>.yaml` | Binds `profile_path`, `profile_id`, `profile_version`, `profile_definition_sha256`, and `profile_source_commit` to source, build, runtime/platform, lock/SBOM, artifacts, and raw evidence references. |
| Per-RDG evidence status and currentness | The same exact evaluation instance | Status is valid only for that evaluation's candidate/profile binding. |
| Signed decision | The same exact evaluation/decision instance | An authorized human decision record binds `evaluation_id` and `sealed_evaluation_sha256`; it cannot mutate the sealed evaluation bytes. An absent or unverifiable record is not a signature. |

`STATE.yaml` continues to own accepted epic progression and live research
convergence.  An evaluation resolves the latter from its authoritative source;
an accepted epic report or artifact remains evidence input, never a gate result
by implication.  In the absence of a valid sealed evaluation plus a bound human
decision, the applicable gate result is fail-closed `CLOSED`.

## Profile semantics

A profile is an explicit security and operational scope, not a label such as
`all accepted epics`.  A stable profile must contain:

- `profile_id`, `profile_version`, intended use, supported operating-system and
  runtime envelope;
- a complete inventory of the enabled, disabled, excluded, and unavailable
  capability/trust boundaries; and
- for each materially relevant boundary, its implementation-enforcement state,
  applicable RDG controls, review classes, and reason/reference.

The stable profile does **not** store a SHA-256 of its own complete serialized
bytes.  The exact evaluation computes SHA-256 over the exact profile-file bytes
and records that external binding as `profile_definition_sha256`, together with
the profile path, ID, version, and source commit.

The four capability states have only these meanings:

| State | Meaning | Gate consequence |
| --- | --- | --- |
| `ENABLED` | Part of the candidate's intended executable/configuration scope. | Every relevant control, evidence, review and regression trigger applies. |
| `DISABLED` | Present in the candidate but deliberately off by a stated enforceable configuration. | It is not treated as absent until evaluation proves the disabling mechanism and no bypass; otherwise affected controls remain applicable. |
| `EXCLUDED` | Not shipped, reachable, or authorized in this profile. | A control may be `NOT_APPLICABLE_EXCLUDED` only when its whole applicability predicate is excluded. |
| `UNAVAILABLE` | Not implemented or intentionally fails closed at the boundary. | Not enabled; evidence must show fail-closed unavailability if it is relevant to the candidate. |

`UNKNOWN` is not a capability state.  It is the required pre-evaluation
implementation/evidence state when the proposal cannot truthfully establish the
candidate configuration.  Unknown boundary state blocks evaluation and therefore
blocks opening.

The accompanying proposed first-profile definition deliberately does not claim
that current code is enabled for real data.  Its boundary states describe the
proposed release scope; every entry has `candidate_implementation_state: UNKNOWN`
until a later exact candidate evaluates enforcement.

## Exact evaluation lifecycle and RDG semantics

An exact evaluation has one lifecycle:

`DRAFT` → deterministic final validation → `SEALED` → human decision bound to
the sealed evaluation digest.

While `DRAFT`, the evaluation may be updated to collect candidate evidence,
resolve applicability, add required reviews, and correct incomplete metadata. A
`DRAFT` can never support `OPEN`. Finalization deterministically validates the
complete draft, computes/verifies its exact evaluation identity and digest, and
marks the evaluation `SEALED`.

After `SEALED`, the evaluation content is immutable: no evidence, review, RDG
status, candidate identity, profile binding, or applicability may be changed in
place. The authorized human decision is a distinct immutable record logically
belonging to the same evaluation/decision instance; it names the exact
`evaluation_id` and `sealed_evaluation_sha256`. It therefore binds the decision
without editing the evaluated content. A missing, unverifiable, expired, or
mismatched decision record is fail-closed `CLOSED`.

Any build change, evidence refresh or expiry, regression, new review, changed
applicability, changed RDG status, or new decision requires a new evaluation ID.
The new instance may record `supersedes: <previous-evaluation-id>`, but never
alters the prior sealed evaluation or its decision binding.

An evaluation instance must include at least:

- an opaque `evaluation_id`, lifecycle state, and date; a `DRAFT` has no
  `OPEN` decision;
- profile path, ID, version, `profile_definition_sha256`, and profile source
  commit, where the SHA-256 is over the exact profile-file bytes;
- full source commit and clean-tree identity; build recipe/toolchain/runtime and
  supported OS/architecture identity; lock-file hashes, SBOM identity, output
  artifact hashes, and reproducibility result;
- a boundary inventory copied from the bound profile with the exact enforcement
  evidence for this build;
- an RDG-01 through RDG-12 entry with applicability, status, evidence IDs,
  evidence producer/reviewer, timestamps, expiry/currentness, raw-result
  references, and regression/invalidation record;
- review attestations, the `SEALED` evaluation digest, and an authorized-human
  decision record bound to that digest, including role class, identity/method
  reference, date, scope, and expiry.

The minimum RDG status vocabulary is:

| Status | Meaning | May support `OPEN`? |
| --- | --- | --- |
| `PROVED_FOR_CANDIDATE` | Exact candidate/profile/platform binding, raw evidence, required review, no expiry, and no invalidation all verify. | Yes, if applicable and all other opening conditions hold. |
| `NOT_PROVED` | Required evidence was run and failed, contradicted, or is missing a mandatory proof. | No. |
| `NOT_APPLICABLE_EXCLUDED` | The profile explicitly excludes the entire boundary predicate, and the evaluation proves the exclusion. | Only for that truly inapplicable control. |
| `STALE_OR_EXPIRED` | Evidence is from a different binding, is past expiry, or has an unclosed regression trigger. | No. |
| `UNKNOWN_OR_INCOMPLETE` | Scope, applicability, evidence, review, or provenance cannot be established. | No. |

Existing `UNSATISFIED` gate entries migrate as `UNKNOWN_OR_INCOMPLETE` unless a
future evaluation has actually tested and failed that candidate, in which case
they become `NOT_PROVED`.  A mixed control is not N/A merely because one of its
sub-boundaries is excluded.  For example, excluding an importer does not make
desktop rendering, supply-chain, recovery, privacy, or intended-use controls
inapplicable.

An exact build SHA mismatch makes prior evidence `STALE_OR_EXPIRED` for the new
candidate, even where a source-file digest happens to match.  Raw test material
may be cited and revalidated, but a fresh candidate-bound evidence record is
required.  Missing, contradictory, future-dated, or reviewer-less evidence is
`UNKNOWN_OR_INCOMPLETE`, never inferred green.

## Evidence, expiry, and regression

Evidence is valid only while all of its candidate/profile/platform/boundary/RDG
bindings, content hashes, producer and reviewer references, timestamps, expiry,
and regression sequence match the evaluation instance.  The instance must record
the effective expiry, not merely an evidence creation date.  An expired artifact
does not remain partially green.

The policy must invalidate affected evidence on any of the following. The prior
sealed evaluation remains historical but cannot support `OPEN`; a new evaluation
must resolve the affected candidate to `CLOSED` pending a scoped rerun and
required review:

- crypto, keys, encrypted storage, migrations, schema, deletion, backup,
  recovery, filesystem/path, or plaintext-handling changes;
- desktop renderer, IPC, webview, parser, importer, quarantine, projection, or
  local retrieval changes;
- provider/model/network/prompt/policy/safety change or enabling of cloud;
- professional, clinical, research, assessment, longitudinal, N-of-1,
  distribution, sharing, sync, mobile, multi-user, jurisdiction, legal, or
  intended-use change;
- dependency, lock, SBOM, license, signing, build provenance, packaging, or
  supported-platform/runtime change;
- security/privacy/safety incident, source retraction affecting a boundary, or
  a new Critical/High finding; and
- expiry of evidence, review, decision, or a failure to reproduce the recorded
  candidate.

An incident or new Critical/High finding closes the affected profile immediately;
no temporary user consent, model review, or waiver can retain it as open.

## Human authority boundary

Coding-model output is a proposal and cannot supply source evidence, independent
technical review, qualified review, or a human signature.  The evaluation must
separate these role classes:

1. coding-model review (non-authoritative assistance only);
2. independent technical/security review, including the crypto/key/recovery,
   threat, privacy-lineage/deletion, clean restore, and enabled parser/import
   reviews required by the applicable boundary;
3. qualified domain/legal/privacy/clinical/safety/human-factors review when the
   profile's intended use or enabled capability requires it; and
4. an authorized human gate decider whose decision binds the exact sealed
   candidate evaluation digest.

Current authority requires reviewer-signed, authorized roles but does not define
the gate-decider identity class or signature mechanism.  The future schema must
make either absent, unverifiable, expired, conflicted, or out-of-scope role
attestation fail closed.  Human acceptance of this proposal must define the
minimal accepted decision role and signature/recording method before any `OPEN`
decision is possible.

## Rejected shortcuts

- Do not keep `profiles: ["all"]`, infer enablement from accepted epics, or let
  implementation acceptance update RDG status automatically.
- Do not put a release SHA or self-referential profile-file digest in the
  reusable profile definition, or make a profile mutable without a version and
  an externally verified evaluation digest.
- Do not grant N/A to a partially relevant control, carry an expired/mismatched
  artifact as green, or use a model's review as a human authorization.
- Do not add an online workflow engine, attestation service, database, or PKI
  hierarchy.  Versioned YAML plus deterministic validation is sufficient.

## Migration and reconciliation plan

After explicit human acceptance, perform a separate, authorized bounded change:

1. Create the accepted stable profile file from the proposal and validate its
   schema/YAML.
2. Reconcile `REAL_DATA_GATE.yaml` according to
   `REAL_DATA_GATE_RECONCILIATION.md`: retain policy; remove stale snapshot and
   former next-action claims; move candidate facts, RDG states, evidence, and
   decision/signature fields out of the policy file.
3. Add a `DRAFT`, `UNKNOWN_OR_INCOMPLETE` evaluation for a specifically selected
   candidate only when its exact build exists. Finalize it deterministically as
   `SEALED` before an authorized human decision binds its sealed digest. Do not
   manufacture PASS states from accepted-epic reports.
4. Add deterministic validation that rejects an `OPEN` decision unless all
   applicable controls, bindings, currentness, reviews, and human decision data
   verify; and rejects an N/A entry without an exact excluded-boundary proof.
5. Run the authorized E11 preparation again.  E11 remains unprepared until this
   architecture is accepted and the gate artifact is reconciled.

## Self-falsification

| Counterexample | Required result under this proposal |
| --- | --- |
| Accepted code capability is disabled in the profile. | Not enabled; the evaluation must prove its disabled/unavailable enforcement before it can affect applicability. |
| Evidence is from a prior build SHA. | `STALE_OR_EXPIRED`; fresh candidate-bound evidence is required. |
| Provider/model boundary changes. | Affected profile closes; provider/safety/currentness evidence and reviews rerun. |
| Professional handoff exists but qualified reviews are pending. | `NOT_PROVED`/`UNKNOWN_OR_INCOMPLETE` for applicable intended-use review; no open decision. |
| Required evidence expires. | Status becomes `STALE_OR_EXPIRED`; candidate decision is `CLOSED`. |
| A new High finding appears after green. | Affected profile immediately closes pending fix, evidence rerun, and review. |
| Two profiles share evidence. | Reuse is invalid unless each instance carries exact profile digest/boundary/platform binding and validates it; otherwise stale. |
| Candidate cannot be reproduced. | RDG-09 and the overall decision are not proved; gate remains closed. |
| A requirement is N/A while its boundary is enabled. | Validator rejects it; status must be applicable and non-green until proved. |
| A model claims a human signature role. | No authorized human record exists; decision cannot open. |
| Stable policy has `fail_closed_default: CLOSED`; a valid exact evaluation later has an `OPEN` decision. | No conflict: the policy has no current candidate decision; the bound sealed evaluation/decision instance is the sole current decision owner for that candidate. |
| A new evidence artifact appears for a `SEALED` evaluation. | Do not edit it; create a new evaluation ID, optionally linked by `supersedes`, and re-evaluate fail closed. |
| A human decision references E1 and E1's evaluated bytes change. | Its `sealed_evaluation_sha256` no longer verifies, so the decision is invalid and cannot support `OPEN`. |
| Profile v1.2 bytes change without a version update. | The evaluation's external `profile_definition_sha256` mismatches, invalidating the candidate binding and keeping it closed. |
| No evaluation exists. | No decision exists; `fail_closed_default: CLOSED` applies. |

All ten cases remain fail closed.  No counterexample yields a false `OPEN` state.

## Questions requiring human acceptance

1. Accept Option B and the three canonical owners above.
2. Accept the proposed first local/offline candidate profile scope, including its
   explicit exclusions, as a definition to be evaluated rather than a claim that
   it is currently enabled.
3. Accept the five RDG statuses, exact-binding/currentness rule, and mandatory
   invalidation behavior.
4. Define the authorized human gate-decider role and acceptable local signature
   or attestation-record method; confirm the required qualified-review classes
   for the first actual profile.

No authoritative architecture has changed.  `REAL_DATA_GATE` remains `CLOSED`.
