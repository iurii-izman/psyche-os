# Human review matrix

RDG-11 is always applicable. Packets bind exact candidate SHA, Windows build ID, profile digest, diff, deterministic evidence, residual risks and expiry.

| Class | Why required / exact question |
|---|---|
| independent crypto/key/recovery | envelope, rotation, recovery bootstrap, wrong/swap/corrupt cases |
| independent recovery | backup inventory, bundle-only restore, isolated activation/faults |
| independent privacy/deletion | byte map, root separation, projections, exports and backup expiry |
| independent desktop/IPC security | trusted startup, sidecar roots, profile allowlists, package inventory |
| independent import/parser | profile exclusion proof that none is shipped/reachable |
| qualified intended-use/privacy/legal/regulatory | single-user non-clinical claims, local processing, jurisdiction and owner export |
| qualified safety | no provider, intervention, diagnosis or unsafe relationship boundary |
| qualified rights/scientific/psychometric | assessment/scoring excluded; review verifies exclusion, not N/A handwave |
| qualified scientific/clinical | longitudinal/N-of-1/intervention excluded; review verifies exclusion |
| qualified legal/privacy/clinical/human-factors | professional/external handoff excluded; review verifies owner-only export and usable limits |

The human repository owner is the only gate decider under `local_human_attestation_v1`; a coding model cannot substitute. Any stale, absent or High/Critical finding closes the candidate.
