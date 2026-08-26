# Personal Data Safety V1 — exact candidate proof

Candidate `1cfca99daf5ff2a87a9abfc9efd006edd7d59139` was built from a clean detached worktree on Windows x86_64 using `desktop/scripts/build-personal.ps1 -BoundedOpenAI`.

The exact NSIS installer is `PSYCHE OS Personal_0.2.0_x64-setup.exe`, SHA-256 `0ebd9fbb4622156e729a041115e92c7e062333c81a9e9a371d6b6020505b4b99`. Its embedded build ID is the candidate SHA; its embedded runtime profile is `local_personal_bounded_openai_reflection_windows_v1`, whose LF-normalized digest is `1b91fad63ad04e02e90f9cae70d8d5d36a9a66ec9f00d1002cded853726ca99a`. `UNBOUND` is absent.

`scripts/dev/verify_personal_package_inventory.py` passed for the bounded OpenAI profile. The inspection proved the Personal sidecar inventory, expected bounded adapter-only modulegraph, typed command table, forbidden renderer-surface exclusion, and fixed Responses endpoint invariants. Installer listing contains no `.env` or vault/test-vault entries; an installer byte scan found no `OPENAI_API_KEY`, recovery-secret, or DPAPI plaintext marker.

Targeted synthetic lifecycle proof passed: `38 passed in 44.24s` across integrity, key-envelope, recovery-bootstrap, V11 lifecycle/rotation/reconciliation, V10 migration, and reflection runtime tests. It covers valid V11 verification, wrong recovery secret/key failure, schema/FK drift failure, encrypted backup authentication plus isolated restore, V10→V11 migration, no orphan provenance/source-turn links, non-activating restore inspection, and failure-atomic rotation publication states. SQLCipher's keyed `PRAGMA cipher_integrity_check` is used when supported; its non-`ok` result fails closed, while SQLite integrity and FK checks are separately required.

No real Personal data, owner installation, or OpenAI live request was used. Installed-product smoke remains deferred because no existing installed-app smoke mechanism can cover the complete lifecycle without creating new E2E infrastructure.
