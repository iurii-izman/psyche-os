from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json

import pytest

from psyche_os.personal_mode.admission import AdmissionDecision, PersonalAdmissionGuard
from psyche_os.personal_mode.lifecycle import (
    PersonalLifecycleError,
    PersonalLifecycleService,
    RotationFaultPoint,
    RotationProcessInterrupted,
)
from psyche_os.personal_mode.runtime import PersonalRuntime, PersonalRuntimeError
from psyche_os.personal_mode.runtime_profile import personal_runtime_paths


class _DPAPI:
    available = True

    def protect(self, value: bytes, description: str) -> bytes:
        return b"x" * 1024


def _guard(now: datetime) -> PersonalAdmissionGuard:
    decision = AdmissionDecision(
        True,
        "evaluation",
        "digest",
        "attestation",
        "profile",
        "candidate",
        now + timedelta(minutes=10),
    )
    return PersonalAdmissionGuard(lambda: decision, clock=lambda: now)


def test_personal_v10_backup_restore_export_and_deletion_are_guarded_and_isolated(tmp_path) -> None:
    now = datetime(2026, 8, 24, tzinfo=UTC)
    paths = personal_runtime_paths(local_app_data=tmp_path)
    runtime = PersonalRuntime(paths, _guard(now), os_wrapper_factory=_DPAPI)
    runtime.setup("fictional recovery secret")
    session = runtime.reflection.create_session("Fictional lifecycle title")
    runtime.reflection.add_user_turn(session["session_id"], "SLICE_B_SYNTHETIC_SENTINEL")

    backup = runtime.lifecycle.create_backup("fictional recovery secret")
    export = runtime.lifecycle.create_owner_export("fictional recovery secret")
    candidate = runtime.lifecycle.restore_isolated(backup["backup_id"], "fictional recovery secret")

    assert backup["key_version"] == "1"
    assert export["audience"] == "OWNER_ONLY"
    assert (
        paths.exports.joinpath(f"{export['export_id']}.pmv1")
        .read_bytes()
        .find(b"SLICE_B_SYNTHETIC_SENTINEL")
        < 0
    )
    assert paths.staging.joinpath(candidate["candidate_id"], "vault.sqlite").exists()
    assert (
        runtime.reflection.get_session(session["session_id"])["turns"][0]["content"]
        == "SLICE_B_SYNTHETIC_SENTINEL"
    )

    receipt = runtime.lifecycle.delete_session(
        runtime.reflection, session["session_id"], "DELETE REFLECTION SESSION"
    )
    assert receipt["deleted"] is True
    assert runtime.reflection.list_sessions()["sessions"] == []
    assert paths.backups.joinpath(f"{backup['backup_id']}.pmv1", "payload.bin").exists()


def test_backup_n_remains_isolated_restorable_after_sqlcipher_rotation(tmp_path) -> None:
    now = datetime(2026, 8, 24, tzinfo=UTC)
    paths = personal_runtime_paths(local_app_data=tmp_path)
    runtime = PersonalRuntime(paths, _guard(now), os_wrapper_factory=_DPAPI)
    runtime.setup("fictional recovery secret")
    session = runtime.reflection.create_session("Fictional rotation title")
    runtime.reflection.add_user_turn(session["session_id"], "ROTATION_SYNTHETIC_SENTINEL")
    backup = runtime.lifecycle.create_backup("fictional recovery secret")

    result = runtime.rotate("fictional recovery secret")
    assert result == {"from_key_version": "1", "to_key_version": "2"}
    runtime.unlock("fictional recovery secret")
    assert (
        runtime.reflection.get_session(session["session_id"])["turns"][0]["content"]
        == "ROTATION_SYNTHETIC_SENTINEL"
    )
    candidate = runtime.lifecycle.restore_isolated(backup["backup_id"], "fictional recovery secret")
    assert candidate["key_version"] == "1"
    assert paths.retained_keys.joinpath("key-envelope-v1.pmv1.json").exists()


def test_retained_n_destruction_refuses_backup_dependency_then_allows_final_cleanup(
    tmp_path,
) -> None:
    now = datetime(2026, 8, 24, tzinfo=UTC)
    paths = personal_runtime_paths(local_app_data=tmp_path)
    runtime = PersonalRuntime(paths, _guard(now), os_wrapper_factory=_DPAPI)
    runtime.setup("fictional recovery secret")
    runtime.reflection.create_session("Fictional retained-key title")
    backup = runtime.lifecycle.create_backup("fictional recovery secret")
    runtime.rotate("fictional recovery secret")
    runtime.unlock("fictional recovery secret")

    from psyche_os.personal_mode.lifecycle import PersonalLifecycleError

    with pytest.raises(PersonalLifecycleError):
        runtime.destroy_retained(1)
    assert paths.retained_keys.joinpath("key-envelope-v1.pmv1.json").exists()
    package = paths.backups / f"{backup['backup_id']}.pmv1"
    for artifact in package.iterdir():
        artifact.unlink()
    package.rmdir()
    assert runtime.destroy_retained(1)["state"] == "destroyed"
    runtime.lock()
    runtime = PersonalRuntime(paths, _guard(now), os_wrapper_factory=_DPAPI)
    runtime.unlock("fictional recovery secret")
    assert runtime.reflection.list_sessions()["sessions"]


