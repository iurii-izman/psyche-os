# psyche-verify

WHEN TO USE: deciding and running the right verification for a change.

INPUTS: risk level, affected files, Task Contract.

STEPS:
1. Classify planned evidence in the Task Contract: policy-owned
   `repository_required_gates`, risk-owned `contract_required_proof`, and
   non-load-bearing `supplemental_evidence`. Never silently relabel required proof
   after it fails.
2. Select repository gates from `.ai-dev/verification/gates.yaml` by changed area
   (python / ts / rust), then run targeted inner-loop checks per edit batch.
3. Run the risk-appropriate final repository gate once. Required extra proof must use
   its stated primary trusted oracle, failure meaning, and any pre-authorized
   equivalent alternate-oracle conditions.
4. If an oracle fails, classify PRODUCT / TEST / ORACLE / ENVIRONMENT / TOOL-HARNESS
   failure and identify its proof class. Infrastructure failure is neither product PASS
   nor automatic product FAIL:
   - A repository-required gate remains mandatory; it cannot be waived, replaced by a
     Task Contract fallback, or reclassified as supplemental.
   - Classified supplemental evidence failure does not change acceptance when all
     repository gates and contract-required proof remain satisfied and no material
     product/security invariant is unproven.
   - Contract-required proof may switch only to an already-trusted, equivalent
     alternate oracle explicitly pre-authorized in the Task Contract before execution.
     Record the primary failure, alternate evidence, and residual limitation.
   - Without that pre-authorization, keep the affected acceptance claim blocked until
     explicit human approval changes acceptance under `approvals.yaml`; neither an
     implementer nor reviewer/orchestrator may remove, downgrade, or replace proof
     after observing its failure.
5. For LOW/MEDIUM work, stop feature-local verifier expansion when policy gates pass,
   deterministic tests and/or trustworthy runtime evidence cover material behavior,
   and the failing non-load-bearing oracle does not protect a storage, security,
   privacy, permissions, or trust boundary. Record the limitation and residual.
   HIGH/CRITICAL work still blocks on missing load-bearing runtime/security evidence.
6. Record exit code, classification, and result in telemetry/snapshot.

OUTPUT: PASS/FAIL per gate with evidence.

STOP CONDITIONS: do not weaken a gate, assertion, test, or scanner to pass
(anti-reward-hacking). If a verifier repeatedly fails without showing a direct product
regression, crosses unrelated UI/locator/lifecycle mechanisms, consumes more loops
than the product change, and no longer discriminates correctness, stop patching that
verifier for this slice. Use one already-trusted sufficient oracle, record a separate
verifier debt, or escalate its architecture separately; do not redesign it inside an
unrelated MEDIUM feature for a decorative marker. A repeated deterministic product
failure → escalate, do not retry-until-green.

ALLOWED TOOLS: run verification commands.

FORBIDDEN SIDE EFFECTS: no editing of verification commands, no `noqa`/`type: ignore`
solely to silence errors.
