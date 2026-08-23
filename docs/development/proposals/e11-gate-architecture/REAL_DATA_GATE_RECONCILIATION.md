# Proposed REAL_DATA_GATE Reconciliation

**Status:** `PROPOSED` / `HUMAN_ACCEPTANCE_REQUIRED`
**Applies to:** `docs/architecture/REAL_DATA_GATE.yaml` only after a separate
authorized change.  This is a patch plan, not an applied patch.

## Target shape

`REAL_DATA_GATE.yaml` becomes the stable policy and fail-closed default owner.
Its policy semantics are `fail_closed_default: CLOSED`,
`automatic_opening_forbidden: true`, and `research_convergence_required: true`.
It owns neither a current candidate decision nor a mutable live fact such as
research convergence. The proposed `docs/architecture/REAL_DATA_GATE_PROFILE.yaml`
owns reusable scope. An exact `artifacts/e11/gate-evaluations/<evaluation-id>.yaml`
starts as `DRAFT`, becomes immutable only when `SEALED`, and owns the selected
candidate's evidence status, review/expiry/invalidation state, and the decision
binding for that exact sealed evaluation. `STATE.yaml` remains the accepted-epic
and live research-convergence authority.

The current authoritative gate state is `CLOSED`; this proposal does not change
it. The stable policy's `CLOSED` value is a fail-closed default, not a competing
current-decision owner. No existing `UNSATISFIED` result becomes satisfied through
this reconciliation.

## Current field classification and proposed disposition

| Current field | Classification | Proposed action |
| --- | --- | --- |
| `schema_version` | `UPDATE_FROM_CURRENT_AUTHORITY` | Bump only if the accepted policy schema needs the explicit owner split. |
| `gate_id` | `KEEP` | Retain `PSYCHE-REAL-DATA-GATE`. |
| `snapshot_date` | `REMOVE_AS_STALE_OPERATIONAL_METADATA` | A policy has no snapshot date; dates belong to an evaluation/evidence record. |
| `status` | `REMOVE_AS_CURRENT_DECISION` | Replace with stable `fail_closed_default: CLOSED`; a policy never owns an exact candidate's current `CLOSED`/`OPEN` decision. |
| `research_converged` | `REMOVE_AS_MUTABLE_CURRENT_FACT` | Replace with stable `research_convergence_required: true`; an exact evaluation resolves the actual fact from authoritative `STATE.yaml`. |
| `production_implementation_exists` | `REMOVE_AS_STALE_OPERATIONAL_METADATA` | It is neither a control nor a profile-specific predicate; accepted implementation progression belongs to `STATE.yaml`. |
| `scope.profiles` | `MOVE_TO_PROFILE_DEFINITION` | Replace `all` with exact profile ID/version/digest binding in the profile and evaluation artifacts. |
| `scope.data_classes` | `KEEP` | Stable policy coverage remains, with profile applicability interpreted explicitly. |
| `scope.synthetic_fixtures_allowed` | `KEEP` | Retain synthetic-first rule. |
| `authority.constitution`, `master_spec`, `privacy_security`, `threat_model` | `KEEP` | These are stable policy authorities. |
| `authority.frozen_f0_contract`, `e00_rebaseline` | `REMOVE_AS_STALE_OPERATIONAL_METADATA` | Historical implementation inputs are not current gate authorities. Preserve their history in accepted reports/ADRs. |
| `authority.next_implementation_contract` | `REMOVE_AS_STALE_OPERATIONAL_METADATA` | A gate policy must not direct a stale next epic; `STATE.yaml` owns the next action. |
| `opening_rule` | `KEEP` | Retain `automatic_opening_forbidden: true` and clarify exact profile-definition digest, candidate/provenance, required review, expiry, and a human decision bound to the sealed evaluation digest. |
| `requirements[].id` and `requirements[].control` | `KEEP` | Retain RDG-01..RDG-12 stable controls; clarify applicability predicates where necessary. |
| `requirements[].state` | `MOVE_TO_CANDIDATE_INSTANCE` | A result is valid only for an exact evaluation. Until then, no result is implied. |
| `requirements[].evidence` | `MOVE_TO_CANDIDATE_INSTANCE` | Bind evidence IDs, raw artifacts, timestamps, expiry, reviews and invalidations to the exact evaluation. |
| `pre_real_data_blockers` | `MOVE_TO_CANDIDATE_INSTANCE` | Retain only active candidate-relevant findings/evidence references there; do not preserve historical E01 deferrals as current facts. |
| `regression_triggers` | `UPDATE_FROM_CURRENT_AUTHORITY` | Keep and expand as the stable invalidation policy listed below. |
| `current_decision` | `REMOVE_AS_POLICY_OWNED_STATE` | The exact evaluation/decision instance owns a candidate decision only after a human record binds its sealed digest; absent valid instance defaults closed. |

## Evaluation lifecycle and RDG status migration rule

Each exact evaluation follows one lifecycle:

`DRAFT` → deterministic final validation → `SEALED` → human decision bound to
the sealed evaluation digest.

A `DRAFT` may be updated while candidate evidence is collected, applicability is
resolved, required reviews are added, and incomplete metadata is corrected. It
can never support `OPEN`. Finalization computes/verifies the exact evaluation
identity and digest and produces a `SEALED` evaluation. After sealing, no
evidence, review, RDG status, candidate identity, profile binding, or
applicability may be changed in place.