def test_rotation_fault_after_prepared_preserves_durable_n_for_fresh_reconciliation(
    tmp_path,
) -> None:
    now = datetime(2026, 8, 24, tzinfo=UTC)
    paths = personal_runtime_paths(local_app_data=tmp_path)
    runtime = PersonalRuntime(paths, _guard(now), os_wrapper_factory=_DPAPI)
    runtime.setup("fictional recovery secret")
    session = runtime.reflection.create_session("Fault seam title")
    runtime.reflection.add_user_turn(session["session_id"], "FAULT_SENTINEL")
    observed: list[RotationFaultPoint] = []

    def crash(point: RotationFaultPoint) -> None:
        observed.append(point)
        if point is RotationFaultPoint.AFTER_PREPARED:
            raise RotationProcessInterrupted()

    with pytest.raises(RotationProcessInterrupted):
        PersonalLifecycleService(
            paths, _guard(now), os_wrapper_factory=_DPAPI, rotation_fault_hook=crash
        ).rotate("fictional recovery secret", close_active=runtime._clear)
    assert observed == [RotationFaultPoint.AFTER_PREPARED]
    assert paths.rotation_journal.exists()
    assert not paths.retained_keys.exists()

    restarted = PersonalRuntime(paths, _guard(now), os_wrapper_factory=_DPAPI)
    assert restarted.reconcile_rotation("fictional recovery secret") == "ACTIVE_N"
    restarted.unlock("fictional recovery secret")
    assert (
        restarted.reflection.get_session(session["session_id"])["turns"][0]["content"]
        == "FAULT_SENTINEL"
    )


@pytest.mark.parametrize(
    ("point", "expected_generation"),
    [
        (RotationFaultPoint.DURING_EXPORT, 1),
        (RotationFaultPoint.AFTER_CANDIDATE_VERIFIED, 1),
        (RotationFaultPoint.AFTER_ACTIVATION_STARTED, 1),
        (RotationFaultPoint.AFTER_DB_REPLACEMENT, 2),
        (RotationFaultPoint.AFTER_DB_N_PLUS_1_VERIFIED, 2),
        (RotationFaultPoint.DURING_RETAINED_PUBLICATION, 2),
        (RotationFaultPoint.AFTER_RETAINED_N_PUBLISHED, 2),
        (RotationFaultPoint.AFTER_ENVELOPE_N_PLUS_1_PROMOTED, 2),
        (RotationFaultPoint.AFTER_ROTATION_COMPLETE, 2),
        (RotationFaultPoint.BEFORE_JOURNAL_CLEANUP, 2),
    ],
)
def test_rotation_faults_reconcile_from_fresh_durable_state(
    tmp_path, point, expected_generation
) -> None:
    now = datetime(2026, 8, 24, tzinfo=UTC)
    paths = personal_runtime_paths(local_app_data=tmp_path)
    runtime = PersonalRuntime(paths, _guard(now), os_wrapper_factory=_DPAPI)
    runtime.setup("fictional recovery secret")
    session = runtime.reflection.create_session("Fault matrix title")
    runtime.reflection.add_user_turn(session["session_id"], "FAULT_MATRIX_SENTINEL")

    def crash(actual: RotationFaultPoint) -> None:
        if actual is point:
            raise RotationProcessInterrupted()

    with pytest.raises(RotationProcessInterrupted):
        PersonalLifecycleService(
            paths, _guard(now), os_wrapper_factory=_DPAPI, rotation_fault_hook=crash
        ).rotate("fictional recovery secret", close_active=runtime._clear)
    restarted = PersonalRuntime(paths, _guard(now), os_wrapper_factory=_DPAPI)
    assert restarted.reconcile_rotation("fictional recovery secret") in {
        "ACTIVE_N",
        "ACTIVE_N_PLUS_1",
    }
    envelope = json.loads(paths.envelope.read_text(encoding="utf-8"))
    assert envelope["key_version"] == expected_generation
    restarted.unlock("fictional recovery secret")
    assert (
        restarted.reflection.get_session(session["session_id"])["turns"][0]["content"]
        == "FAULT_MATRIX_SENTINEL"
    )


