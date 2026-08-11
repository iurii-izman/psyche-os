"""PSYCHE OS — F0 Minimal Irreversible Secure Core CLI entry point.

Synthetic-only. No network, no LLM, no provider calls.
REAL_DATA_GATE is CLOSED.
"""

from __future__ import annotations

import sys


def main() -> int:
    """Entry point for `psyche-os` CLI."""
    from psyche_os.interfaces.cli import create_cli

    cli = create_cli()
    return cli.run(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
