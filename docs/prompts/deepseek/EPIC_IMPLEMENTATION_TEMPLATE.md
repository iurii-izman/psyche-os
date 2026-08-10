# PSYCHE OS — EPIC {ID}: {NAME}

**Project root:** `C:\Dev\psyche-os`
**Risk:** `{RISK-L | RISK-M | RISK-H}`
**Expected final gate:** `{FAST | EPIC | FULL}`

## Role and outcome

You are the primary implementation engineer for this epic. Deliver one concise outcome: `{OBJECTIVE}`. Work autonomously through implementation and objective validation; do not expand the epic or redesign the project.

## Read first

Always read completely:

- `AGENTS.md`
- `CONSTITUTION.md`
- `docs/development/STATE.yaml`

Then read only these relevant sources:

- `{EXACT_MASTER_SPEC_SECTIONS_OR_FILES}`
- `{RELEVANT_ARCHITECTURE_FILES}`
- `{PREVIOUS_EPIC_REPORT_IF_DIRECT_DEPENDENCY}`

Do not load historical v1, the original research master prompt, the full research dossier, source registry, threat model, or safety/scientific documents unless this prompt explicitly lists them for a current decision.

## In scope

- `{BOUNDED_DELIVERABLE}`

## Out of scope

- `{EXPLICIT_EXCLUSION}`
- Real personal or sensitive data while `REAL_DATA_GATE = CLOSED`.
- Unrelated refactoring, speculative abstractions, or future-epic scaffolding.

## Invariants to protect

- `{ONLY_TOUCHED_CONSTITUTIONAL_OR_ARCHITECTURAL_INVARIANTS}`

## Implementation requirements

1. Inspect the current worktree, dependencies, accepted interfaces, and applicable nested `AGENTS.md` before editing.
2. Preserve unrelated changes. Reuse accepted architecture and existing utilities before adding a dependency or abstraction.
3. `{EPIC_SPECIFIC_REQUIREMENT}`
4. Keep domain decisions deterministic and typed; model/imported output is never policy or evidence.

## Data, migration, security, and privacy

Include this section only for touched concerns:

- `{SCHEMA_COMPATIBILITY_ROLLBACK_RECOVERY_DELETION}`
- `{TRUST_BOUNDARY_POLICY_NEVER_CLOUD_LOGGING_RIGHTS}`
- Use only clearly fictional repository-owned synthetic fixtures not derived from conversations or real persons.

## Validation

Every new check must name the realistic failure it closes. During implementation run the smallest relevant unit/property/integration checks. Before reporting completion run the final `{FAST | EPIC | FULL}` gate once:

```powershell
{EXACT_COMMANDS_FROM_ACCEPTED_TOOLCHAIN}
```

Do not add tests for counts, duplicate an equivalent assertion, or impose an arbitrary coverage target. A skipped security/migration/recovery check is not a pass unless the prompt explicitly defines the profile as out of scope.

## Acceptance criteria

- [ ] `{OBJECTIVE_OBSERVABLE_CRITERION}`
- [ ] `{INVARIANT_OR_FAILURE_PATH_CRITERION}`
- [ ] Targeted and final validation results are recorded exactly.
- [ ] `REAL_DATA_GATE` remains `CLOSED` unless this is a separately authorized gate-decision epic; even then, never open it automatically.

## Work and stop rules

- Inspect before editing; keep scope controlled; do not duplicate the specification in code comments/docs.
- Fix in-scope failures before stopping. Do not commit or push unless this prompt explicitly authorizes it.
- Stop only the blocked portion for a material source-of-truth contradiction, destructive/unrecoverable migration, security/privacy impossibility, unavailable required dependency/license, gate bypass, or appearance of real data/secrets.
- For a material architecture conflict, create a record from `docs/development/ARCHITECTURE_DEVIATION_TEMPLATE.md`; do not silently change higher-authority documents. Continue unaffected work safely.

## Final report and state boundary

Create `docs/development/reports/{ID}.md` from `docs/development/EPIC_REPORT_TEMPLATE.md`. Report only implemented behavior, key files, exact validation results, named blockers/limitations, and deviations—never chain-of-thought or sensitive content.

If all implementation criteria and local validation pass, set only `current_epic.status` in `docs/development/STATE.yaml` to `IMPLEMENTED`. For a material blocker set it to `BLOCKED`. Do not set `ACCEPTED`, append `accepted_epics`, advance the next epic, or commit: those happen after any required review and acceptance.

End with a concise summary, changed areas, validation results, material limitations, and recommended next state.
