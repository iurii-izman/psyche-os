# Personal Mode v1 implementation authorization

Status: CLOSED_HISTORICAL_IMPLEMENTATION_AUTHORITY
Recorded: 2026-08-24

Accepted architecture candidate: `79bf063902ab4c1106fdfb420edcf905dfa42f43`

Architecture merge: `e8bfb83211fb424d09fa9a272066d5c6232cc0dd`

Implementation commit: `e9fec09b23e27a04bd300452963675e653671313`

Canonical merge: `f397c949812cfc82749a9a5a49d5458e53ea36af`

Independent architecture verdict: ACCEPT

This file records explicit owner decisions already given. It does not create
new authority beyond their exact text.

## PMV1-V10-SQLITE-GENERALIZED-REBUILD

Classification: `HUMAN_REPOSITORY_OWNER`, `EXPLICIT_APPROVAL`,
`HISTORICAL_APPROVAL_FOR_ACCEPTED_PERSONAL_MODE_V1_IMPLEMENTATION`.

> I explicitly approve V10 migration PMV1-V10-SQLITE-GENERALIZED-REBUILD exactly as described in the independently reviewed Personal Mode v1 architecture, with foreign_keys disabled only outside the migration transaction. This does not authorize destructive migration, crypto-algorithm change, a new dependency, network, REAL_DATA_GATE opening, or real personal data.

This authorizes only `PMV1-V10-SQLITE-GENERALIZED-REBUILD` and its already
accepted implementation scope.

## Key, recovery, and rotation

Classification: `HUMAN_REPOSITORY_OWNER`, `EXPLICIT_APPROVAL`,
`HISTORICAL_APPROVAL_FOR_ACCEPTED_PERSONAL_MODE_V1_IMPLEMENTATION`.

> I explicitly approve PMV1-KEY-ENVELOPE-V1, PMV1-ROTATION-ISOLATED-REENCRYPTION-V1, PMV1-RECOVERY-BOOTSTRAP-V1, the retained-key lifecycle, and the retained-N-before-active-promotion durability invariant exactly as described in the independently reviewed Personal Mode v1 architecture. This does not authorize crypto-algorithm change, destructive migration, a new dependency, network, REAL_DATA_GATE opening, or real personal data.

## PMV1-V10-POLICY-IDENTITY-REPAIR-A1

Classification: `HUMAN_REPOSITORY_OWNER`, `EXPLICIT_APPROVAL`,
`HISTORICAL_APPROVAL_FOR_ACCEPTED_PERSONAL_MODE_V1_IMPLEMENTATION`.

> I explicitly approve schema amendment PMV1-V10-POLICY-IDENTITY-REPAIR-A1 as part of the already approved V10 migration: introduce the non-versioned system-owned `policy_identities` registry for stable Policy identity, require a one-to-one `policy_id`↔`record_id` mapping, rebuild `data_policies` to bind version rows to that stable identity, and rebuild `policy_lineage` foreign keys to reference `policy_identities`. I also approve replacing the impossible pre-migration global `foreign_key_check` on the known malformed V9 schema with exact-schema recognition and bounded policy-identity/orphan preflight checks; the post-migration global `foreign_key_check` remains mandatory and must be empty. Fail closed on ambiguous legacy mappings. This does not authorize destructive data loss, semantic policy rewriting, crypto changes, new dependencies, network exposure, REAL_DATA_GATE opening, or real personal data.

The amendment is an accepted bounded amendment: `policy_identities` is the
stable system-owned identity registry; `policy_id` and `record_id` are
one-to-one; `data_policies` remains versioned with
`PRIMARY KEY(record_id, version_id)`; version rows bind to the stable identity;
and `policy_lineage` remains `PolicyId`-to-`PolicyId` lineage. The exact known
malformed V9 preflight exception is permitted only for that relationship;
post-V10 global `foreign_key_check` is mandatory and empty, and ambiguity
fails closed. This does not authorize `UNIQUE(data_policies.policy_id)` or a
conversion of lineage to version IDs.

## Explicit non-authorization

These approvals do not authorize REAL_DATA_GATE opening, LOCAL_PERSONAL
real-data admission, real personal data, owner gate attestation, fabricated
independent or qualified review, a new crypto algorithm, weakened KDF/AEAD, a
new production dependency, network/provider enablement, permission expansion
outside the accepted architecture, destructive data loss, force push, or
history rewrite.
