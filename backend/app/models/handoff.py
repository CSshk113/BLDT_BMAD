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


class QuestionCandidateStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    SELECTED = "SELECTED"
    DELETED = "DELETED"


class QuestionCandidate(BaseModel):
    id: str
    original_question: str = Field(min_length=1, max_length=1000)
    current_question: str = Field(min_length=1, max_length=1000)
    reason: str = Field(min_length=1, max_length=2000)
    criterion_item_ids: list[str] = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    question_type: str = Field(min_length=1, max_length=50)
    status: QuestionCandidateStatus = QuestionCandidateStatus.CANDIDATE
    created_at: datetime
    edit_history: list[dict[str, Any]] = Field(default_factory=list)


class QuestionCandidateEditInput(BaseModel):
    current_question: str = Field(min_length=1, max_length=1000)
    edit_reason: str = Field(min_length=1, max_length=500)


class QuestionCandidateSelectionInput(BaseModel):
    selected: bool


class QuestionCandidateGenerationResponse(BaseModel):
    card_id: str
    candidates: list[QuestionCandidate] = Field(default_factory=list)


class QuestionCandidateListResponse(BaseModel):
    card_id: str
    candidates: list[QuestionCandidate] = Field(default_factory=list)
    selected_question_ids: list[str] = Field(default_factory=list)
