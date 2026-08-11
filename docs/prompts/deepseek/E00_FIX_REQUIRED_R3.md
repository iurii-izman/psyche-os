# PSYCHE OS — E00 minimal targeted repair R3

Repair only the six failed R2 findings below: F02, F04, F05, F07, F08, and F09.
Do not revisit F03 or F06, do not start E01, and do not perform research or an
architecture redesign. Preserve genuine AES-GCM backup/export encryption and
all already passing behavior. `REAL_DATA_GATE` must remain `CLOSED`.

## F02 — complete backup and atomic fail-closed restore

- Define the exact required backup table/schema inventory; never skip a required
  table or convert a query/schema error into omission.
- Query each table according to its real schema instead of assuming every table
  has `is_active`. Authenticate the complete versioned inventory and reject
  missing, extra, incompatible, or downgraded manifest/schema evidence.
- Treat a restore target as empty only after checking the entire target schema,
  not only `vault_config`. Restore into an isolated staging database, validate
  everything, commit once, and expose/activate only after success. Any failure
  must leave the target unchanged and no partial state visible.
- Add production-path tests for the complete real schema, an omitted table,
  incompatible format, wrong key, data outside `vault_config` in the target,
  mid-restore failure/rollback, and encrypted backup → restore → content equality.

## F04 — unambiguous SQLCipher probes

- Accept licence/build evidence only when it matches an explicit recognized
  SQLCipher licence/tier/version pattern; arbitrary non-placeholder text fails.
- Require keyed `PRAGMA cipher_integrity_check` evidence with its documented
  successful result. Plain SQLite `integrity_check`, empty/ambiguous output, and
  any non-`ok` result must not establish cipher page/HMAC integrity.
- Ensure missing, placeholder, generic exception, and ambiguous evidence fails
  every relevant gate. Add direct negative tests for arbitrary licence text and
  the currently passing non-`ok` final integrity branch.

## F05 — enforce storage invariants in the real schema and write path

- Separate stable record/business identity from row `version_id`; allow multiple
  historical versions and enforce exactly one active version for each stable
  record across every declared versioned table. Add consistent version columns,
  constraints, indexes, and foreign keys through explicit transactional migration
  files.
- Preserve all subtype fields when closing/versioning immutable dataclasses
  (for example with `dataclasses.replace`) and test an actual subtype.
- Use per-table column allowlists; never interpolate caller-controlled column
  names into SQL merely because the table is allowed.
- Enforce blob `created → stored → verified` before semantic commit; require the
  vault identity and a non-empty keyed digest. Persist/reload all AAD/vault fields
  so verification uses the same envelope context and rejects cross-vault blobs.
- Add real-schema tests for two versions of one record, active-version uniqueness,
  subtype preservation, hostile column names, transactional migration rollback,
  blob state transitions, missing digest, and cross-vault verification.

## F07 — non-self-issuable synthetic authority and truthful CLI

- Remove the public capability constructor/token disclosure. Mint bundled-fixture
  authority only inside a private package-owned loader and make it non-serializable,
  non-reconstructible, and bound to the bundled synthetic fixture identity.
- Require and validate that authority at the actual storage/UoW write boundary;
  direct calls without it must fail before mutation.
- `vault init` must create and verify the vault/database it reports, otherwise
  return a non-zero fail-closed result. Apply the same rule to every command.
- Test public self-issuance attempts, direct write without authority, forged or
  copied tokens, and success-without-operation CLI paths.

## F08 — read-only behavioral validators

- Validators must not create or modify any directory/artifact. Remove all
  `mkdir`/write side effects and test filesystem immutability.
- Generate representative backup/export artifacts with production code and
  validate the emitted instances against the shipped JSON Schemas. Reconcile
  schema names, required fields, formats, versions, and checksum structures.
- Validate actual migration files and bundled fixtures behaviorally, not by
  filenames. Reconcile every direct SBOM dependency name and exact resolved
  version with `uv.lock`; reject missing, extra, and mismatched entries.
- Consume strict F04 probe semantics and reject label-only/status-only evidence.
  Add negative tests for the current manifest mismatch and SBOM version drift.

## F09 — provenance referential integrity and Windows-safe filesystem boundary

- Reject provenance edges unless both endpoint IDs exist in the graph at
  mutation time; retain canonical relation validation and implement/test the
  required contradiction and supersession behavior.
- On Windows, enforce no-follow/reparse-safe operations with handles and verify
  the opened object and parent chain. Do not treat `O_NOFOLLOW == 0`, absent
  `/proc/self/fd`, or swallowed verification errors as protection.
- Remove or route all legacy path-based read/write/delete entry points through
  the same hardened boundary. Add a Windows-capable reparse/swap test that does
  not silently skip the invariant.

## Required handoff

Run small production-path regression tests while repairing, then the repository
E00 gate once. Update the implementation/repair report with exact outputs. Leave
`STATE.yaml` at `IMPLEMENTED / REVIEW_REQUIRED`, create no accepted commit, and
do not prepare E01; independent Codex re-acceptance owns those transitions.
