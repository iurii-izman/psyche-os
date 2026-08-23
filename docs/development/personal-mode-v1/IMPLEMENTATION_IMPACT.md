# Bounded implementation impact (not authorization)

The future, separately authorized implementation requires focused Personal modules: `src/psyche_os/personal_mode/key_envelope.py`, `key_rotation.py`, `admission.py`, and `runtime_profile.py`; V10 migration surfaces; storage connection handling; backup/export operations and versioning; desktop service/sidecar/E11 admission integration; Tauri/profile allowlists; packaging; and focused synthetic tests. The expected scope is enumerated in the DRAFT contract.

Required acceptance includes safe SQLCipher key rotation, recoverable N or N+1 at every crash stage, no active DB without recoverable matching envelope, recoverable old backup after rotation, all Personal reads/writes blocked on expired admission, bootstrap swap/tamper rejection, and exact E11 review-ID compatibility. No production path is authorized until an independently reviewed architecture and explicitly approved ACTIVE contract exist.