@pytest.mark.parametrize("retained_mutation", ["missing", "corrupted"])
def test_post_promotion_retained_n_is_required_before_fresh_unlock(
    tmp_path, retained_mutation
) -> None:
    """N+1 cannot expose content when its N-authenticated journal lacks retained N."""
    now = datetime(2026, 8, 24, tzinfo=UTC)
    paths = personal_runtime_paths(local_app_data=tmp_path)
    runtime = PersonalRuntime(paths, _guard(now), os_wrapper_factory=_DPAPI)
    runtime.setup("fictional recovery secret")
    session = runtime.reflection.create_session("Post-promotion retained N proof")
    runtime.reflection.add_user_turn(session["session_id"], "POST_PROMOTION_SENTINEL")

    def crash(point: RotationFaultPoint) -> None:
        if point is RotationFaultPoint.AFTER_ENVELOPE_N_PLUS_1_PROMOTED:
            raise RotationProcessInterrupted()

    with pytest.raises(RotationProcessInterrupted):
        PersonalLifecycleService(
            paths, _guard(now), os_wrapper_factory=_DPAPI, rotation_fault_hook=crash
        ).rotate("fictional recovery secret", close_active=runtime._clear)

    retained = paths.retained_keys / "key-envelope-v1.pmv1.json"
    if retained_mutation == "missing":
        retained.unlink()
    else:
        retained.write_bytes(b'{"tampered":true}')

    fresh = PersonalRuntime(paths, _guard(now), os_wrapper_factory=_DPAPI)
    with pytest.raises(PersonalRuntimeError) as error:
        fresh.unlock("fictional recovery secret")
    assert error.value.code == "PERSONAL_RUNTIME_UNAVAILABLE"
    assert paths.rotation_journal.exists()
    assert fresh._reflection is None
    assert paths.envelope.exists()


def test_retained_n_destruction_dependency_oracle_covers_journal_staging_and_restore(
    tmp_path,
) -> None:
    now = datetime(2026, 8, 24, tzinfo=UTC)

    # J: an authenticated N journal blocks destruction even after the obsolete
    # previous-N file has legitimately gone away.
    journal_paths = personal_runtime_paths(local_app_data=tmp_path / "journal")
    journal_runtime = PersonalRuntime(journal_paths, _guard(now), os_wrapper_factory=_DPAPI)
    journal_runtime.setup("fictional recovery secret")

    def after_promotion(point: RotationFaultPoint) -> None:
        if point is RotationFaultPoint.AFTER_ENVELOPE_N_PLUS_1_PROMOTED:
            raise RotationProcessInterrupted()

    with pytest.raises(RotationProcessInterrupted):
        PersonalLifecycleService(
            journal_paths,
            _guard(now),
            os_wrapper_factory=_DPAPI,
            rotation_fault_hook=after_promotion,
        ).rotate("fictional recovery secret", close_active=journal_runtime._clear)
    for previous in journal_paths.staging.glob("**/previous-N.sqlite"):
        previous.unlink()
    assert journal_runtime.lifecycle.destruction_dependencies(1) == ("journal",)
    with pytest.raises(PersonalLifecycleError):
        journal_runtime.destroy_retained(1)
    assert journal_paths.retained_keys.joinpath("key-envelope-v1.pmv1.json").exists()
    assert json.loads(journal_paths.envelope.read_text(encoding="utf-8"))["key_version"] == 2
    assert journal_runtime.reconcile_rotation("fictional recovery secret") == "ACTIVE_N_PLUS_1"
    assert journal_runtime.destroy_retained(1)["state"] == "destroyed"

    # S: an interrupted activation has a real prior-N staging database, which
    # the oracle exposes alongside the still-authenticated reconciliation journal.
    staging_paths = personal_runtime_paths(local_app_data=tmp_path / "staging")
    staging_runtime = PersonalRuntime(staging_paths, _guard(now), os_wrapper_factory=_DPAPI)
    staging_runtime.setup("fictional recovery secret")

    def after_retained_published(point: RotationFaultPoint) -> None:
        if point is RotationFaultPoint.AFTER_RETAINED_N_PUBLISHED:
            raise RotationProcessInterrupted()

    with pytest.raises(RotationProcessInterrupted):
        PersonalLifecycleService(
            staging_paths,
            _guard(now),
            os_wrapper_factory=_DPAPI,
            rotation_fault_hook=after_retained_published,
        ).rotate("fictional recovery secret", close_active=staging_runtime._clear)
    assert "staging" in staging_runtime.lifecycle.destruction_dependencies(1)
    with pytest.raises(PersonalLifecycleError):
        staging_runtime.destroy_retained(1)
    assert staging_paths.retained_keys.joinpath("key-envelope-v1.pmv1.json").exists()
    assert json.loads(staging_paths.envelope.read_text(encoding="utf-8"))["key_version"] == 1
    assert staging_runtime.reconcile_rotation("fictional recovery secret") == "ACTIVE_N_PLUS_1"
    assert staging_runtime.lifecycle.destruction_dependencies(1) == ()
    assert staging_runtime.destroy_retained(1)["state"] == "destroyed"

    # R: an isolated old-N restore remains an observable staging dependency
    # after its backup has been legitimately removed.
    restore_paths = personal_runtime_paths(local_app_data=tmp_path / "restore")
    restore_runtime = PersonalRuntime(restore_paths, _guard(now), os_wrapper_factory=_DPAPI)
    restore_runtime.setup("fictional recovery secret")
    backup = restore_runtime.lifecycle.create_backup("fictional recovery secret")
    restore_runtime.rotate("fictional recovery secret")
    restore_runtime.lifecycle.restore_isolated(backup["backup_id"], "fictional recovery secret")
    package = restore_paths.backups / f"{backup['backup_id']}.pmv1"
    for artifact in package.iterdir():
        artifact.unlink()
    package.rmdir()
    assert restore_runtime.lifecycle.destruction_dependencies(1) == ("staging",)
    with pytest.raises(PersonalLifecycleError):
        restore_runtime.destroy_retained(1)
    assert restore_paths.retained_keys.joinpath("key-envelope-v1.pmv1.json").exists()
    assert json.loads(restore_paths.envelope.read_text(encoding="utf-8"))["key_version"] == 2
    for candidate in restore_paths.staging.glob("**/vault.sqlite"):
        candidate.unlink()
    assert restore_runtime.lifecycle.destruction_dependencies(1) == ()
    assert restore_runtime.destroy_retained(1)["state"] == "destroyed"


