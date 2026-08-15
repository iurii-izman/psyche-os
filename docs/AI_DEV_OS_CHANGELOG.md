# AI Dev OS v1 — Changelog

Concise change ledger. No narrative filler.

| File / tool | Change | Reason | Behavior impact | Rollback |
|---|---|---|---|---|
| `ast-grep` (0.45.1) | Installed user-local via npm | Core structural-retrieval layer (V1 §25) | `ast-grep`/`sg` available | `npm uninstall -g @ast-grep/cli` |
| `gitleaks` (8.30.1) | Installed user-local via winget | Conditional secret scan (git repo) | `gitleaks` available | `winget uninstall Gitleaks.Gitleaks` |
| `osv-scanner` (2.4.0) | Installed user-local via winget | Conditional dependency-vuln scan (uv.lock + Cargo.lock) | `osv-scanner` available | `winget uninstall Google.OSVScanner` |
| `semgrep` (1.173.0) | Installed user-local via pipx | Conditional SAST over security-sensitive Python | `semgrep` available | `pipx uninstall semgrep` |
| `.ai-dev/policy/*` | Added risk, protected-paths, approvals, capabilities, dependencies | Encode risk engine + approval matrix (V1 §9–10) | Documented policy; enforced by hook dispatcher | delete `.ai-dev/policy/` |
| `.ai-dev/profiles/*` | Added balanced/quality/economy/lab | Operating profiles (V1 §55) | Profile selection reference | delete `.ai-dev/profiles/` |
| `.ai-dev/contracts/task-contract.template.yaml` | Added | Reusable Task Contract (V1 §8) | Template only | delete file |
| `.ai-dev/verification/*` | Added commands.yaml + gates.yaml | Canonical project commands + V0–V4 ladder (V1 §31–32) | Verification reference | delete `.ai-dev/verification/` |
| `.ai-dev/skills/*` | Added 11 psyche-* skills | Project-local skills (V1 §37) | Skill reference via AGENTS.md | delete `.ai-dev/skills/` |
| `.ai-dev/hooks/dispatcher.py` + modules + test | Added single deterministic dispatcher | One entry point; fail-closed guard (V1 §36) | Hooks guard protected paths + destructive commands | create `.ai-dev/hooks/DISABLED` |
| `.claude/settings.json` | Added PreToolUse + Stop hook wiring | Activate dispatcher (V1 §36) | Dispatcher runs on Bash/Edit/Write/NotebookEdit + Stop | delete `.claude/settings.json` |
| `.ai-dev/telemetry/*` | Added schema.json, redaction.yaml, retention.yaml, writer.py, derive_sqlite.py | Append-only JSONL telemetry + redaction (V1 §46–48) | Local telemetry, metadata-first | delete `.ai-dev/telemetry/` |
| `.ai-dev/capabilities/registry.yaml` | Added | Capability registry (V1 §39) | Capability states | delete file |
| `.ai-dev/evidence/*` | Added capability evidence + decision dir | Evidence ledger (V1 §52) | Provenance | delete `.ai-dev/evidence/` |
| `.ai-dev/recovery/*`, `.ai-dev/routing/*` | Added snapshot/recovery-packet templates + routing/circuit-breakers | Recovery + routing (V1 §13–17) | Templates + config | delete dirs |
| `.ai-dev/context-broker.md` | Added | Context waterfall doc (V1 §25) | Reference | delete file |
| `scripts/ai_dev_doctor.py` | Added | Doctor command (V1 §44) | `python scripts/ai_dev_doctor.py` validates system | delete file |
| `AGENTS.md` | Added "AI Dev OS v1 — control plane" bootloader section | Route to control plane (V1 §7) | Extra routing pointers only | revert section |
| `docs/AI_DEV_OS_*` (report/manual/changelog) | Added | Required reporting (V1 §45–48) | Documentation | delete files |

Canonical inputs (`docs/AI_DEV_OS_V1.md`, `docs/AI_DEV_OS_RESEARCH_CATALOG_V1.docx`) were NOT modified.
