# PSYCHE OS development strategy

**Status:** current operating contract
**Operating mode:** `PRODUCT_DEVELOPMENT`
**Current data state:** `REAL_DATA_GATE = CLOSED`

The research foundation, E00–E11 delivery sequence, and Personal Mode v1 are accepted historical work. No epic or implementation prompt is currently active. This contract governs the next bounded product increment without weakening the constitutional safety floor.

## Authority

1. `CONSTITUTION.md`.
2. `docs/PSYCHE_OS_MASTER_SPEC_v2.1_PRODUCT_REORIENTATION.md`, with the retained v2.0 foundation specification for nonsuperseded scientific and operational contracts.
3. Accepted ADR or supersession in `docs/DECISION_LOG.md`.
4. `docs/ROADMAP.md` and `docs/development/EPIC_MAP.md`.
5. The active Task Contract.
6. Implementation detail.

## Default delivery lane

One writer uses a short Task Contract, implements a coherent user-facing increment, runs targeted checks, runs one risk-appropriate final gate, obtains independent review only when a concrete trigger applies, merges, and stops. A normal deterministic failure is localized, repaired minimally, and retested inside the same Task Contract.

Risk follows the changed invariant and enabled boundary, not the directory name. Docs-only, status-only, and test-only deltas remain low when they preserve semantics. Ordinary cross-module product work is medium. A bounded storage/security fix that preserves accepted architecture is high when it exercises a load-bearing invariant, but does not automatically require an architecture restart or human approval.

## Boundary lane

Use stronger deterministic proof and focused architecture confirmation for a new or materially changed trust boundary, crypto/key behavior, recovery integrity, irreversible migration, permissions/filesystem expansion, production network/provider boundary, real-data admission, or core privacy/security architecture change. Human approval is required only for an action named by `.ai-dev/policy/approvals.yaml`; explicit Task Contract pre-authorization counts.

Independent review is triggered by that changed boundary/invariant, a task-contract requirement, a high-risk delta where independent falsification materially improves confidence, or a repair that invalidates the reviewed proof. A sensitive path, a scary word in documentation, optional lint/type debt, or a new packaging SHA is not a review trigger.

## Acceptance and closeout

One coherent candidate has at most one candidate-wide independent review. A bounded review finding gets one writer repair; rerun the failed oracle and directly coupled regressions, then recheck only the repair delta. Do not restart candidate-wide review unless scope, authority, boundary, or load-bearing evidence materially changed.

`ACCEPT` and `ACCEPT_WITH_OPTIONAL_ITEMS` close core implementation. Record optional items and stop. Status/docs cleanup gets targeted checks; packaging is closeout and a candidate commit SHA is the normal review identity. A narrow proven regression reruns only invalidated proof. Reopen full acceptance only for direct regression evidence, relevant changed code, invalidated load-bearing proof, changed authority, or materially expanded risk.

## Safety and data

Use only clearly fictional synthetic fixtures. `NEVER_CLOUD` and reconstructive derivatives remain out of cloud context; imported content remains untrusted. The real-data gate can open only through its separate authoritative, human-governed decision process. No accepted product work or process change opens it.

## Control-plane maintenance

The AI Dev OS is stable and exception-only. Change it only for a required gate, a material invariant, or a **REPEATED + OBSERVABLE + MATERIAL + ACTIONABLE** bottleneck. Do not build a new process layer from a single awkward task, optional polish, or benchmark curiosity.
