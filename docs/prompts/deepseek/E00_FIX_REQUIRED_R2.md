# PSYCHE OS — E00 targeted repair R2

Repair only the remaining focused F02–F09 defects. Preserve the genuine F01
AES-GCM export fix, component-aware path containment, and unknown-time `None`
semantics. Do not start E01, admit real data, or change the frozen architecture.
`REAL_DATA_GATE` must remain `CLOSED`.

## Required fixes

1. **Backup/restore:** never convert a failed table read to an empty table.
   Authenticate a complete, versioned manifest; reject omissions and incompatible
   schema. Restore only into an isolated empty target, in one transaction, with
   rollback and no partially visible state.
2. **Keys/recovery:** use current-user DPAPI scope without machine-wide access.
   Accept only the supported recovery-header version and enforce conservative
   upper/lower bounds for every Argon2 parameter before allocation or KDF work.
3. **SQLCipher proof:** missing, placeholder, empty, ambiguous, or generic-error
   evidence must fail. Require the expected cipher/licence result, keyed
   `cipher_integrity_check`, explicit wrong-key/plaintext classifications, and a
   real encrypted backup → restore → content round trip.
4. **Storage invariants:** separate record identity from version identity; permit
   history with exactly one active version; add real foreign keys; preserve
   subtype fields during closure; use explicit migration transactions and files.
   Replace dynamic table/column SQL with allowlists. Commit a blob only after
   created → stored → verified, persist its vault identity, use a keyed digest,
   and restrict audit reasons to content-free enums.
5. **Policy lineage:** material third-party involvement must remain `MATERIAL`
   when combined with `NONE`. Test the normative rule, not the broken result.
6. **Synthetic boundary/CLI:** enforce an unforgeable internal bundled-fixture
   authority at the storage write boundary. Remove success stubs: every command
   must perform and verify its operation or return a non-zero fail-closed result.
7. **Validators/evidence:** validators must be read-only and behavioral. They
   must reject missing/empty/label-only evidence, validate emitted backup/export
   artifacts against their schemas, require real migrations/fixtures, and
   reconcile the SBOM with `uv.lock`. Do not create evidence while validating.
8. **Provenance/filesystem:** validate edge kind and both endpoints at mutation;
   implement contradiction/supersession semantics; hash canonical nested JSON.
   Close the remaining symlink/reparse replacement race with handle-relative or
   equivalent no-follow filesystem operations.
9. **Relevant static defects:** fix non-strict row/column `zip`, validate export
   magic and restore format version, remove the duplicate digest definition, and
   correct security-boundary typing in unit-of-work and AES-GCM imports. Do not
   spend time on unrelated style-only or out-of-boundary type cleanup.

## Proof required

Add small negative regression tests that exercise the real production paths for
each item above. Include adversarial evidence for partial backup, populated-target
restore, unsupported recovery version, excessive KDF values, empty/ambiguous
SQLCipher evidence, direct write without fixture authority, success-stub CLI,
dangling provenance edges, and validator false passes.

Run targeted tests while repairing, then run the repository's final E00 gate
once. Update the implementation and repair reports with actual outputs. Leave
`STATE.yaml` at `IMPLEMENTED / REVIEW_REQUIRED` for independent re-acceptance;
do not create an accepted commit and do not prepare E01.
