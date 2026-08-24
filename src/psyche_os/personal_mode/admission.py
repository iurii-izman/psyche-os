"""Fail-closed Personal Mode admission boundary."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


class PersonalNotAdmittedError(Exception):
    """Content-free failure for every denied Personal byte operation."""

    code = "NOT_ADMITTED"


@dataclass(frozen=True, slots=True)
class AdmissionDecision:
    """Trusted evaluator output; no roots, paths, secrets, or content."""

    admitted: bool
    evaluation_id: str = ""
    evaluation_digest: str = ""
    attestation_digest: str = ""
    profile_digest: str = ""
    candidate_identity: str = ""
    expires_at: datetime | None = None

    def currently_open(self, now: datetime) -> bool:
        return (
            self.admitted
            and self.expires_at is not None
            and now < self.expires_at.astimezone(UTC)
            and all(
                (
                    self.evaluation_id,
                    self.evaluation_digest,
                    self.attestation_digest,
                    self.profile_digest,
                    self.candidate_identity,
                )
            )
        )


class PersonalAdmissionGuard:
    """The sole authorization boundary before Personal reads or writes.

    Production composition passes an evaluator that always returns a closed
    decision until the real-data gate is legitimately opened. Tests may inject
    an explicit decision factory; there is intentionally no environment,
    command-line, config, or renderer bypass.
    """

    def __init__(
        self,
        evaluator: Callable[[], AdmissionDecision] | None = None,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        clear_key_material: Callable[[], None] | None = None,
    ) -> None:
        self._evaluator = evaluator or (lambda: AdmissionDecision(False))
        self._clock = clock
        self._clear_key_material = clear_key_material or (lambda: None)
        self._identity: tuple[str, str, str, str, str] | None = None
        self._locked = True

    @staticmethod
    def _identity_for(decision: AdmissionDecision) -> tuple[str, str, str, str, str]:
        return (
            decision.evaluation_id,
            decision.evaluation_digest,
            decision.attestation_digest,
            decision.profile_digest,
            decision.candidate_identity,
        )

    def require(self) -> AdmissionDecision:
        """Re-evaluate before every protected operation, including reads."""
        decision = self._evaluator()
        now = self._clock()
        identity = self._identity_for(decision)
        if not decision.currently_open(now) or (
            self._identity is not None and identity != self._identity
        ):
            self.lock()
            raise PersonalNotAdmittedError()
        self._identity = identity
        self._locked = False
        return decision

    def lock(self) -> None:
        self._locked = True
        self._identity = None
        with suppress(Exception):
            self._clear_key_material()

    def bind_key_clearer(self, clearer: Callable[[], None]) -> None:
        """Bind trusted runtime cleanup after composition, never through IPC.

        The Personal runtime is deliberately constructed only after the guard,
        so the composition root binds its in-memory key cleanup callback here.
        Renderer data never reaches this method.
        """
        self._clear_key_material = clearer

    @property
    def locked(self) -> bool:
        return self._locked

    def status(self) -> dict[str, Any]:
        """Content-free admission status; never opens Personal storage."""
        decision = self._evaluator()
        available = decision.currently_open(self._clock())
        if self._locked:
            return {"local_personal": "ADMISSION_AVAILABLE" if available else "NOT_ADMITTED"}
        return {"local_personal": "ADMITTED" if available else "NOT_ADMITTED"}


PersonalNotAdmitted = PersonalNotAdmittedError
