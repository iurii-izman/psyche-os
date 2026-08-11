# E00 final repair calibration

## Result

The final repair remains bounded to F02, F05, F07, F08, and F09. The
Constitution, v2 master specification, accepted threat model, ADRs, and frozen
F0/E00 contract support the proposed F07 and F09 clarifications; no architecture
deviation is required.

## F07 calibration

The synthetic-fixture authorization control protects the supported application
and storage mutation path against ordinary callers, imported/untrusted input,
direct unauthorized UoW use, and forged, copied, uninitialized, or serialized
capabilities. Only the package-owned, manifest-verifying bundled-fixture loader
may obtain and consume valid authority, and storage must validate it before any
mutation.

This control does not claim to remain unforgeable after arbitrary code execution,
unrestricted monkey-patching/introspection, process-memory access, trusted-package
replacement, or Administrator/SYSTEM compromise. Those attacks are not removed
from the repository threat model: same-user malware and supply-chain execution
remain Critical/residual system risks. The clarification only avoids presenting
one in-process capability as their complete mitigation.

## F09 calibration

The F0 filesystem control protects the supported Windows vault boundary against
ordinary traversal, junction/reparse redirection, and pathname swap/TOCTOU
attacks. All public read, write, text, delete, and atomic-replace operations must
use one minimal handle-bound implementation that validates the actual opened
object and relevant parent containment. A pathname `realpath` check followed by
a later pathname operation is insufficient.

The control does not promise resistance to Administrator/SYSTEM, a hostile
kernel/filesystem driver, trusted-process arbitrary execution, or replacement of
trusted package code. These remain deployment/endpoint or supply-chain risks,
not properties solved by the F09 adapter. No generic cross-platform filesystem
framework is requested.

## Preserved requirements

- F02 remains exact and fail closed: authenticated inventory/manifest, exact
  versions/checksums/counts, wrong-key and tamper rejection, isolated atomic
  restore, and complete encrypted round trip.
- F05 remains an irreversible foundation: consistent historical versioning,
  one active version, referential/SQL safety, transactional migration artifacts,
  and vault-bound `CREATED → STORED → VERIFIED` blobs.
- F08 remains behavioral and read-only: production artifacts validated with JSON
  Schema, temporary-database migrations, production fixture authority, exact
  SBOM/lock reconciliation, and structured accepted SQLCipher evidence.
- F01, F03, F04, and F06 remain accepted and are not reopened without a direct
  regression caused by the final repair.

Tests remain risk-based and map one-to-one to demonstrated failure modes. No
arbitrary coverage target, impossible absolute security promise, new research,
or architecture expansion was introduced.
