# PSYCHE OS — F0 Minimal Irreversible Secure Core

Personal Evidence & Reflection System.

**Status:** Pre-Alpha / Synthetic Only
**REAL_DATA_GATE:** CLOSED

## Overview

PSYCHE OS is a hybrid bitemporal relational canonical store for evidence management.
The F0 release implements the minimal irreversible secure core:

- Opaque 128-bit UUID identifiers
- Versioned rows with half-open transaction intervals
- Orthogonal data policy with NEVER_CLOUD transitive inheritance
- 256-bit Vault Master Key with domain-separated derivation
- Windows DPAPI convenience wrapping + independent Argon2id recovery
- SQLCipher encrypted storage (8-probe gate)
- Independently authenticated encrypted blob envelopes
- Content-free allowlisted audit
- Hard deletion with dependency graph traversal
- Authenticated encrypted backup and isolated restore

## Quick Start

```bash
pip install -e .
psyche-os version
psyche-os gate status
psyche-os vault create
```

## License

MIT
