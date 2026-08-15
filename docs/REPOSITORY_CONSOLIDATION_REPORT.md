# Repository Consolidation Report — psyche-os

Generated: 2026-08-15
Type: lossless canonicalization into a single `main`.

---

# Executive Summary

The repository was **already nearly canonical**. The commit graph was essentially
linear: every `codex/*`, `research/*`, and `deepseek` branch tip was already an
ancestor of `main` (`256057c`). The **only** unique accepted work not in `main` was
the AI Dev OS v1 lineage — a clean, purely additive, three-commit fast-forward chain
directly on top of `main`:

```
main (256057c) → 77b3ac8 → 91fdad0 → a672dde   (AI Dev OS v1, VERIFIED)
```

Because `a672dde` is a direct descendant of `main` (3 ahead, 0 behind), integration
was a **pure fast-forward** — no merge commit, no cherry-pick, no conflict resolution.

Two canonical documents (`docs/AI_DEV_OS_V1.md`, `docs/AI_DEV_OS_RESEARCH_CATALOG_V1.docx`)
were present in the main worktree as **untracked files** but are referenced by SHA256
in the accepted `.ai-dev/state.yaml` (`canonical_doc_hashes`). They were preserved by
committing them in a provenance-documented commit.

**Result:** `main` now contains all accepted project work + all accepted AI Dev OS v1
work + all valuable documentation. No valuable content was lost. Verification matches
the documented baseline exactly.

---

# Original State

- Repository: `C:\Dev\psyche-os`
- Remote: `origin` → `git@github.com:iurii-izman/psyche-os.git`
- `main` = `origin/main` = `256057ca4a23efb1051631e29e54ade5d4536fc4` (in sync at freeze)
- No detached HEADs. No DIRTY_TRACKED or DIRTY_STAGED worktrees.

AI Dev OS lineage (the unique work):

| Commit | Message | Parent |
|---|---|---|
| `77b3ac8` | chore(ai-dev): implement AI Dev OS v1 control plane | `256057c` (main) |
| `91fdad0` | chore(ai-dev): finalize v1 acceptance | `77b3ac8` |
| `a672dde` | chore(ai-dev): close v1 live hook acceptance | `91fdad0` |

- `merge-base(main, a672dde)` = `256057c` → `a672dde` is a direct descendant of `main`.
- `.ai-dev/` did not exist in `main` → the lineage is purely additive.
- `.ai-dev/state.yaml`: `production_ready: true`, `acceptance_status: VERIFIED`.

Dangling superseded object (no unique content, documented for completeness):
- `fe3c55e` (`chore(ai-dev): finalize v1 acceptance`) was referenced by
  `.ai-dev/state.yaml` as `acceptance_commit` at freeze time (later corrected to
  `91fdad0` in the metadata hygiene pass). It is unreachable from any ref;
  `git diff fe3c55e 91fdad0` = 1 line in `.ai-dev/state.yaml` (the `acceptance_commit`
  field itself). Fully subsumed by `91fdad0`; retained in the object store (dangling).

---

# Backup

| Field | Value |
|---|---|
| Path | `C:\Dev\psyche-os-backups\psyche-os-pre-consolidation-20260815.bundle` |
| Command | `git bundle create … --all` |
| Verify | `… is okay` (56 refs) |
| Size | 1,239,018 bytes |
| SHA256 | `ff084e217c4281a606774f9d4c9b1c1c5d36fc0ad1ab7bacdee04f1d248b4f00` |

Stored outside the repository (not committed). Do not delete. Captures all refs
including Codex internal `refs/codex/turn-diffs/*` checkpoints.

---

# Branch Inventory (at freeze)

Classification: `ANCESTOR` = tip is ancestor of main; `UNIQUE_ACCEPTED` = ahead of main.

