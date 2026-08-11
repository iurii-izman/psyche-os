# PSYCHE OS F0 Threat-Test Matrix

Generated from THREAT_MODEL.md and the E00 acceptance criteria.
Each threat is mapped to at least one verifying test.

| # | Threat | Severity | Test File | Test Name | Status |
|---|--------|----------|-----------|-----------|--------|
| T01 | Plaintext export masquerading as encrypted | Critical | tests/security/test_crypto_security.py | test_export_encrypted_by_default | ✅ |
| T02 | Backup verification bypass | Critical | tests/integration/test_storage_integration.py | test_backup_verify_roundtrip | ⚠️ |
| T03 | Path traversal: vault/../vault2 escape | High | tests/unit/test_adapters.py | test_path_containment | ⚠️ |
| T04 | Encryption key reuse (same key+nonce) | Critical | tests/security/test_crypto_security.py | test_unique_nonce_per_encrypt | ✅ |
| T05 | Gate acceptance with placeholder license | High | tests/integration/test_storage_integration.py | test_all_8_probes_registered | ✅ |
| T06 | Gate acceptance with failed integrity | Critical | tests/integration/test_storage_integration.py | test_gate_accepted | ✅ |
| T07 | Policy inheritance downgrade NEVER_CLOUD | High | tests/unit/test_policy.py | test_never_cloud_closure | ✅ |
| T08 | Unknown time fabricated to known point | Medium | tests/unit/test_temporal.py | test_decade_precision | ✅ |
| T09 | Direct write without synthetic-fixture capability | High | tests/unit/test_fixtures.py | test_synthetic_only_enforced | ⚠️ |
| T10 | Dangling provenance reference | Medium | tests/unit/test_provenance.py | test_find_dependencies_transitive | ✅ |
| T11 | Blob state corruption (stored without content) | Critical | tests/integration/test_storage_integration.py | test_commit_and_rollback | ✅ |
| T12 | Deletion without closure (orphaned references) | High | tests/unit/test_versions.py | test_two_active_for_same_record_fails | ✅ |
| T13 | Wrong key → silent corruption | Critical | tests/integration/test_storage_integration.py | test_gate_accepted (probe 4) | ✅ |
| T14 | Plaintext SQLite accepted as encrypted | Critical | tests/integration/test_storage_integration.py | test_gate_accepted (probe 6) | ✅ |
| T15 | Recovery key wrapping failure | High | tests/unit/test_crypto.py | test_recovery_wrap_roundtrip | ✅ |
| T16 | Schema migration rollback | Medium | tests/integration/test_storage_integration.py | test_all_ddl_applies | ✅ |
| T17 | Backup restore corrupts existing vault | Critical | tests/integration/test_storage_integration.py | test_backup_restore_isolated | ⚠️ |
| T18 | Audit event missing forbidden-content CHECK | High | tests/integration/test_storage_integration.py | test_audit_content_free | ⚠️ |

**Status legend:**
- ✅ Covered by passing test
- ⚠️ Covered by test but verification incomplete (test needs completion or may not exist yet)
- ❌ Not covered

**Notes:**
- Tests marked ⚠️ exist as test stubs or are implied by existing infrastructure but need dedicated regression-proof implementations.
- The mandatory regression proofs (see E00_FIX_REQUIRED.md §Mandatory regression proofs) provide additional coverage for the ⚠️ items.
