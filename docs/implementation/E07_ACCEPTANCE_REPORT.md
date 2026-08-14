# E07 final high-risk bounded acceptance report

**Review date:** 2026-08-14
**Verdict:** `ACCEPTED`
**Base:** `32ea55114a9285057602ef2b88b11a2edcadf58b`
**Accepted E07 implementation commit:** `7d6c040eb22e15ab214f904bdf97d22d38014599`
**Profile:** one optional synthetic-only bounded AI proposal slice
**REAL_DATA_GATE:** `CLOSED`

## Independent review findings and repairs

| Review target | Finding | Accepted repair |
| --- | --- | --- |
| Capability issuance | Public look-alike `PreparedDisclosure` and `DisclosureAuthorization` values could authorize or execute, including across service instances. | The service now owns exact pending preparation and issued authorization object registries. Only exact values minted by that instance pass; an execution attempt consumes the issued capability. |
| Provider call count | Reusing one `interaction_id` with a new authorization could invoke the provider twice. | Each successfully prepared interaction identity is reserved for the service lifecycle and may reach the provider at most once. Failures are not retried. |
| Authorization time | Use before `authorized_at` succeeded and a naive execution clock raised an uncontrolled datetime exception. | Execution requires an aware clock and enforces the inclusive interval `authorized_at <= now <= expires_at`, failing with a typed boundary error. |
| Policy TOCTOU | Own policy, reconstructive lineage, and purpose expiry were not revalidated after authorization. | Immediately before content access, the service recomputes exact current policy and lineage at execution time and compares the decision identity with the authorized manifest. Drift, contradiction, expiry, and `NEVER_CLOUD` fail before content or provider access. |
| Required safety vocabulary | Direct medical direction (`Take 10 mg of aspirin now`) and autonomous recommendation (`Start journaling every morning`) bypassed the bounded deterministic validator. | The demonstrated forms were added to the frozen E07 vocabulary with focused regression tests; no general NLP classifier was introduced. |

## Bounded acceptance decision

| Target | Result | Evidence |
| --- | --- | --- |
| Capability minting and replay | **PASS** | Fabricated prepared values, fabricated/modified authorizations, and cross-service replay cause zero content reads and zero provider calls. |
| One interaction / one call | **PASS** | Re-preparing the same interaction is rejected; successful, unavailable, timeout, and malformed paths never retry. |
| Authorization window | **PASS** | Use-before-authorized, post-expiry, and naive clocks fail closed; both inclusive endpoints are covered. |
| Policy and lineage freshness | **PASS** | Own/parent policy identity, purpose, location, expiry, composition, and `NEVER_CLOUD` are revalidated before content. |
| Provider identity freshness | **PASS** | Exact provider/model/config and approval/evaluation status are re-resolved before disclosure. Unknown, removed, retired, revoked, drifted, or unevaluated identities cannot call. |
| Canonical content binding | **PASS** | Accepted E03 writes create immutable successor versions; no authorized production path changes selected assertion/unknown content while preserving `version_id`. E07 pins and rechecks exact active versions. |
| Preview exactness and ordering | **PASS** | Exact purpose, selected IDs/versions/categories/roles, provider identity, policy decision, transformations, and retention remain bound to the minted preview. All final gates precede content reads. |
| Proposal and safety authority | **PASS** | Instruction-shaped content cannot alter policy, selection, provider identity, tools, call count, retention, or ceilings. Output remains ephemeral `PROPOSED` / proposal-only and never becomes evidence or canonical state. |
| Stateless removal | **PASS** | No hosted memory, thread, file/vector store, tool authority, raw canonical prompt/response storage, or migration exists. Provider removal leaves core archive workflows usable. |

## Validation

```text
uv sync --frozen: PASS
authoritative E07 + adjacent-regression target: PASS (126 passed, 0 skipped)
uv run pytest -q: PASS (462 passed, 1 skipped)
validate_f0_scope.py: PASS (6/6)
validate_orchestration.py before acceptance metadata: PASS (112/112)
touched E07 Ruff: PASS
strict mypy over touched E07 source: PASS
whole-repository Ruff: baseline 127, candidate 127, new identities 0
whole-repository mypy: baseline 41, candidate 41, new identities 0
```

The sole skip is the unchanged administrator-only Windows symlink fixture. Expected SQLCipher diagnostics are wrong-key negative tests. Ruff `0.15.10` and mypy `2.3.0` were used for both baseline `32ea55114a9285057602ef2b88b11a2edcadf58b` and candidate comparison. Ruff retained 81 unique identities and mypy retained 25; all are unchanged accepted pre-E07 debt.

## Decision

The one mandatory independent bounded review found five concrete high-risk defects. All were repaired without adding a schema, trust boundary, production provider, session behavior, or E08 scope. Every frozen E07 boundary passes at implementation commit `7d6c040eb22e15ab214f904bdf97d22d38014599`. E07 is accepted; E08 remains `PLANNED`; `REAL_DATA_GATE` remains `CLOSED`.
