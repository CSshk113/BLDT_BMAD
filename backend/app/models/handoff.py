"""Contracts for the JSON-based official handoff card."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class HandoffStatus(StrEnum):
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class HandoffCard(BaseModel):
    id: str
    application_id: str
    criteria_version_id: str
    status: HandoffStatus
    payload: dict[str, Any] = Field(default_factory=dict)
    created_by: str
    failure_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class HandoffGenerationResponse(BaseModel):
    card: HandoffCard
    already_exists: bool = False


class HandoffPrerequisiteError(ValueError):
    def __init__(self, missing_conditions: list[str]):
        self.missing_conditions = missing_conditions
        super().__init__("핸드오프 생성 조건이 충족되지 않았습니다")


class HandoffStateError(ValueError):
    def __init__(self, message: str, card: HandoffCard | None = None):
        self.card = card
        super().__init__(message)
