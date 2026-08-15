# E10 — Strong Review

Fresh strong adversarial review of the E10 candidate on
`codex/e10-professional-handoff`.

- **Reviewed candidate:** `dfc5823ec2dc7ea4cee07a4fd0c2274c73cf0a8e`
  (F1–F9 state, before the F10 transitive-lineage pass)
- **Reviewer runtime observed:** the reviewer reported
  `claude-opus-5[1m]`. This is recorded as reported; DeepSeek V4 Pro was
  **not observably confirmed** and is not claimed as the observed runtime.
- **Review date:** 2026-08-15

## Findings

### G-2 — BLOCKING: E10 policy resolution composes only direct `policy_lineage` parents

`_applicable_export_policy()` in
`src/psyche_os/application/e10_professional_handoff.py` resolves the effective
policy for a disclosed record from the record's own active policy plus only the
**direct** `policy_lineage` parents. The canonical policy authority
(`src/psyche_os/policy/engine.py`) requires **transitive** inheritance: a
node's effective policy is the most-restrictive meet of its own policy and
**ALL** ancestors (`resolve_with_own_policy` / PS-02); `NEVER_CLOUD`
inheritance is transitive; descendants cannot weaken restrictions inherited
from any ancestor.

Consequence: a restrictive grandparent or deeper ancestor can be omitted from
the effective policy, allowing a descendant to become export-eligible when the
complete ancestry would block it. Example that MUST fail closed and remain
restrictive:

```
grandparent: export_rule = block
parent:      export_rule = allow
child:       export_rule = allow
```

The child must NOT become exportable. The same requirement applies to the other
axes already composed by the canonical policy engine (processing_location,
cloud_policy, export_rule, export_audience, and the remaining orthogonal axes).

### LOW — non-blocking: filesystem no-clobber race (accepted residual)

`ReportFileWriter.write()` in `src/psyche_os/adapters/e10_filesystem.py`
performs a check-then-act sequence: `resolved.exists()` → concurrent creation of
the target by another writer → `os.replace(tmp_path, resolved)`. In the window
between the `exists()` check and the `os.replace()`, a concurrently created
target can be silently clobbered by the replace. This is a confirmed
non-atomic no-clobber guarantee and is **accepted as a LOW residual under the
accepted single-user threat model** — no absolute race-free no-clobber behavior
is claimed. It was not fixed in this pass.

## Final disposition

- **G-2:** **FIXED by this pass** (F10 — transitive policy-lineage closure).
  `_applicable_export_policy()` now resolves the complete transitive ancestor
  set before deciding export eligibility; counterevidence uses the same
  resolution; lineage cycle, missing/ambiguous ancestor, and composition
  failures fail closed; a restrictive ancestor at any depth survives into the
  effective policy. Targeted lineage tests A–F added
  (`tests/integration/test_e10_professional_handoff.py`).
- **Filesystem race:** **accepted LOW residual / documented limitation.** See
  "LOW — non-blocking" above and the Known limitations section of
  `docs/development/reports/E10.md`. No absolute race-free no-clobber claim is
  made.
- **Reviewer observed model:** `claude-opus-5[1m]` was reported; DeepSeek V4
  Pro was not observably confirmed.

## Acceptance disposition (2026-08-15)

E10 was **ACCEPTED** at implementation candidate
`6c2ccf75637ef85db42bc62caf206c1c0e736d21` and merged into canonical `main`.
This strong review was the fresh strong independent review substituted for the
unavailable Codex review by explicit architect/user decision. Recorded
truthfully: the reviewer reported its observable runtime model as
`claude-opus-5[1m]`; DeepSeek V4 Pro was requested/configured but was **not
observably confirmed**; Codex did **not** review E10. The original
Codex-review requirement remains a recorded historical contract fact. See
`docs/implementation/E10_ACCEPTANCE_REPORT.md`.