| Branch | Tip | Class |
|---|---|---|
| `main` | `256057c` | HEAD |
| `claude/priceless-keller-a86c97` | `a672dde` | UNIQUE_ACCEPTED |
| `claude/sad-chebyshev-784466` | `91fdad0` | UNIQUE_ACCEPTED |
| `claude/awesome-jepsen-439ea4` | `0090ba0` | ANCESTOR |
| `claude/charming-jennings-956993` | `0090ba0` | ANCESTOR |
| `claude/elegant-chebyshev-b2c8fa` | `0fa1547` | ANCESTOR |
| `claude/gracious-carson-085fde` | `256057c` | ANCESTOR |
| `claude/practical-blackwell-2a40fc` | `256057c` | ANCESTOR |
| `claude/practical-meninsky-04d80f` | `a9b2b59` | ANCESTOR |
| `claude/quizzical-yonath-2fd701` | `a9b2b59` | ANCESTOR |
| `claude/xenodochial-greider-9e2f02` | `0090ba0` | ANCESTOR |
| `codex/deepseek-development-system` | `a9b2b59` | ANCESTOR |
| `codex/e02-secure-desktop-shell` | `d7fbe21` | ANCESTOR |
| `codex/e03-evidence-archive` | `52221ad` | ANCESTOR |
| `codex/e04-rights-gated-assessment-registry` | `66e6e04` | ANCESTOR |
| `codex/e05-longitudinal-ema-sleep-analysis` | `e0d9962` | ANCESTOR |
| `codex/e06-bounded-n-of-1-protocols` | `cc2688a` | ANCESTOR |
| `codex/e07-bounded-ai-proposal` | `f6c87ac` | ANCESTOR |
| `codex/e08-untrusted-import-core` | `9e4383f` | ANCESTOR |
| `codex/e09-local-retrieval` | `13522ab` | ANCESTOR |
| `research/master-spec-v2-final` | `eff1a97` | ANCESTOR |

Remote: `origin/main` (= main) + `origin/codex/e02…e09` (all ANCESTOR).

---

# Worktree Inventory (at freeze)

| Worktree | Branch | Status |
|---|---|---|
| `C:/Dev/psyche-os` | `main` | DIRTY_UNTRACKED (2 canonical docs) |
| `.claude/worktrees/awesome-jepsen-439ea4` | `claude/awesome-jepsen-439ea4` | CLEAN |
| `.claude/worktrees/charming-jennings-956993` | `claude/charming-jennings-956993` | DIRTY_UNTRACKED (1 file) |
| `.claude/worktrees/elegant-chebyshev-b2c8fa` | `claude/elegant-chebyshev-b2c8fa` | CLEAN |
| `.claude/worktrees/gracious-carson-085fde` | `claude/gracious-carson-085fde` | CLEAN |
| `.claude/worktrees/practical-blackwell-2a40fc` | `claude/practical-blackwell-2a40fc` | CLEAN |
| `.claude/worktrees/practical-meninsky-04d80f` | `claude/practical-meninsky-04d80f` | CLEAN |
| `.claude/worktrees/priceless-keller-a86c97` | `claude/priceless-keller-a86c97` | CLEAN |
| `.claude/worktrees/quizzical-yonath-2fd701` | `claude/quizzical-yonath-2fd701` | CLEAN |
| `.claude/worktrees/sad-chebyshev-784466` | `claude/sad-chebyshev-784466` | CLEAN |

Dirty worktree protection:
1. **Main worktree**: `docs/AI_DEV_OS_V1.md` (66,461 B) + `docs/AI_DEV_OS_RESEARCH_CATALOG_V1.docx`
   (114,628 B). SHA256 matches `canonical_doc_hashes` in `.ai-dev/state.yaml` → canonical
   docs, preserved by commit.
2. **charming-jennings-956993**: `scripts/validate_e01_assurance.py` (19,019 B) — an
   earlier draft of a script already tracked in `main` (tracked version is a superset).
   Retained and documented; no unique content beyond what is in `main`.

---

# Unique Work Analysis

Only the AI Dev OS lineage was ahead of `main`. Final acceptance content includes:
Windows absolute protected-path handling; `_norm()`; `_relativize()`; absolute-path
regression tests; dispatcher 12/12; final `VERIFIED` state/reports. All `codex/e*`
epics were already merged (ancestors).

---

# Integrations Performed

1. **Fast-forward** `main` → `a672dde` (preserves the natural 3-commit AI Dev OS history;
   no cherry-pick, no merge commit). Verified `git merge-base --is-ancestor a672dde main` = PASS.
2. **Commit** `129b34b` — `docs: preserve canonical AI Dev OS v1 documentation`
   (the two canonical docs referenced by `.ai-dev/state.yaml` `canonical_doc_hashes`).

No other branch had unique content, so nothing else was merged. No conflict resolution
was required (pure additive fast-forward).

---

