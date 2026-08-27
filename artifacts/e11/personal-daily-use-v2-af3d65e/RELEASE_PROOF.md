# Personal Daily Use Release V2 — exact candidate proof

Candidate/build: `af3d65e5401c3cfeb3ca4412f6e210674c1612a3` on Windows x86_64.
Profile: `local_personal_bounded_openai_reflection_windows_v1` with LF-normalized
digest `1b91fad63ad04e02e90f9cae70d8d5d36a9a66ec9f00d1002cded853726ca99a`.

The exact NSIS installer is `PSYCHE OS Personal_0.2.0_x64-setup.exe`, SHA-256
`c8c750aa56f46710c09fa3fcb8a0714cad3b92edd113a28e610b40d44466d142`.
Extracted package bytes contain the exact candidate build ID, profile ID, and
profile digest; `UNBOUND`, `OPENAI_API_KEY`, recovery-secret, and DPAPI markers
are absent.

Observed deterministic results:

- Personal frontend: typecheck and lint passed; unit suite passed, 68 tests.
- Personal product gates: 160 synthetic tests passed, covering Evidence Workspace
  source/derived/AI provenance, exact source navigation, formulation lifecycle
  and correction, Longitudinal history, Context & Retrieval, bounded AI preview /
  one-call authorization boundaries, integrity, recovery, and V10/V11 lifecycle
  regressions.
- Rust canonical check and test passed; Rust test suite passed, 12 tests.
- `scripts/dev/verify_personal_package_inventory.py` passed for the bounded OpenAI
  profile: Personal sidecar-only installer inventory, renderer/command boundary,
  frozen modulegraph, and fixed bounded provider invariants.
- Candidate-range Gitleaks scan and canonical repository secret validation passed;
  package byte scans found no secret markers.

No live OpenAI request, real Personal data, owner installation, schema migration,
cryptography/key change, permission expansion, or network expansion was used.
The predecessor evidence for encryption/key lifecycle, recovery, backup/restore,
V10/V11 compatibility, deletion/provenance, DPAPI, and bounded provider
constraints remains applicable; this proof supplies new candidate-bound package
and deterministic product evidence.
