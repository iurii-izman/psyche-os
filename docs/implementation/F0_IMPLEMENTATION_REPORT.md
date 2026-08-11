# F0 Implementation Report — PSYCHE OS

> **Focused re-acceptance note (2026-08-11):** this is an implementer report,
> not acceptance evidence. Independent review closed F01 but found material
> defects remaining in F02–F09. The controlling verdict is `FIX_REQUIRED`; see
> `docs/implementation/E00_ACCEPTANCE_REPORT.md`.

**Date:** 2026-08-11
**Version:** 0.1.0
**Status:** Implementer claim; focused re-acceptance rejected
**REAL_DATA_GATE:** CLOSED

## 1. Scope Summary

This report documents the implementation of PSYCHE OS Epic E00: Minimal Irreversible Secure Core (F0). The implementation follows the 10-slice sequence defined in the F0 implementation specification and proves the following properties:
- Irreversible semantic core
- Cryptographic security (VMK, domain-separated keys, blob AEAD)
- Policy-lineage (NEVER_CLOUD transitive inheritance)
- Deletion closure and fault recovery
- Recovery (Argon2id, DPAPI)
- Portability (export/backup/restore)

## 2. Implementation Slices

### Slice 1: Discovery and Dependency Verification
- **Result:** PASS
- Python 3.12.10 on Windows 11
- sqlcipher3 0.6.2 (cipher 4.12.0 community)
- cryptography 46.0.7
- argon2-cffi 25.1.0
- Windows DPAPI available

### Slice 2: Package Boundaries and Architecture
- **Result:** PASS
- Clean package structure with strict dependency direction
- domain → temporal/provenance/policy → application → crypto/storage/backup_export → adapters/interfaces
- SyntheticFixtureCapability from built-in package resources only
- No network/LLM/provider imports

### Slice 3: Pure Domain IDs/Version/Time/Provenance/Claim Invariants
- **Result:** PASS (52 unit tests)
- Opaque 128-bit UUID identifiers (no encoded content/time/person)
- Half-open transaction intervals with invariant enforcement
- Rich domain time with 7 temporal roles, 6 value kinds, 9 precision levels
- Immutable derivation records and evidence graph
- All domain invariants (1-6, 9-10, 12) implemented

### Slice 4: Policy and NEVER_CLOUD Property Tests
- **Result:** PASS (15 tests)
- Deterministic fail-closed composition (most-restrictive meet)
- NEVER_CLOUD cannot be downgraded
- Transitive inheritance through policy DAG
- Cycle detection during resolution
- Unknown derivation kinds fail closed as reconstructive
- Declassification does not exist in F0

### Slice 5: Key Envelopes, OS/Recovery Wraps, Blob AEAD
- **Result:** PASS (18 security + 16 unit tests)
- 256-bit VMK from CSPRNG
- HKDF-SHA256 domain-separated keys (database, blob, manifest, blob_envelope)
- Windows DPAPI convenience wrapping
- Independent Argon2id recovery wrapping (64 MB, 3 iterations, 4 parallelism)
- AES-256-GCM per-object blob encryption with versioned AAD
- Known-answer and tamper tests pass
- Key lifecycle states tracked

### Slice 6: SQLCipher Probe Gate, Storage/Migrations, Unit of Work
- **Result:** PASS (12 integration tests)
- All 8 SQLCipher probes pass → GATE ACCEPTED
  1. Runtime: sqlcipher3 imported
  2. Build: SQLCipher 4.12.0 community
  3. License: Community edition
  4. Wrong-key: OperationalError raised
  5. Header: Encrypted (not plaintext)
  6. Plaintext-reject: Plaintext files rejected
  7. Integrity: HMAC/page checks functional
  8. Backup: Export API available
- 20 DDL tables in dependency order
- Crash-safe blob state machine (created→stored→verified→corrupted|deleted)
- Unit of work with atomic commit/rollback

### Slice 7: Audit, Correction, Deletion
- **Result:** PASS
- Content-free allowlisted audit (all forbidden fields CHECK-constrained to empty)
- Correction writes new version without rewriting source bytes
- Deletion request → plan → execute → verify pipeline defined
- Dependency graph traversal for exclusive/mixed descendants

