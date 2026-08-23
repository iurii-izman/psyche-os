# Runtime profile and package isolation

The requested profile is `local_personal_evidence_reflection_windows_v1`. Rust accepts a requested profile but is the boundary authority: it computes an effective profile only after Python sidecar admission confirms `REAL_DATA_GATE` and an exact evaluation/attestation. Renderer input is untrusted; it receives only capability/status DTOs and cannot select `LOCAL_PERSONAL`, alter data mode, execute generic sidecar commands, or write SQL.

Personal v1 allows unlock/lock, Quick Capture, Reflection sessions and turns, bounded local search, Guided Exploration/Working Formulation as clearly labelled proposals, actions/outcomes, correction/history, deletion, encrypted backup/recovery/export and restart persistence. Search/list UI is a local workspace view, not a longitudinal/Return/Follow-up workflow.

Excluded and denied at Rust command allowlist, typed Python dispatcher, renderer routing, and shipped package inventory: provider/model/network/telemetry/sync; Longitudinal/N-of-1, Review Hub/Return/Follow-up cross-session workflows; importer/parser/untrusted rendering; assessment/scoring; professional report/external handoff; general blob/attachment writes. The implementation must make excluded modules/commands unreachable and absent from the Personal package where the profile requires package exclusion; an environment `OPENAI_API_KEY` is neither read nor forwarded.

Tests must prove: forged renderer profile/AI/longitudinal/import requests deny; no provider construction/transport call/credential forwarding; package artifact and sidecar inventories omit importer/render capability; direct backend call rechecks effective profile; and all denials are content-free.
