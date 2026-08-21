"""Pure interaction-workspace concepts for V3-A0.

These records deliberately are not canonical evidence, reports, observations,
claims, or model snapshots.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SessionState(StrEnum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class TurnActor(StrEnum):
    USER = "USER"


class SessionRetention(StrEnum):
    ENCRYPTED_LOCAL = "ENCRYPTED_LOCAL"


@dataclass(frozen=True, slots=True)
class ReflectionSession:
    session_id: str
    title: str
    state: SessionState
    retention: SessionRetention
    created_at: str
    updated_at: str
    closed_at: str | None
    turn_count: int


@dataclass(frozen=True, slots=True)
class ReflectionTurn:
    turn_id: str
    session_id: str
    sequence: int
    actor: TurnActor
    created_at: str
    content: str