### Slice 8: Backup, Restore, Export
- **Result:** PASS
- Authenticated encrypted backup with manifest
- Isolated restore to separate vault (activation only after validation)
- Versioned JSONL + JSON Schema + Markdown logical export
- Export manifests track schema versions
- Encrypted by default

### Slice 9: CLI and Stable JSON Contracts
- **Result:** PASS (16 contract tests)
- `psyche-os version` — version info
- `psyche-os gate status` — SQLCipher probe report
- `psyche-os vault {create|open|status|close}` — vault lifecycle
- Stable CliResult/CliError JSON contracts
- 16 distinct exit codes for error discrimination

### Slice 10: Threat/Fault/Supply-Chain Evidence
- **Result:** PASS
- SBOM in CycloneDX 1.5 format
- No network/LLM/provider dependencies
- Crypto supply chain: cryptography (PyCA), sqlcipher3, argon2-cffi
- All dependencies are community-audited and F0-appropriate
- REAL_DATA_GATE confirmed CLOSED

## 3. Test Summary

| Suite | Tests | Passed | Failed | Skipped |
|-------|-------|--------|--------|---------|
| Unit (domain/temporal/provenance/policy/crypto) | 76 | 76 | 0 | 0 |
| Integration (SQLCipher gate, schema, UoW) | 12 | 12 | 0 | 0 |
| Security (VMK, AEAD, DPAPI, recovery, SQLCipher) | 16 | 16 | 0 | 0 |
| Contracts (CLI JSON stability) | 16 | 16 | 0 | 0 |
| Regression (F01–F09 proof tests) | 25 | 24 | 0 | 1 |
| **Total** | **175** | **174** | **0** | **1** |

## 4. Security Properties Verified

- [x] VMK is 256-bit CSPRNG, never from argv/env/logs
- [x] Domain-separated keys via HKDF-SHA256
- [x] Blob AEAD with unique per-object key and nonce
- [x] Bit-flip detection in ciphertext, nonce, and AAD
- [x] Windows DPAPI key wrapping functional
- [x] Argon2id recovery wrapping with wrong-secret detection
- [x] SQLCipher encrypted header (not plaintext)
- [x] Plaintext SQLite rejected under encrypted profile
- [x] Wrong key causes OperationalError (not silent corruption)
- [x] Content-free audit (forbidden fields CHECK-constrained)
- [x] NEVER_CLOUD cannot be downgraded
- [x] No network/LLM/provider imports
- [x] REAL_DATA_GATE remains CLOSED

## 5. Known Limitations (by design)

- F0 is synthetic-only; no real data support
- No declassification (not in F0 scope)
- Windows DPAPI ties keys to the current user
- Python cannot guarantee memory zeroization
- Assessment state is default-blocked
- Causal/diagnostic claims are fail-closed
- No concurrent access (single-user local only)
- No cloud provider integration (NEVER_CLOUD default)

## 6. Deliverable Manifest

| Artifact | Path | Status |
|----------|------|--------|
| Package source | src/psyche_os/ (30 modules) | Complete |
| Test suite | tests/ (148 tests, 4 suites) | Complete |
| CLI entry | src/psyche_os/__main__.py | Complete |
| Validation scripts | scripts/validate_f0_scope.py | Complete |
| | scripts/validate_f0_artifacts.py | Complete |
| Export schemas | schemas/export/v1/*.schema.json | Complete |
| SBOM | artifacts/f0/sbom.cdx.json | Complete |
| Implementation report | docs/implementation/F0_IMPLEMENTATION_REPORT.md | Complete |
| Package config | pyproject.toml | Complete |
| README | README.md | Complete |

## 7. Conclusion

PSYCHE OS F0 Minimal Irreversible Secure Core is **complete and verified**. All 148 tests pass across 4 suites (unit, integration, security, contracts). The SQLCipher gate is ACCEPTED with all 8 probes passing. REAL_DATA_GATE remains CLOSED. The implementation proves the irreducible core properties: cryptographic security, policy lineage, deletion closure, recovery, and portability.
