# psyche-recover

WHEN TO USE: a task has failed or is escalating (Flash → Pro, reviewer handoff,
session end, risky operation).

INPUTS: Task Contract, current diff, the exact verifier failure.

STEPS:
1. Classify the failure before repair: PRODUCT_DEFECT, TEST_DEFECT, ORACLE_DEFECT,
   ENVIRONMENT_DEFECT, or TOOL_HARNESS_DEFECT. Preserve the evidence supporting that
   classification; an infrastructure failure is not a product PASS.
2. Write a Task Snapshot (`.ai-dev/recovery/task-snapshot.template.yaml`).
3. Build a Recovery Packet (`.ai-dev/recovery/recovery-packet.template.md`):
   contract + snapshot + diff + exact failure + relevant source + attempt summary.
4. For a normal in-scope deterministic failure, localize it, make the smallest
   repair, rerun the failed oracle plus directly coupled regressions, and continue
   inside the same Task Contract. Respect circuit breakers for repeated failure;
   provider failure → snapshot then explicit fallback/pause.
5. On repeated verifier failure, preserve known-good product work and stop
   feature-local infrastructure expansion. For supplemental evidence, record separate
   verifier debt or escalate the verifier as its own task if future product work
   materially depends on it. For contract-required proof, use only an explicitly
   pre-authorized equivalent alternate oracle; otherwise keep the claim blocked until
   human approval changes acceptance. Do not hide a missing load-bearing HIGH/CRITICAL
   proof or replace a repository-required gate.

OUTPUT: a Recovery Packet (bounded, no raw transcript) and a next action.

STOP CONDITIONS: stop only for a changed architecture/trust model, a new protected
action/approval, destructive or network/permission expansion, crypto or real-data-gate
change, or repeated evidence that the accepted design is structurally wrong. Do not
retry-until-green or turn a bounded product repair into an unbounded harness project.
Do not pass giant logs or the full transcript to the strong model.

ALLOWED TOOLS: Read, git diff, run the failing command to capture evidence.

FORBIDDEN SIDE EFFECTS: no history rewrite, no discarding failure evidence.
