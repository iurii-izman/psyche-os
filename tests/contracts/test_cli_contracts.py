"""Contract tests for stable JSON error and CLI output."""

import json

from psyche_os.interfaces.cli import (
    F0CLI,
    CliError,
    CliResult,
    ExitCode,
    create_cli,
)


class TestCliError:
    def test_to_json(self) -> None:
        error = CliError(
            code="F0_TEST",
            detail="Test error",
            hint="This is a hint",
            transaction_id="abc-123",
        )
        data = json.loads(error.to_json())
        assert data["error"]["code"] == "F0_TEST"
        assert data["error"]["detail"] == "Test error"
        assert data["error"]["hint"] == "This is a hint"
        assert data["error"]["transaction_id"] == "abc-123"


class TestCliResult:
    def test_ok_result(self) -> None:
        result = CliResult(status="ok", data={"key": "value"})
        data = json.loads(result.to_json())
        assert data["status"] == "ok"
        assert data["data"]["key"] == "value"

    def test_error_result(self) -> None:
        result = CliResult(
            status="error",
            data=None,
            warnings=["Something went wrong"],
        )
        data = json.loads(result.to_json())
        assert data["status"] == "error"
        assert len(data["warnings"]) == 1


class TestF0CLI:
    def test_create_cli(self) -> None:
        cli = create_cli()
        assert isinstance(cli, F0CLI)

    def test_version_command(self) -> None:
        cli = create_cli()
        result = cli.dispatch(["version"])
        assert result.status == "ok"
        assert result.data is not None
        assert "version" in result.data
        assert result.data["version"] == "0.1.0"
        assert result.data["real_data_gate"] == "CLOSED"

    def test_empty_args_returns_version(self) -> None:
        cli = create_cli()
        result = cli.dispatch([])
        assert result.status == "ok"
        assert "version" in result.data

    def test_gate_status(self) -> None:
        cli = create_cli()
        result = cli.dispatch(["gate", "status"])
        assert result.status == "ok"
        assert result.data is not None
        assert "gate_state" in result.data
        assert "probes" in result.data
        assert result.data["real_data_gate"] == "CLOSED"
        assert len(result.data["probes"]) == 8
        # All probes report capability_verdict
        for probe in result.data["probes"]:
            assert "capability_verdict" in probe

    def test_gate_no_subcommand(self) -> None:
        cli = create_cli()
        result = cli.dispatch(["gate"])
        assert result.status == "error"

    def test_vault_init(self) -> None:
        cli = create_cli()
        result = cli.dispatch(["vault", "init"])
        # May fail if gate not accepted, but should return structured data
        assert result.status in ("ok", "error")
        if result.status == "ok":
            assert "vault_id" in result.data
            assert result.data["real_data_gate"] == "CLOSED"

    def test_vault_verify(self) -> None:
        cli = create_cli()
        result = cli.dispatch(["vault", "verify"])
        # F07: Fail-closed — no open vault, must return error
        assert result.status == "error"

    def test_vault_status(self) -> None:
        cli = create_cli()
        result = cli.dispatch(["vault", "status"])
        # F07: Fail-closed — no open vault, must return error
        assert result.status == "error"

    def test_vault_close(self) -> None:
        cli = create_cli()
        result = cli.dispatch(["vault", "close"])
        # F07: Fail-closed — no open vault, must return error
        assert result.status == "error"

    def test_doctor_command(self) -> None:
        cli = create_cli()
        result = cli.dispatch(["doctor"])
        # Doctor always returns data with profiles
        assert result.data is not None
        assert "profiles" in result.data
        assert result.data["real_data_gate"] == "CLOSED"
        # Profiles should report sqlcipher, os_key_wrap, recovery, crypto_library
        for profile in ("sqlcipher", "os_key_wrap", "recovery", "crypto_library"):
            assert profile in result.data["profiles"]

    def test_fixture_list(self) -> None:
        cli = create_cli()
        result = cli.dispatch(["fixture", "list"])
        assert result.status == "ok"
        assert "available_packs" in result.data
        assert result.data["synthetic_only"] is True

    def test_unknown_command(self) -> None:
        cli = create_cli()
        result = cli.dispatch(["nonexistent"])
        assert result.status == "error"

    def test_run_returns_exit_code(self) -> None:
        cli = create_cli()
        exit_code = cli.run(["version"])
        assert exit_code == ExitCode.SUCCESS

    def test_run_error_returns_general_error(self) -> None:
        cli = create_cli()
        exit_code = cli.run(["nonexistent"])
        assert exit_code == ExitCode.GENERAL_ERROR


class TestExitCodes:
    def test_all_exit_codes_distinct(self) -> None:
        codes = {
            ExitCode.SUCCESS,
            ExitCode.GENERAL_ERROR,
            ExitCode.VAULT_ERROR,
            ExitCode.GATE_REJECTED,
            ExitCode.GATE_BLOCKED,
            ExitCode.GATE_UNAVAILABLE,
            ExitCode.POLICY_BLOCKED,
            ExitCode.NEVER_CLOUD_VIOLATION,
            ExitCode.CRYPTO_ERROR,
            ExitCode.STORAGE_ERROR,
            ExitCode.DELETION_ERROR,
            ExitCode.BACKUP_ERROR,
            ExitCode.EXPORT_ERROR,
            ExitCode.VALIDATION_ERROR,
            ExitCode.INVARIANT_VIOLATION,
            ExitCode.LICENSE_ERROR,
            ExitCode.SYNTHETIC_ONLY_ERROR,
            ExitCode.FIXTURE_ERROR,
            ExitCode.MIGRATION_ERROR,
            ExitCode.REAL_DATA_GATE,
        }
        assert len(codes) == 20
