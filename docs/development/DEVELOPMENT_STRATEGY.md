# PSYCHE OS development strategy

**Status:** implementation operating contract
**Primary implementer:** DeepSeek V4 Pro
**Focused reviewer:** Codex / GPT-5.6 Sol
**Current data state:** `REAL_DATA_GATE = CLOSED`

This manual governs delivery after research convergence. It does not restate the master specification and does not authorize production data. The goal is a small, inspectable loop that spends extra work only where a named failure would be costly.

## 1. Model roles

DeepSeek is the primary implementation engineer. It inspects the current repository, implements one bounded epic, runs targeted validation during development, performs a short diff self-check, runs the required final gate once, and writes a compact epic report.

Codex prepares later epic prompts just in time and reviews only `RISK-H` work, material architecture deviations, or a specific severe anomaly. A Codex checkpoint inspects the changed attack/invariant paths and relevant tests; it is not a project-wide re-audit. Neither model can provide independent clinical, cryptographic, legal, rights, or lived-experience approval where the normative documents require a qualified human reviewer.

## 2. Source-of-truth hierarchy

1. `CONSTITUTION.md`.
2. `docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md`.
3. Explicitly accepted ADR or supersession in `docs/DECISION_LOG.md`.
4. `docs/ROADMAP.md` and `docs/development/EPIC_MAP.md`.
5. The current epic prompt named by `docs/development/STATE.yaml`.
6. Implementation details.

Profile architecture and scientific/safety documents are binding within their subject. A lower layer cannot silently weaken a higher one. An explicitly accepted later ADR may supersede master-spec detail only through the documented supersession rule.

## 3. Epic lifecycle

`PLANNED → READY → IN_PROGRESS → IMPLEMENTED → ACCEPTED`

- `BLOCKED` can replace `IN_PROGRESS` only for a material blocker described by the prompt.
- `READY` means dependencies and the exact implementation prompt exist.
- `IMPLEMENTED` means DeepSeek reports the scope complete and the mandatory local gate passes.
- `ACCEPTED` means objective acceptance criteria pass and any required focused review is complete.
- Update `STATE.yaml` only at epic boundaries. Commit after acceptance, then record the accepted commit and prepare the next epic.

## 4. Risk levels

| Level | Typical work | Required validation | Codex review |
|---|---|---|---|
| `RISK-L` | docs, non-sensitive read-only presentation, mechanical configuration | formatter/lint/typecheck as applicable; behavior test only for a real failure mode | no |
| `RISK-M` | ordinary domain services, CRUD/invariants, metadata, deterministic scoring, non-causal longitudinal analysis, rebuildable projections | targeted unit/integration; project lint/typecheck; migration check if schema changes; `EPIC` gate | no by default |
| `RISK-H` | encryption/keys, recovery/deletion, canonical time/provenance, desktop/provider/import trust boundaries, `NEVER_CLOUD`, LLM/safety, causal methods, gate decision | targeted + integration/adversarial/recovery or migration checks relevant to the boundary; constitutional check; `FULL` gate | yes |

Architecture deviation always escalates. A medium/low epic escalates only when its actual diff crosses a high-risk boundary or a severe unexplained failure makes the classification false.

## 5. Test policy

Add or run a check when it closes a named realistic failure: an invariant regression, security/privacy bypass, wrong result, destructive migration, recovery/deletion failure, contract break, or previously observed defect. Prefer the smallest deterministic test at the boundary that owns the behavior, then one integration path where components can disagree.

Do not add tests only to increase a count, hit an arbitrary coverage percentage, restate type-system guarantees, snapshot unstable formatting, or repeat an equivalent assertion at every layer. Coverage is diagnostic, not an acceptance target. During development run the changed-module checks; at epic completion run the risk-appropriate gate once after targeted checks are green.

Conceptual gates:

- `FAST`: changed-module unit tests plus relevant lint/typecheck.
- `EPIC`: relevant integration tests, project lint/typecheck, and migrations if touched.
- `FULL`: high-risk acceptance, milestone/release, or gate review; includes the relevant security, recovery, deletion, privacy, scientific, and adversarial suites.

E00 establishes the actual locked toolchain and canonical executable commands. Until then, these names describe confidence levels rather than invented scripts.

## 6. Review policy

Standard epic: DeepSeek implements → targeted validation → concise self-check → final `EPIC` gate → report → acceptance.

High-risk epic: DeepSeek implements → targeted/full validation → report → focused Codex review → validated fixes through `FIX_FINDINGS_TEMPLATE.md` → affected checks and final gate → acceptance.

Codex returns `ACCEPT` or `FIX_REQUIRED` with severity-ranked actionable findings. No stylistic bikeshedding, unrelated cleanup, new global research, or repeated review of already accepted unchanged code. Human approvals named by scientific, safety, privacy, rights, or independent-review contracts remain separate evidence.

## 7. Git policy

- Work on a dedicated development branch; do not create a branch for each tiny task.
- Preserve unrelated user changes and inspect the worktree before editing.
- Prefer one clean logical commit per accepted epic; a genuinely large epic may use a small coherent series.
- Commit only after validation and required review. Do not push automatically or rewrite unrelated history.
- `STATE.yaml.git.accepted_commit` records the last accepted epic, not every working commit.

## 8. Context and token policy

Every implementation prompt reads `AGENTS.md`, `CONSTITUTION.md`, and `STATE.yaml`. Add only the exact master-spec sections and architecture documents touched by the epic, plus the prior report when it is a direct dependency. Read scientific governance, safety, threat, source registry, or dossier only for a decision that needs them.

Avoid historical v1, the original research master prompt, unrelated reports, and full source registries by default. Refer to repository paths instead of pasting normative prose. Future prompts are prepared just in time; do not materialize a long queue that will drift.

## 9. Architecture deviation

Use `ARCHITECTURE_DEVIATION_TEMPLATE.md` only when the accepted architecture is materially impractical, unsafe, contradictory, or would require a destructive semantic change. Record minimal evidence and options. DeepSeek continues unaffected work and stops only the blocked portion. A minor implementation choice within the contract belongs in code/tests or the epic report, not a deviation document.

## 10. REAL_DATA_GATE

`docs/architecture/REAL_DATA_GATE.yaml` is the only authority. It stays `CLOSED` throughout this delivery-system task and every implementation epic unless a separate, explicit, signed gate decision satisfies the machine-readable requirements. An application that appears to work, passing synthetic tests, or completion of one model review cannot open it.

While closed, use only clearly fictional package-owned synthetic fixtures not derived from user conversations. No prompt may request personal psychological, medical, family, sexual, legal, messaging, calendar, wearable, life-archive, or other sensitive data. Any gate-open proposal is `RISK-H`, requires the full relevant gate and the independent human reviews required by the gate.

## 11. Next-epic generation

After an epic is accepted, run the coordinator in `docs/prompts/codex/PREPARE_NEXT_EPIC.md`. It reads the compact state, epic map, accepted report, and only directly affected architecture; confirms dependencies and risk; instantiates the lean DeepSeek template; validates it; changes the next epic from `PLANNED` to `READY`; and updates `next_action`. It must not restart research, rewrite the master specification, or perform a repository-wide red team unless an accepted decision explicitly changes the roadmap.