# Conflict Decisions

None. The integration was a purely additive fast-forward onto an unchanged `main`;
no conflicts arose. All non-conflicting intent preserved by construction.

---

# AI Dev OS Preservation

- `a672dde` (`chore(ai-dev): close v1 live hook acceptance`) is an **ancestor of final main**:
  `git merge-base --is-ancestor a672dde main` → PASS.
- Full lineage `77b3ac8 → 91fdad0 → a672dde` is preserved with original authorship,
  messages, and order (no squash, no rewrite).
- `a672dde` tree content is fully present in final main (the docs commit is additive on top).

---

# Verification (on final content)

| Check | Result | Status |
|---|---|---|
| `uv run pytest -q` | 589 passed, 1 skipped | PASS (== baseline) |
| orchestration validator (`on main`) | 114 passed, 0 failed | PASS |
| research foundation validator | pre-existing env-artifact errors only (node_modules / `.db` / `.venv`); AI Dev OS contributes 0 | PASS (no new findings) |
| AI Dev OS doctor | `RESULT: PASS` (all core checks OK) | PASS |

Notes (all documented pre-existing in `.ai-dev/state.yaml` / implementation report):
- `ruff`: 215 pre-existing lint errors; `mypy`: 40 pre-existing type errors.
- research validator's 113 errors are **all** gitignored local artifacts
  (`desktop/node_modules/*`, `psyche_vault_*.db`, `.mypy_cache/*.db`,
  `.venv/*/cryptography/*`). Verified via `git check-ignore`; zero errors outside
  those pre-existing categories.
- orchestration validator reports 113/1 on feature branches (branch-name gate) and
  114/0 on `main` — observed 114/0 after promotion.

---

# Branches Deleted

## Local (19) — all `git branch -d` (safe, proven merged)

`claude/awesome-jepsen-439ea4`, `claude/elegant-chebyshev-b2c8fa`,
`claude/practical-blackwell-2a40fc`, `claude/practical-meninsky-04d80f`,
`claude/priceless-keller-a86c97` (= `a672dde`), `claude/quizzical-yonath-2fd701`,
`claude/sad-chebyshev-784466` (= `91fdad0`), `claude/xenodochial-greider-9e2f02`,
`codex/deepseek-development-system`, `codex/e02-secure-desktop-shell`,
`codex/e03-evidence-archive`, `codex/e04-rights-gated-assessment-registry`,
`codex/e05-longitudinal-ema-sleep-analysis`, `codex/e06-bounded-n-of-1-protocols`,
`codex/e07-bounded-ai-proposal`, `codex/e08-untrusted-import-core`,
`codex/e09-local-retrieval`, `research/master-spec-v2-final`,
`integration/canonical-main-20260815`.

## Remote (8)

`origin/codex/e02-secure-desktop-shell`, `origin/codex/e03-evidence-archive`,
`origin/codex/e04-rights-gated-assessment-registry`,
`origin/codex/e05-longitudinal-ema-sleep-analysis`, `origin/codex/e06-bounded-n-of-1-protocols`,
`origin/codex/e07-bounded-ai-proposal`, `origin/codex/e08-untrusted-import-core`,
`origin/codex/e09-local-retrieval` — deleted after final main push (all proven ancestors).

---

# Branches Retained

| Branch | Why |
|---|---|
| `main` | canonical development branch |
| `claude/charming-jennings-956993` | checked out in a DIRTY worktree (untracked `scripts/validate_e01_assurance.py` draft) — not deletable per safety rule |
| `claude/gracious-carson-085fde` | checked out in the active Claude Code session worktree |

---

# Worktrees Removed

`awesome-jepsen-439ea4`, `elegant-chebyshev-b2c8fa`, `practical-meninsky-04d80f`,
`quizzical-yonath-2fd701` (fully removed), plus `practical-blackwell-2a40fc`,
`priceless-keller-a86c97`, `sad-chebyshev-784466` (registrations removed; empty
directories remain on disk pending OS handle release — see Known Risks).

# Worktrees Retained

| Worktree | Why |
|---|---|
| `C:/Dev/psyche-os` | main worktree |
| `.claude/worktrees/charming-jennings-956993` | dirty (untracked file) — preserved |
| `.claude/worktrees/gracious-carson-085fde` | active session |

---

# Final Main

