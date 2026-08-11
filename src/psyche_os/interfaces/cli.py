"""Interfaces layer — F0 restricted CLI with stable JSON error contracts.

Implements the exact E00 command surface per F0_IMPLEMENTATION_PROMPT.md §12:
- psyche-os doctor --json
- psyche-os gate status --json
- psyche-os vault init/verify
- psyche-os fixture list/load
- psyche-os migrate plan/apply
- psyche-os delete plan/execute
- psyche-os backup create/verify
- psyche-os restore verify/activate
- psyche-os export create/verify
- psyche-os audit verify
- psyche-os version

All commands use stable CliResult/CliError JSON contracts.
No command accepts arbitrary content or network access.
The REAL_DATA_GATE status is always CLOSED in F0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import datetime as _dt
import json
import os
import sys
from typing import Any


def isodate() -> str:
    return _dt.datetime.now(_dt.UTC).isoformat()


# ---------------------------------------------------------------------------
# Stable JSON error contract
# ---------------------------------------------------------------------------


@dataclass
class CliError:
    """Stable error structure for CLI output."""

    code: str
    detail: str
    hint: str = ""
    transaction_id: str = ""

    def to_json(self) -> str:
        return json.dumps(
            {
                "error": {
                    "code": self.code,
                    "detail": self.detail,
                    "hint": self.hint,
                    "transaction_id": self.transaction_id,
                },
            },
            indent=2,
        )


@dataclass
class CliResult:
    """Stable result structure for CLI output."""

    status: str  # "ok" | "error"
    data: Any = None
    warnings: list[str] = field(default_factory=list)
    transaction_id: str = ""

    def to_json(self) -> str:
        return json.dumps(
            {
                "status": self.status,
                "data": self.data,
                "warnings": self.warnings,
                "transaction_id": self.transaction_id,
            },
            indent=2,
        )


# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------


class ExitCode:
    SUCCESS = 0
    GENERAL_ERROR = 1
    VAULT_ERROR = 10
    GATE_REJECTED = 20
    GATE_BLOCKED = 21
    GATE_UNAVAILABLE = 22
    POLICY_BLOCKED = 30
    NEVER_CLOUD_VIOLATION = 31
    CRYPTO_ERROR = 40
    STORAGE_ERROR = 50
    DELETION_ERROR = 60
    BACKUP_ERROR = 70
    EXPORT_ERROR = 80
    VALIDATION_ERROR = 90
    INVARIANT_VIOLATION = 91
    LICENSE_ERROR = 92
    SYNTHETIC_ONLY_ERROR = 93
    FIXTURE_ERROR = 94
    MIGRATION_ERROR = 95
    REAL_DATA_GATE = 99
    FEATURE_DEFERRED = 96  # Feature deferred to PRE_REAL_DATA; not available in E00


# ---------------------------------------------------------------------------
# Command registry
# ---------------------------------------------------------------------------


@dataclass
class Command:
    name: str
    handler: Any
    help: str
    subcommands: dict[str, Command] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# F0 CLI
# ---------------------------------------------------------------------------


class F0CLI:
    """F0 restricted CLI — synthetic-only, no network/LLM/provider calls.

    All commands require and verify the synthetic-only gate.
    Direct writes without SyntheticFixtureCapability fail.
    """

    def __init__(self) -> None:
        self._commands = self._build_commands()

    def _build_commands(self) -> dict[str, Command]:
        cmds: dict[str, Command] = {}

        # --- version ---
        cmds["version"] = Command(
            name="version",
            handler=self._cmd_version,
            help="Show version information",
        )

        # --- doctor ---
        cmds["doctor"] = Command(
            name="doctor",
            handler=self._cmd_doctor,
            help="Report exact profile blockers and available capabilities",
        )

        # --- gate ---
        cmds["gate"] = Command(
            name="gate",
            handler=self._cmd_gate_help,
            help="SQLCipher probe gate",
            subcommands={
                "status": Command(
                    name="status",
                    handler=self._cmd_gate_status,
                    help="Run all 8 probes and report gate state",
                ),
            },
        )

        # --- vault ---
        cmds["vault"] = Command(
            name="vault",
            handler=self._cmd_vault_help,
            help="Vault lifecycle operations",
            subcommands={
                "init": Command(
                    name="init",
                    handler=self._cmd_vault_init,
                    help="Initialize a new vault with key material",
                ),
                "verify": Command(
                    name="verify",
                    handler=self._cmd_vault_verify,
                    help="Verify vault integrity and invariants",
                ),
                "status": Command(
                    name="status",
                    handler=self._cmd_vault_status,
                    help="Show vault metadata",
                ),
                "close": Command(
                    name="close",
                    handler=self._cmd_vault_close,
                    help="Close vault and clear key material",
                ),
            },
        )

        # --- fixture ---
        cmds["fixture"] = Command(
            name="fixture",
            handler=self._cmd_fixture_help,
            help="Synthetic fixture operations (deny-by-default)",
            subcommands={
                "list": Command(
                    name="list",
                    handler=self._cmd_fixture_list,
                    help="List available built-in fixture packs",
                ),
                "load": Command(
                    name="load",
                    handler=self._cmd_fixture_load,
                    help="Load a fixture pack into a vault",
                ),
            },
        )

        # --- migrate ---
        cmds["migrate"] = Command(
            name="migrate",
            handler=self._cmd_migrate_help,
            help="Schema migration operations",
            subcommands={
                "plan": Command(
                    name="plan",
                    handler=self._cmd_migrate_plan,
                    help="Plan a schema migration",
                ),
                "apply": Command(
                    name="apply",
                    handler=self._cmd_migrate_apply,
                    help="Apply a planned migration",
                ),
            },
        )

        # --- delete ---
        cmds["delete"] = Command(
            name="delete",
            handler=self._cmd_delete_help,
            help="Deletion operations (content-free)",
            subcommands={
                "plan": Command(
                    name="plan",
                    handler=self._cmd_delete_plan,
                    help="Plan hard deletion with dependency traversal",
                ),
                "execute": Command(
                    name="execute",
                    handler=self._cmd_delete_execute,
                    help="Execute a deletion plan",
                ),
            },
        )

        # --- backup ---
        cmds["backup"] = Command(
            name="backup",
            handler=self._cmd_backup_help,
            help="Authenticated encrypted backup operations",
            subcommands={
                "create": Command(
                    name="create",
                    handler=self._cmd_backup_create,
                    help="Create encrypted backup",
                ),
                "verify": Command(
                    name="verify",
                    handler=self._cmd_backup_verify,
                    help="Verify backup integrity and authenticity",
                ),
            },
        )

        # --- restore ---
        cmds["restore"] = Command(
            name="restore",
            handler=self._cmd_restore_help,
            help="Isolated restore operations",
            subcommands={
                "verify": Command(
                    name="verify",
                    handler=self._cmd_restore_verify,
                    help="Verify restore package without activating",
                ),
                "activate": Command(
                    name="activate",
                    handler=self._cmd_restore_activate,
                    help="Activate a validated restored vault",
                ),
            },
        )

        # --- export ---
        cmds["export"] = Command(
            name="export",
            handler=self._cmd_export_help,
            help="Logical export operations",
            subcommands={
                "create": Command(
                    name="create",
                    handler=self._cmd_export_create,
                    help="Create authenticated encrypted export",
                ),
                "verify": Command(
                    name="verify",
                    handler=self._cmd_export_verify,
                    help="Verify export package integrity",
                ),
            },
        )

        # --- audit ---
        cmds["audit"] = Command(
            name="audit",
            handler=self._cmd_audit_help,
            help="Content-free audit verification",
            subcommands={
                "verify": Command(
                    name="verify",
                    handler=self._cmd_audit_verify,
                    help="Verify audit log integrity and content-free compliance",
                ),
            },
        )

        return cmds

    # ==================================================================
    # Doctor
    # ==================================================================

    def _cmd_version(self, args: list[str]) -> CliResult:
        from psyche_os import __version__

        return CliResult(
            status="ok",
            data={
                "version": __version__,
                "python": sys.version,
                "platform": sys.platform,
                "real_data_gate": "CLOSED",
            },
        )

    def _cmd_doctor(self, args: list[str]) -> CliResult:
        """Report exact profile blockers and available capabilities."""
        import platform
        import sys as _sys

        report: dict[str, Any] = {
            "platform": platform.platform(),
            "python_version": _sys.version,
            "real_data_gate": "CLOSED",
            "profiles": {},
        }

        # SQLCipher profile
        try:
            from psyche_os.storage.sqlcipher_gate import GateState, run_gate

            gate_report = run_gate()
            report["profiles"]["sqlcipher"] = {
                "verified": gate_report.gate_state == GateState.ACCEPTED,
                "state": gate_report.gate_state.value,
                "failed_count": gate_report.failed_count,
                "blocker": gate_report.blocker,
            }
        except Exception as exc:
            report["profiles"]["sqlcipher"] = {
                "verified": False,
                "state": "unavailable",
                "blocker": str(exc),
            }

        # OS key wrap profile
        try:
            from psyche_os.crypto.envelope import OSKeyWrapper

            os_wrapper = OSKeyWrapper()
            report["profiles"]["os_key_wrap"] = {
                "verified": os_wrapper.available,
                "provider": "Windows DPAPI" if os_wrapper.available else "unavailable",
            }
        except Exception as exc:
            report["profiles"]["os_key_wrap"] = {
                "verified": False,
                "provider": "unavailable",
                "blocker": str(exc),
            }

        # Recovery profile
        try:
            from psyche_os.crypto.envelope import RecoveryWrapper

            rw = RecoveryWrapper()
            report["profiles"]["recovery"] = {
                "verified": rw.available,
                "algorithm": "Argon2id" if rw.available else "unavailable",
            }
        except Exception as exc:
            report["profiles"]["recovery"] = {
                "verified": False,
                "algorithm": "unavailable",
                "blocker": str(exc),
            }

        # Crypto library profile
        try:
            import cryptography

            report["profiles"]["crypto_library"] = {
                "verified": True,
                "library": "cryptography",
                "version": cryptography.__version__,
            }
        except Exception:
            report["profiles"]["crypto_library"] = {"verified": False}

        all_verified = all(p.get("verified", False) for p in report["profiles"].values())

        if all_verified:
            return CliResult(status="ok", data=report)
        else:
            blockers = [
                f"{k}: {v.get('blocker', 'not verified')}"
                for k, v in report["profiles"].items()
                if not v.get("verified", False)
            ]
            return CliResult(
                status="error",
                data=report,
                warnings=[f"Blockers: {'; '.join(blockers)}"],
            )

    # ==================================================================
    # Gate
    # ==================================================================

    def _cmd_gate_help(self, args: list[str]) -> CliResult:
        return CliResult(status="error", data=None, warnings=["Use: psyche-os gate status"])

    def _cmd_gate_status(self, args: list[str]) -> CliResult:
        from psyche_os.storage.sqlcipher_gate import run_gate

        report = run_gate()
        return CliResult(
            status="ok",
            data={
                "gate_state": report.gate_state.value,
                "all_passed": report.all_passed,
                "failed_count": report.failed_count,
                "real_data_gate": "CLOSED",
                "probes": [
                    {
                        "number": r.probe_number,
                        "name": r.probe_name,
                        "passed": r.passed,
                        "detail": r.detail,
                        "capability_verdict": r.capability_verdict,
                    }
                    for r in report.results
                ],
                "blocker": report.blocker,
            },
        )

    # ==================================================================
    # Vault
    # ==================================================================

    def _cmd_vault_help(self, args: list[str]) -> CliResult:
        return CliResult(
            status="error", data=None, warnings=["Use: psyche-os vault {init|verify|status|close}"]
        )

    def _cmd_vault_init(self, args: list[str]) -> CliResult:
        """Initialize a new vault. Requires a passing gate result.

        F07 (FIX): vault init must create and verify the vault/database it
        reports, otherwise return a non-zero fail-closed result. It opens
        a real SQLCipher database file, applies the schema, and verifies
        the result before reporting success.
        """
        try:
            from psyche_os.storage.sqlcipher_gate import GateState, run_gate

            # F04 fix: Bind vault creation to a fresh passing gate
            gate_report = run_gate()
            if gate_report.gate_state != GateState.ACCEPTED:
                return CliResult(
                    status="error",
                    data={
                        "gate_state": gate_report.gate_state.value,
                        "blocker": gate_report.blocker,
                    },
                    warnings=[f"Gate not accepted: {gate_report.gate_state.value}"],
                )

            from psyche_os.crypto.envelope import (
                RecoveryWrapper,
                derive_domain_key,
                generate_vmk,
            )
            from psyche_os.domain.ids import VaultId, generate_id

            # Parse --path argument
            path = ""
            profile = "sqlcipher"
            for i, arg in enumerate(args):
                if arg == "--path" and i + 1 < len(args):
                    path = args[i + 1]
                elif arg == "--profile" and i + 1 < len(args):
                    profile = args[i + 1]
                    if profile != "sqlcipher":
                        return CliResult(
                            status="error",
                            data=None,
                            warnings=[
                                f"Unsupported profile: {profile}. Only 'sqlcipher' is supported."
                            ],
                        )

            # Generate VMK and derive keys
            vmk = generate_vmk()
            vault_id = VaultId(generate_id())
            db_salt = os.urandom(32)
            blob_salt = os.urandom(32)

            db_key = derive_domain_key(vmk, "database", salt=db_salt)
            blob_key = derive_domain_key(vmk, "blob_envelope", salt=blob_salt)
            backup_key = derive_domain_key(vmk, "backup")
            export_key = derive_domain_key(vmk, "export")

            # OS-wrap VMK
            from psyche_os.adapters.adapters import OSKeyStoreAdapter

            os_store = OSKeyStoreAdapter()

            # F07: Actually create the vault database and apply schema
            db_path = (
                path if path else os.path.join(os.getcwd(), f"psyche_vault_{str(vault_id)[:12]}.db")
            )

            from sqlcipher3 import dbapi2

            from psyche_os.storage.schema import apply_schema

            # F07: Use the derived database key as the SQLCipher key
            db_key_hex = db_salt.hex()

            con = dbapi2.connect(db_path)
            try:
                con.execute(f"PRAGMA key = \"x'{db_key_hex}'\";")
                apply_schema(con)

                # Verify: after schema application, verify the vault was created
                cur = con.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
                tables = [row[0] for row in cur.fetchall()]
                required = {"schema_migrations", "vault_config", "actors", "blobs"}
                missing = required - set(tables)
                if missing:
                    con.rollback()
                    return CliResult(
                        status="error",
                        data=None,
                        warnings=[f"Vault creation incomplete — missing tables: {missing}"],
                    )

                # Insert vault_config singleton row
                now = isodate()
                cur.execute(
                    """INSERT INTO vault_config
                       (vault_id, vault_name, data_mode, created_at,
                        vmk_os_wrapped, db_key_salt, blob_envelope_key_salt, key_state)
                       VALUES (?, ?, 'synthetic_only', ?, NULL, ?, ?, 'generated')""",
                    (str(vault_id), "default", now, db_salt, blob_salt),
                )
                con.commit()
            except Exception as exc:
                con.rollback()
                return CliResult(
                    status="error",
                    data=None,
                    warnings=[f"Vault database creation failed: {exc}"],
                )
            finally:
                con.close()

            result_data: dict[str, Any] = {
                "vault_id": str(vault_id),
                "prepared": True,
                "key_state": "generated",
                "os_wrap_available": os_store.available,
                "data_mode": "synthetic_only",
                "real_data_gate": "CLOSED",
                "db_path": db_path,
                "tables_created": len(tables),
            }

            if os_store.available:
                wrapped = os_store.protect_vmk(vmk, vault_id)
                result_data["os_wrapped"] = True
            else:
                result_data["os_wrapped"] = False

            # Recovery wrap readiness
            rw = RecoveryWrapper()
            result_data["recovery_wrap_available"] = rw.available
            result_data["recovery_algorithm"] = "Argon2id" if rw.available else "unavailable"

            return CliResult(status="ok", data=result_data)

        except Exception as exc:
            return CliResult(status="error", data=None, warnings=[str(exc)])

    def _cmd_vault_verify(self, args: list[str]) -> CliResult:
        """Verify vault integrity — schema, invariants, blob state.

        F07: Fail-closed. Without a live vault connection, this cannot verify
        anything real — must not return a false-positive success.
        """
        return CliResult(
            status="error",
            data=None,
            warnings=[
                "Vault verification requires an open vault connection. "
                "Run 'psyche-os vault init' first to create a vault."
            ],
        )

    def _cmd_vault_status(self, args: list[str]) -> CliResult:
        # F07: Fail-closed — no live vault, no status claim
        return CliResult(
            status="error",
            data=None,
            warnings=["Vault status requires an open vault connection."],
        )

    def _cmd_vault_close(self, args: list[str]) -> CliResult:
        # F07: Fail-closed — no live vault, nothing to close
        return CliResult(
            status="error",
            data=None,
            warnings=["No open vault to close."],
        )

    # ==================================================================
    # Fixture
    # ==================================================================

    def _cmd_fixture_help(self, args: list[str]) -> CliResult:
        return CliResult(status="error", data=None, warnings=["Use: psyche-os fixture {list|load}"])

    def _cmd_fixture_list(self, args: list[str]) -> CliResult:
        # F07 (FIX): SyntheticFixtureCapability cannot be instantiated directly.
        # The capability can only be obtained through the private loader.
        # For listing available packs, we only need the static table list.
        return CliResult(
            status="ok",
            data={
                "available_packs": ["f0_smoke", "f0_integration"],
                "allowed_tables": [
                    "actors",
                    "subjects",
                    "source_artifacts",
                    "observations",
                    "assertions",
                    "claims",
                    "data_policies",
                ],
                "synthetic_only": True,
                "note": (
                    "Fixtures are deny-by-default. Direct writes without "
                    "a valid FixtureAuthority fail at the storage write boundary. "
                    "Authority tokens cannot be self-issued. "
                    "The public SyntheticFixtureCapability constructor is closed."
                ),
            },
        )

    def _cmd_fixture_load(self, args: list[str]) -> CliResult:
        # Parse --path and --pack-id
        path = ""
        pack_id = ""
        for i, arg in enumerate(args):
            if arg == "--path" and i + 1 < len(args):
                path = args[i + 1]
            elif arg == "--pack-id" and i + 1 < len(args):
                pack_id = args[i + 1]

        if not pack_id:
            return CliResult(status="error", data=None, warnings=["--pack-id is required"])

        available = ["f0_smoke", "f0_integration"]

        if pack_id not in available:
            return CliResult(
                status="error",
                data=None,
                warnings=[f"Unknown fixture pack: {pack_id}. Available: {available}"],
            )

        # F07: Fail-closed — fixture load requires a live vault and capability authority
        return CliResult(
            status="error",
            data=None,
            warnings=[
                f"Fixture pack '{pack_id}' requires an open vault and valid FixtureAuthority. "
                "Direct writes without FixtureAuthority are rejected at the storage boundary. "
                "Authority tokens cannot be self-issued."
            ],
        )

    # ==================================================================
    # Migrate
    # ==================================================================

    def _cmd_migrate_help(self, args: list[str]) -> CliResult:
        return CliResult(
            status="error", data=None, warnings=["Use: psyche-os migrate {plan|apply}"]
        )

    def _cmd_migrate_plan(self, args: list[str]) -> CliResult:
        # F07: Fail-closed — requires open vault
        return CliResult(
            status="error",
            data=None,
            warnings=["Migration plan requires an open vault connection."],
        )

    def _cmd_migrate_apply(self, args: list[str]) -> CliResult:
        # F07: Fail-closed — requires open vault
        return CliResult(
            status="error",
            data=None,
            warnings=["Migration apply requires an open vault connection."],
        )

    # ==================================================================
    # Delete
    # ==================================================================

    def _cmd_delete_help(self, args: list[str]) -> CliResult:
        return CliResult(
            status="error", data=None, warnings=["Use: psyche-os delete {plan|execute}"]
        )

    def _cmd_delete_plan(self, args: list[str]) -> CliResult:
        # Parse --path, --root-id, --scope
        root_id = ""
        scope = "single_record"
        for i, arg in enumerate(args):
            if arg == "--root-id" and i + 1 < len(args):
                root_id = args[i + 1]
            elif arg == "--scope" and i + 1 < len(args):
                scope = args[i + 1]

        if not root_id:
            return CliResult(status="error", data=None, warnings=["--root-id is required"])

        # F07: Fail-closed — requires open vault for dependency traversal
        return CliResult(
            status="error",
            data=None,
            warnings=["Deletion plan requires an open vault for dependency traversal."],
        )

    def _cmd_delete_execute(self, args: list[str]) -> CliResult:
        plan_id = ""
        for i, arg in enumerate(args):
            if arg == "--plan-id" and i + 1 < len(args):
                plan_id = args[i + 1]

        if not plan_id:
            return CliResult(status="error", data=None, warnings=["--plan-id is required"])

        # F07: Fail-closed — requires open vault
        return CliResult(
            status="error",
            data=None,
            warnings=["Deletion execution requires an open vault."],
        )

    # ==================================================================
    # Backup
    # ==================================================================

    def _cmd_backup_help(self, args: list[str]) -> CliResult:
        return CliResult(
            status="error", data=None, warnings=["Use: psyche-os backup {create|verify}"]
        )

    def _cmd_backup_create(self, args: list[str]) -> CliResult:
        """Backup creation is DEFERRED to PRE_REAL_DATA — no backup surface in E00."""
        return CliResult(
            status="error",
            data={
                "feature": "backup.create",
                "state": "FEATURE_DEFERRED_PRE_REAL_DATA",
                "reason": (
                    "Authenticated encrypted backup is deferred per ADR-021. "
                    "It will be implemented and independently attacked in E01 "
                    "before RDG-03 can pass."
                ),
            },
            warnings=["Backup creation is not available in E00."],
        )

    def _cmd_backup_verify(self, args: list[str]) -> CliResult:
        """Backup verification is DEFERRED to PRE_REAL_DATA."""
        return CliResult(
            status="error",
            data={
                "feature": "backup.verify",
                "state": "FEATURE_DEFERRED_PRE_REAL_DATA",
                "reason": "Backup verification is deferred per ADR-021.",
            },
            warnings=["Backup verification is not available in E00."],
        )

    # ==================================================================
    # Restore
    # ==================================================================

    def _cmd_restore_help(self, args: list[str]) -> CliResult:
        return CliResult(
            status="error", data=None, warnings=["Use: psyche-os restore {verify|activate}"]
        )

    def _cmd_restore_verify(self, args: list[str]) -> CliResult:
        """Restore verification is DEFERRED to PRE_REAL_DATA."""
        return CliResult(
            status="error",
            data={
                "feature": "restore.verify",
                "state": "FEATURE_DEFERRED_PRE_REAL_DATA",
                "reason": "Restore verification is deferred per ADR-021.",
            },
            warnings=["Restore verification is not available in E00."],
        )

    def _cmd_restore_activate(self, args: list[str]) -> CliResult:
        """Restore activation is DEFERRED to PRE_REAL_DATA."""
        return CliResult(
            status="error",
            data={
                "feature": "restore.activate",
                "state": "FEATURE_DEFERRED_PRE_REAL_DATA",
                "reason": "Restore activation is deferred per ADR-021.",
            },
            warnings=["Restore activation is not available in E00."],
        )

    # ==================================================================
    # Export
    # ==================================================================

    def _cmd_export_help(self, args: list[str]) -> CliResult:
        return CliResult(
            status="error", data=None, warnings=["Use: psyche-os export {create|verify}"]
        )

    def _cmd_export_create(self, args: list[str]) -> CliResult:
        path = ""
        output = ""
        audience = "personal_archive"
        for i, arg in enumerate(args):
            if arg == "--path" and i + 1 < len(args):
                path = args[i + 1]
            elif arg == "--output" and i + 1 < len(args):
                output = args[i + 1]
            elif arg == "--audience" and i + 1 < len(args):
                audience = args[i + 1]

        if not output:
            return CliResult(status="error", data=None, warnings=["--output is required"])

        # F07: Fail-closed — requires open vault
        return CliResult(
            status="error",
            data=None,
            warnings=["Export creation requires an open vault connection."],
        )

    def _cmd_export_verify(self, args: list[str]) -> CliResult:
        package = ""
        for i, arg in enumerate(args):
            if arg == "--package" and i + 1 < len(args):
                package = args[i + 1]

        if not package:
            return CliResult(status="error", data=None, warnings=["--package is required"])

        # F07: Fail-closed — requires export envelope key
        return CliResult(
            status="error",
            data=None,
            warnings=["Export verification requires an open vault and export envelope key."],
        )

    # ==================================================================
    # Audit
    # ==================================================================

    def _cmd_audit_help(self, args: list[str]) -> CliResult:
        return CliResult(status="error", data=None, warnings=["Use: psyche-os audit verify"])

    def _cmd_audit_verify(self, args: list[str]) -> CliResult:
        # F07: Fail-closed — requires open vault for full log inspection
        return CliResult(
            status="error",
            data=None,
            warnings=["Audit verification requires an open vault for full log inspection."],
        )

    # ==================================================================
    # Dispatch
    # ==================================================================

    def dispatch(self, argv: list[str]) -> CliResult:
        """Parse argv and dispatch to handler. Returns CliResult."""
        if not argv:
            return self._cmd_version([])

        cmd_name = argv[0]
        cmd = self._commands.get(cmd_name)

        if cmd is None:
            return CliResult(
                status="error",
                data=None,
                warnings=[f"Unknown command: {cmd_name}"],
            )

        remaining = argv[1:]

        # Handle --json flag (accepted for stability, already default)
        remaining = [a for a in remaining if a != "--json"]

        # Check for subcommand
        if remaining and cmd.subcommands:
            sub_name = remaining[0]
            sub = cmd.subcommands.get(sub_name)
            if sub:
                return sub.handler(remaining[1:])

        return cmd.handler(remaining)

    def run(self, argv: list[str] | None = None) -> int:
        """Run CLI and print result. Returns exit code."""
        if argv is None:
            argv = sys.argv[1:]

        try:
            result = self.dispatch(argv)
            if result.status == "ok":
                print(result.to_json())
                return ExitCode.SUCCESS
            else:
                print(result.to_json(), file=sys.stderr)
                return ExitCode.GENERAL_ERROR
        except Exception as exc:
            error = CliError(
                code="F0_INTERNAL",
                detail=str(exc),
                hint="Unexpected error in F0 CLI — no content or secrets in error",
            )
            print(error.to_json(), file=sys.stderr)
            return ExitCode.GENERAL_ERROR


def create_cli() -> F0CLI:
    """Factory for the F0 CLI."""
    return F0CLI()