The human decision is an immutable record logically belonging to the exact
evaluation/decision instance, but separate from the sealed evaluation bytes. It
must name `evaluation_id` and `sealed_evaluation_sha256`; this binds the decision
without permitting a post-seal edit. Any new evidence, expiry, regression, new
review, changed applicability, changed RDG status, build change, or new decision
requires a new evaluation ID, optionally with `supersedes` lineage.

All twelve current entries are `UNSATISFIED` with null evidence.  The current
policy file must not carry those as timeless candidate results.  On initial
migration, each starts `UNKNOWN_OR_INCOMPLETE` in a `DRAFT` exact evaluation only
after the profile/build is selected. If no valid sealed evaluation and bound human
decision exist, the policy default is simply `CLOSED`.

| Requirement | Proposed initial exact-candidate disposition | Why no `SATISFIED` is assigned now |
| --- | --- | --- |
| RDG-01 | `UNKNOWN_OR_INCOMPLETE` | E01 evidence was for a different synthetic database-only build/profile; general blob scope was deferred. |
| RDG-02 | `STALE_OR_EXPIRED` if E01 evidence is cited; otherwise `UNKNOWN_OR_INCOMPLETE` | Recovery proof binds E01's accepted/repair commits and synthetic profile, not the future candidate. |
| RDG-03 | `STALE_OR_EXPIRED` if E01 evidence is cited; otherwise `UNKNOWN_OR_INCOMPLETE` | Isolated restore evidence must be rerun for the exact release/platform. |
| RDG-04 | `UNKNOWN_OR_INCOMPLETE` | No exact candidate-wide deletion/projection/backup-expiry evidence has been evaluated. |
| RDG-05 | `UNKNOWN_OR_INCOMPLETE` | Migration/export proof must include the selected build and enabled storage/projection scope. |
| RDG-06 | `UNKNOWN_OR_INCOMPLETE` | Plaintext and filesystem/log/crash/package scope must match the actual candidate. |
| RDG-07 | `UNKNOWN_OR_INCOMPLETE` | `NEVER_CLOUD` proof and enabled/disabling boundaries must be candidate-specific. |
| RDG-08 | `UNKNOWN_OR_INCOMPLETE` | An excluded importer may make its import predicate N/A only after exclusion proof; enabled desktop rendering still requires its applicable proof. |
| RDG-09 | `UNKNOWN_OR_INCOMPLETE` | The F0 SBOM is historic; current lock/SBOM/license/provenance/reproducibility evidence is E11 work. |
| RDG-10 | `UNKNOWN_OR_INCOMPLETE` | E01 independent human crypto/privacy/recovery review remains required; no exact candidate review is recorded. |
| RDG-11 | `NOT_PROVED` when professional/clinical/distribution scope is enabled; otherwise `UNKNOWN_OR_INCOMPLETE` | E10 records qualified legal/privacy/clinical/human-factors review as pending, and actual deployment review remains unselected. |
| RDG-12 | `UNKNOWN_OR_INCOMPLETE` | Synthetic acceptance, fault, recovery, deletion and usability proof must cover the selected candidate. |

`NOT_APPLICABLE_EXCLUDED` is permitted only inside a candidate evaluation after
the evaluator proves the entire control predicate is excluded.  It is never a
default replacement for one of the entries above.

## Stable invalidation policy to retain/update

The accepted patch should retain the existing triggers and make the following
explicit: crypto/keys/storage/schema/migration/backup/recovery/filesystem;
desktop renderer/IPC/webview; importer/parser/quarantine/rendering/projection;
provider/model/network/prompt/policy/safety; assessment/longitudinal/N-of-1 or
professional/clinical/research workflows; sync/mobile/sharing/multi-user or
distribution; dependency/lock/SBOM/license/build/package/platform changes;
intended-use/legal/jurisdiction changes; source/retraction impacts; expiry or
reproduction failure; and any incident or Critical/High finding.

The policy must specify that an incident or new Critical/High finding immediately
closes the affected profile.  Reopening needs fix/retest/current evidence and
the required independent and human reviews; no user consent or model statement
can bypass this.

## Required evaluation-instance checks

The later validator must reject an `OPEN` decision unless all of these hold:

1. the evaluation is `SEALED`; its profile path/ID/version/source-commit and
   externally recorded `profile_definition_sha256` verify against the exact
   profile-file bytes; and exact candidate source/build/platform/lock/SBOM/
   artifact identities are present and verify;
2. every RDG control is explicitly applicable or exactly
   `NOT_APPLICABLE_EXCLUDED`, and every applicable control is
   `PROVED_FOR_CANDIDATE`;
3. raw evidence, producer/reviewer, timestamps, expiry, regression sequence,
   findings, and reproducibility result verify for the exact binding;
4. all applicable independent/qualified reviews are present, current, and in
   scope; and
5. the authorized human gate-decision record is present, current, identifies its
   role/method/scope, and binds this exact `evaluation_id` and
   `sealed_evaluation_sha256`.

Any mismatch, absence, contradiction, expiry, unsupported platform, stale
evidence, failed reproduction, unresolved Critical/High finding, or unknown
scope returns `CLOSED`.

The stable profile never self-stores a digest of its own complete bytes. The
exact evaluation computes SHA-256 over the exact profile-file bytes and records
the resulting `profile_definition_sha256` externally. A changed profile file,
including a change without a version update, causes that binding to fail closed.

## Non-goals of the reconciliation

- Do not edit accepted ADRs, `STATE.yaml`, or historical acceptance reports.
- Do not manufacture a current release manifest, SBOM, human review, or
  signature from E01--E10 acceptance evidence.
- Do not create an E11 implementation prompt, mark E11 ready, or decide `OPEN`.