- Original main SHA: `256057ca4a23efb1051631e29e54ade5d4536fc4`
- Integration content SHA: `129b34b` (`a672dde` + canonical docs commit)
- Final main SHA: resolved via `git rev-parse ai-dev-os-v1-canonical` (tag target)
- Tag: `ai-dev-os-v1-canonical` (annotated)
- origin/main SHA: equals final main after push (fast-forward, no force)

---

# Preservation Matrix

| Original branch | Tip | Disposition | In main? | History preserved? | Safe to delete? |
|---|---|---|---|---|---|
| `claude/priceless-keller-a86c97` | `a672dde` | FF-merged | yes | yes (natural history) | yes |
| `claude/sad-chebyshev-784466` | `91fdad0` | subsumed by FF | yes | yes | yes |
| `claude/awesome-jepsen-439ea4` | `0090ba0` | ancestor | yes | yes | yes |
| `claude/charming-jennings-956993` | `0090ba0` | ancestor (dirty wt) | yes | yes | no (dirty worktree) |
| `claude/elegant-chebyshev-b2c8fa` | `0fa1547` | ancestor | yes | yes | yes |
| `claude/gracious-carson-085fde` | `256057c` | ancestor (session wt) | yes | yes | no (active session) |
| `claude/practical-blackwell-2a40fc` | `256057c` | ancestor | yes | yes | yes |
| `claude/practical-meninsky-04d80f` | `a9b2b59` | ancestor | yes | yes | yes |
| `claude/quizzical-yonath-2fd701` | `a9b2b59` | ancestor | yes | yes | yes |
| `claude/xenodochial-greider-9e2f02` | `0090ba0` | ancestor | yes | yes | yes |
| `codex/deepseek-development-system` | `a9b2b59` | ancestor | yes | yes | yes |
| `codex/e02-secure-desktop-shell` | `d7fbe21` | ancestor | yes | yes | yes |
| `codex/e03-evidence-archive` | `52221ad` | ancestor | yes | yes | yes |
| `codex/e04-rights-gated-assessment-registry` | `66e6e04` | ancestor | yes | yes | yes |
| `codex/e05-longitudinal-ema-sleep-analysis` | `e0d9962` | ancestor | yes | yes | yes |
| `codex/e06-bounded-n-of-1-protocols` | `cc2688a` | ancestor | yes | yes | yes |
| `codex/e07-bounded-ai-proposal` | `f6c87ac` | ancestor | yes | yes | yes |
| `codex/e08-untrusted-import-core` | `9e4383f` | ancestor | yes | yes | yes |
| `codex/e09-local-retrieval` | `13522ab` | ancestor | yes | yes | yes |
| `research/master-spec-v2-final` | `eff1a97` | ancestor | yes | yes | yes |
| `main` | `256057c` | canonical base | yes | yes | n/a |

---

# Known Remaining Risks

1. **Three empty worktree directories** (`.claude/worktrees/{practical-blackwell-2a40fc,
   priceless-keller-a86c97, sad-chebyshev-784466}`) remain on disk: git registrations
   are removed and contents deleted, but the top-level dirs return "Device or resource
   busy" (an OS handle is still open). Harmless; removable after the handle releases or
   on reboot. Not a git state issue.
2. **Resolved — `.ai-dev/state.yaml` provenance**: the dangling
   `acceptance_commit: fe3c55e` was corrected to `91fdad0`, with
   `live_acceptance_commit: a672dde` and `consolidation_commit` added, in the follow-up
   metadata hygiene pass. No dangling refs remain in state.
3. **Pre-existing tool debt**: `ruff` 215, `mypy` 40, research-validator env-artifact
   errors, osv-scanner RUSTSEC, semgrep 1. All pre-existing and unrelated to this pass.

---

# Rollback Procedure

1. The pre-consolidation bundle is the emergency restore point:
   `git clone C:\Dev\psyche-os-backups\psyche-os-pre-consolidation-20260815.bundle restore-repo`
   reproduces every pre-consolidation ref.
2. To restore just `main` to its original state:
   `git branch -f main 256057ca4a23efb1051631e29e54ade5d4536fc4` (only if re-doing locally).
3. The annotated tag `ai-dev-os-v1-canonical` marks the canonical checkpoint; deleting or
   moving it is not required for rollback.
4. Deleted local/remote branches are recoverable from the bundle (all refs included).
