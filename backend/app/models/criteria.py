"""Criteria version contracts for the calibration gate."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CriteriaVersionStatus(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    ARCHIVED = "ARCHIVED"


class MappingStatus(StrEnum):
    RECEIVED = "RECEIVED"
    COMPLETED = "COMPLETED"
    INVALIDATED = "INVALIDATED"


class ReviewerRole(StrEnum):
    HR = "HR"
    HM = "HM"


class ReviewStatus(StrEnum):
    FULFILLED = "FULFILLED"
    PARTIALLY_FULFILLED = "PARTIALLY_FULFILLED"
    UNFULFILLED = "UNFULFILLED"
    UNVERIFIABLE = "UNVERIFIABLE"


class ConflictStatus(StrEnum):
    OPEN = "OPEN"
    PENDING = "PENDING"
    NONE = "NONE"


class CriteriaItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    criterion_text: str
    requirement_type: str
    sort_order: int = 0


class CriteriaVersion(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    position_name: str
    status: CriteriaVersionStatus
    items: list[CriteriaItem] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None = None


class CriteriaItemUpdate(BaseModel):
    criterion_text: str = Field(min_length=1, max_length=500)


class CriteriaVersionUpdate(BaseModel):
    items: list[CriteriaItemUpdate] = Field(min_length=1)


class PreviewMapping(BaseModel):
    application_id: str
    applicant_label: str
    criterion_item_id: str
    citation: str
    location: str
    evidence_status: str
    mapping_status: MappingStatus


class DraftPreview(BaseModel):
    criteria_version_id: str
    criteria_status: CriteriaVersionStatus
    is_preview: bool
    mappings: list[PreviewMapping] = Field(default_factory=list)


class CriteriaMutationResult(BaseModel):
    version: CriteriaVersion
    invalidated_mapping_count: int = 0
    rerun_required: bool = False


class ReviewInput(BaseModel):
    criterion_item_id: str
    status: ReviewStatus
    reason_text: str = Field(min_length=1, max_length=1000)
    source_location: str = Field(min_length=1, max_length=300)

    @field_validator("reason_text", "source_location")
    @classmethod
    def reject_blank_evidence(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("원문 근거와 위치는 공백일 수 없습니다")
        return value.strip()


class ReviewSubmission(BaseModel):
    application_id: str = Field(min_length=1, max_length=100)
    reviewer_role: ReviewerRole
    reviews: list[ReviewInput] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_items(self) -> "ReviewSubmission":
        item_ids = [review.criterion_item_id for review in self.reviews]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("한 번의 제출에는 같은 기준 항목을 중복할 수 없습니다")
        return self


class ReviewLog(BaseModel):
    id: str
    criteria_version_id: str
    application_id: str
    criterion_item_id: str
    reviewer_role: ReviewerRole
    status: ReviewStatus
    reason_text: str
    source_location: str
    created_at: datetime
    updated_at: datetime


class ConflictRow(BaseModel):
    criterion_item_id: str
    criterion_text: str
    requirement_type: str
    conflict_status: ConflictStatus
    differences: list[str] = Field(default_factory=list)
    hr_review: ReviewLog | None = None
    hm_review: ReviewLog | None = None


class ReviewMatrix(BaseModel):
    criteria_version_id: str
    application_id: str
    rows: list[ConflictRow] = Field(default_factory=list)
    open_conflict_count: int = 0


class OfficialActionRejected(BaseModel):
    code: str
    message: str
    criteria_version_id: str
    missing_conditions: list[str]


def to_jsonable(value: Any) -> Any:
    """Small boundary helper kept here for callers that persist model data."""
    return value.model_dump(mode="json") if isinstance(value, BaseModel) else value
