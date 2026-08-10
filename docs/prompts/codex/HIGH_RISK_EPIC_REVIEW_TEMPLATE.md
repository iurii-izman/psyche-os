# PSYCHE OS — focused high-risk review for epic {ID}

Review the implemented `{ID}` diff for acceptance. This is a checkpoint, not a repository-wide security scan or new research cycle.

## Read

- `AGENTS.md`, `CONSTITUTION.md`, and `docs/development/STATE.yaml`.
- The `{ID}` section of `docs/development/EPIC_MAP.md`.
- `docs/development/reports/{ID}.md`.
- The current diff/commits and only the normative sections named by the epic.

## Review focus

1. Trace each changed high-risk boundary and acceptance criterion to implementation and executable evidence.
2. Check for constitutional/spec conflicts, unsafe fallback, misleading pass/security/clinical claims, migration/deletion/recovery regressions, and synthetic-only/gate bypass.
3. Inspect relevant tests and rerun the smallest commands needed to validate doubtful paths. Do not demand arbitrary coverage or duplicate tests.
4. Report only actionable correctness, security, privacy, scientific/safety, durability, or acceptance-evidence issues. No style bikeshedding, speculative refactors, or unrelated cleanup.
5. Do not claim to replace independent clinical, cryptographic, legal, rights, privacy, or lived-experience approval.

## Output

Return exactly one verdict:

```text
ACCEPT
```

when the epic's code/evidence satisfies its acceptance boundary, or:

```text
FIX_REQUIRED
```

followed by severity-ranked findings. Each finding must name the affected file/line or evidence artifact, concrete failure/impact, relevant invariant, and smallest credible fix/test. If accepted, state the exact validation reviewed and remaining non-blocking residual limitations.

Never open `REAL_DATA_GATE` as a side effect of review.
