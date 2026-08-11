# PSYCHE OS — E00 post-R3 exact closure fixes

Repair only the concrete failed mechanisms below in F02, F05, F07, F08, and
F09. F04 passed and must not be revisited. Do not perform research, redesign the
architecture, prepare E01, or admit real data. Keep `REAL_DATA_GATE = CLOSED`.

## Threat-model clarification for F07

The synthetic authority boundary protects against ordinary callers through the
supported/public application and storage interfaces, forged serialized/copied
capabilities, imported/untrusted content, and direct unauthorized UoW usage.

Do not attempt to claim security against an attacker who already has arbitrary
code execution, unrestricted introspection, monkey-patching, or memory access
inside the trusted Python process. Such an attacker is outside this F0
capability boundary.

Acceptance still requires:
- no publicly supported minting path;
- forged/uninitialized/copied/serialized authority objects fail validation;
- only the bundled fixture loader obtains a valid authority;
- storage/UoW enforces it before mutation;
- authority is bound to the exact bundled fixture identity.


## Threat-model clarification for F09

Close pathname/reparse/TOCTOU attacks within the application's vault filesystem
boundary on supported Windows.

If Python stdlib cannot provide the required semantics, implement the minimum
Windows-specific adapter using documented Win32 handle APIs.

Do not invent a generic filesystem framework.

The boundary must protect against ordinary local pathname/reparse manipulation,
but does not claim protection against Administrator/SYSTEM, arbitrary code
execution inside the trusted process, kernel compromise, or malicious filesystem
drivers.


## F02 — bind and require the complete backup contract

1. Treat every frozen E00 backup inventory table as required. A missing or
   unreadable inventory table must fail backup; do not serialize it as omitted
   or empty. Record and authenticate the exact inventory and schema version.
2. Put the authoritative manifest inside the AEAD-protected payload or bind its
   canonical bytes in AAD. Verification must require exact magic/version equality
   at every level, an exact inventory key set, a checksum for every table, and
   agreement between manifest counts/checksums and decrypted rows. Reject lower,
   missing, extra, contradictory, or checksum-empty manifests.
3. Restore only through an isolated staging database with the complete expected
   schema. Missing target tables or target-inspection errors fail closed. Validate
   schema, rows, foreign keys, counts, checksums, and integrity before one atomic
   activation; no partial state may become visible.
4. Add production tests for an omitted non-`vault_config` table, version `0`,
   removed checksums, mutated outer manifest, wrong key, nonempty target,
   injected mid-restore failure with unchanged target, and complete encrypted
   schema backup → isolated restore → content equality.

## F05 — make versioning and blobs true on the real write path

1. Remove global business-ID uniqueness that prevents history. For every table
   in `VERSIONED_TABLES`, use a distinct row/version identity, repeatable stable
   record/business identity, consistent previous-version fields, and a partial
   unique constraint enforcing exactly one active row per stable identity.
2. Close immutable subclasses with `dataclasses.replace()` or an equivalent that
   preserves every subtype field value. Test a subtype field whose value differs
   from its default.
3. Move migrations to explicit ordered migration files and execute each migration
   in an explicit transaction without naïve semicolon splitting. Injected DDL or
   bookkeeping failure must roll back both schema and migration record.
4. Require a non-empty vault digest key whenever blobs are written. Persist vault
   ID and every envelope/AAD field. Enforce and observe `CREATED → STORED →
   VERIFIED` before semantic commit; verification must use the persisted vault
   context and keyed digest and must reject missing digest and cross-vault use.
5. Test two real historical versions for every versioned schema pattern, active
   uniqueness, subtype preservation, migration rollback, every blob transition,
   missing digest, wrong vault, and persisted-AAD verification.

## F07 — remove caller-mintable authority and enforce storage authorization

1. Remove ordinary-caller access to `FixtureAuthority._mint`, public capability
   construction, raw/internal authority attributes, and serializable authority
   state. `object.__new__`, copy/deepcopy, pickle, forged/copied state, and direct
   helper calls must not yield an authority accepted by storage.
2. Keep minting and use inside the bundled-fixture loader; do not return the
   authority to callers. Bind authorization to the exact bundled fixture identity
   and pass it directly to the storage mutation boundary.
3. Make UoW/storage reject synthetic record and blob mutation before any SQL when
   valid loader authority is absent. Direct `UnitOfWorkManager` use without it
   must fail and leave the database unchanged.
4. Retest every CLI success path against the resulting persisted state, including
   a complete and verified `vault init`; never return success for a stub.

## F08 — validate behavior and the actual evidence files

1. Preserve validator read-only behavior and add a before/after repository
   metadata/content snapshot test.
2. Generate representative backup and export artifacts with production code and
   validate the actual emitted instances using the shipped JSON Schemas, including
   nested types, required fields, versions, checksum shape, and negative manifest
   mutations. A Python key-set comparison is not schema validation.
3. Execute migrations against temporary databases to prove ordering, checksum,
   rollback, and idempotence. Load the bundled fixture through its production
   authority path and verify both accepted bundled data and rejected external/
   forged input.
4. Read `artifacts/f0/sbom.cdx.json` and reconcile every direct dependency's
   normalized name and exact resolved version with `uv.lock`. Fail on missing,
   duplicate, stale, or mismatched direct components. The eight currently stale
   versions must be corrected or rejected by the validator.
5. Consume the strict F04 probe outputs structurally; status labels or merely
   non-empty evidence strings cannot independently establish acceptance.

## F09 — use Windows handles for the complete filesystem boundary

1. Replace `resolve → later reopen pathname` with Windows-safe handle operations.
   Open the base and relevant parent/object with reparse-safe Win32 flags, reject
   unexpected reparse points, and validate the final path and identity from the
   actual opened handles. Do not verify by calling `realpath()` on the pathname
   after opening it.
2. Make atomic write/replace and delete operate through the same verified handle
   boundary so a parent or target swap cannot redirect the operation. Route
   `read_bytes`, `write_bytes`, `read_text`, `write_text`, and `delete` through
   this one implementation; retain no legacy pathname bypass.
3. Add a Windows reparse/junction or deterministic swap-race test that exercises
   the production sequence and cannot silently skip. Retain the now-correct
   provenance endpoint, relation, contradiction/supersession, and digest tests.

## Handoff

Run focused production-path tests while repairing and the canonical E00 gate once
after all five findings pass. Update the repair report with exact evidence. Leave
E00 at `IMPLEMENTED / REVIEW_REQUIRED`, create no accepted commit, do not prepare
E01, and keep `REAL_DATA_GATE = CLOSED` for independent acceptance.