def test_slice_b_runtime_artifacts_and_failures_never_contain_synthetic_secrets(tmp_path) -> None:
    """Bounded sentinel over the B2-owned files from its durable states."""
    now = datetime(2026, 8, 24, tzinfo=UTC)
    content = "SLICE_B_PLAINTEXT_SENTINEL"
    secret = "SLICE_B_RECOVERY_SECRET_SENTINEL"
    paths = personal_runtime_paths(local_app_data=tmp_path / "normal")
    runtime = PersonalRuntime(paths, _guard(now), os_wrapper_factory=_DPAPI)
    runtime.setup(secret)
    runtime.reflection.add_user_turn(
        runtime.reflection.create_session("Sentinel test")["session_id"], content
    )
    backup = runtime.lifecycle.create_backup(secret)
    raw_vmk = runtime._vmk.raw
    runtime.rotate(secret)
    runtime.lifecycle.restore_isolated(backup["backup_id"], secret)
    package = paths.backups / f"{backup['backup_id']}.pmv1"
    for artifact in package.iterdir():
        artifact.unlink()
    package.rmdir()
    for candidate in paths.staging.glob("**/vault.sqlite"):
        candidate.unlink()
    runtime.destroy_retained(1)

    # A separate failed post-promotion reconciliation leaves its journal and
    # staging surroundings available to this bounded scan without exposing data.
    failed_paths = personal_runtime_paths(local_app_data=tmp_path / "failed")
    failed = PersonalRuntime(failed_paths, _guard(now), os_wrapper_factory=_DPAPI)
    failed.setup(secret)

    def crash(point: RotationFaultPoint) -> None:
        if point is RotationFaultPoint.AFTER_ENVELOPE_N_PLUS_1_PROMOTED:
            raise RotationProcessInterrupted()

    with pytest.raises(RotationProcessInterrupted):
        PersonalLifecycleService(
            failed_paths, _guard(now), os_wrapper_factory=_DPAPI, rotation_fault_hook=crash
        ).rotate(secret, close_active=failed._clear)
    failed_paths.retained_keys.joinpath("key-envelope-v1.pmv1.json").write_bytes(b"{}")
    fresh = PersonalRuntime(failed_paths, _guard(now), os_wrapper_factory=_DPAPI)
    with pytest.raises(PersonalRuntimeError) as error:
        fresh.unlock(secret)

    forbidden = (content.encode(), secret.encode(), raw_vmk, raw_vmk.hex().encode())
    scanned: list[bytes] = [str(error.value).encode(), error.value.code.encode()]
    for root in (paths.root, failed_paths.root):
        for artifact in root.rglob("*"):
            if artifact.is_file() and artifact.name not in {"vault.sqlite", "previous-N.sqlite"}:
                scanned.append(artifact.read_bytes())
    assert all(value not in artifact for artifact in scanned for value in forbidden)
