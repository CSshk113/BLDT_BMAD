"""Criteria version contracts for the calibration gate."""

from __future__ import annotations

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


class EvidenceStatus(StrEnum):
    FULFILLED = "충족"
    PARTIALLY_FULFILLED = "부분 충족"
    UNFULFILLED = "미충족"
    UNVERIFIABLE = "확인 불가"


class EvidenceLocationKind(StrEnum):
    EXACT = "EXACT"
    FALLBACK = "FALLBACK"
    NONE = "NONE"


class ReviewerRole(StrEnum):
    HR = "HR"
    HM = "HM"


class ReviewStatus(StrEnum):
    FULFILLED = "FULFILLED"
    PARTIALLY_FULFILLED = "PARTIALLY_FULFILLED"
    UNFULFILLED = "UNFULFILLED"
    UNVERIFIABLE = "UNVERIFIABLE"


class ReviewScope(StrEnum):
    CALIBRATION = "CALIBRATION"
    OFFICIAL = "OFFICIAL"


HR_SCREENING_VERDICTS = (
    "불합격 - 허수 지원",
    "불합격 - 경력/역량 부족",
    "불합격 - 회사/지원자 FIT",
    "스크리닝 통과",
)

HM_DOCUMENT_VERDICTS = (
    "불합격 - 허수 지원",
    "불합격 - 경력/역량 부족",
    "불합격 - 회사/지원자 FIT",
    "불합격 - 기타",
    "합격 - 필수 역량 충족",
    "합격 - 회사/지원자 FIT",
    "합격 - 필수 역량 미충족이나 면접 진행 필요",
    "합격 - 기타",
)


class ConflictStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
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
    approved_by: str | None = None


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


class MappingResult(BaseModel):
    id: str
    application_id: str
    criteria_version_id: str
    processing_run_id: str | None = None
    source_artifact_id: str | None = None
    applicant_label: str
    criterion_item_id: str
    criterion_text: str
    requirement_type: str
    citation: str
    location: str
    location_kind: EvidenceLocationKind
    evidence_status: EvidenceStatus
    mapping_status: MappingStatus


class MappingResponse(BaseModel):
    application_id: str
    criteria_version_id: str
    criteria_status: CriteriaVersionStatus
    is_preview: bool
    processing_run_id: str
    source_artifact_id: str
    mappings: list[MappingResult] = Field(default_factory=list)


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
    review_scope: ReviewScope = ReviewScope.CALIBRATION
    status: ReviewStatus
    reason_text: str
    source_location: str
    citation: str = ""
    mapping_result_id: str | None = None
    processing_run_id: str | None = None
    source_artifact_id: str | None = None
    edit_history: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class JudgmentInput(BaseModel):
    criterion_item_id: str
    status: ReviewStatus
    reason_text: str = Field(min_length=1, max_length=1000)
    citation: str = Field(default="", max_length=2000)
    source_location: str = Field(default="", max_length=300)
    edit_reason: str = Field(default="판단 내용 수정", min_length=1, max_length=500)

    @field_validator("reason_text", "edit_reason")
    @classmethod
    def reject_blank_reason(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("판단 사유와 수정 사유는 공백일 수 없습니다")
        return value

    @field_validator("citation", "source_location")
    @classmethod
    def strip_evidence(cls, value: str) -> str:
        return value.strip()


class JudgmentSubmission(BaseModel):
    application_id: str = Field(min_length=1, max_length=100)
    reviewer_role: ReviewerRole
    document_verdict: str | None = Field(default=None, max_length=200)
    document_edit_reason: str = Field(default="지원서 단계 판정 수정", min_length=1, max_length=500)
    reviews: list[JudgmentInput] = Field(min_length=1)

    @field_validator("document_verdict", "document_edit_reason")
    @classmethod
    def strip_verdict(cls, value: str | None) -> str | None:
        return value.strip() if value else value

    @model_validator(mode="after")
    def reject_duplicate_items(self) -> "JudgmentSubmission":
        item_ids = [review.criterion_item_id for review in self.reviews]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("한 번의 제출에는 같은 기준 항목을 중복할 수 없습니다")
        return self


class DocumentJudgment(BaseModel):
    reviewer_role: ReviewerRole
    verdict: str
    edit_history: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class JudgmentRow(BaseModel):
    criterion_item_id: str
    criterion_text: str
    requirement_type: str
    differences: list[str] = Field(default_factory=list)
    hr_review: ReviewLog | None = None
    hm_review: ReviewLog | None = None


class JudgmentMatrix(BaseModel):
    criteria_version_id: str
    application_id: str
    hr_document_judgment: DocumentJudgment | None = None
    hm_document_judgment: DocumentJudgment | None = None
    rows: list[JudgmentRow] = Field(default_factory=list)


class ConflictRow(BaseModel):
    criterion_item_id: str
    criterion_text: str
    requirement_type: str
    conflict_status: ConflictStatus
    differences: list[str] = Field(default_factory=list)
    hr_review: ReviewLog | None = None
    hm_review: ReviewLog | None = None
    resolution: ConflictResolution | None = None


class ReviewMatrix(BaseModel):
    criteria_version_id: str
    application_id: str
    rows: list[ConflictRow] = Field(default_factory=list)
    open_conflict_count: int = 0


class ConflictResolutionInput(BaseModel):
    application_id: str = Field(min_length=1, max_length=100)
    criterion_item_id: str = Field(min_length=1, max_length=200)
    resolution_reason: str = Field(min_length=1, max_length=1000)

    @field_validator("resolution_reason")
    @classmethod
    def reject_blank_resolution(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("충돌 해결 사유는 공백일 수 없습니다")
        return value.strip()


class ConflictResolution(BaseModel):
    id: str
    criteria_version_id: str
    application_id: str
    criterion_item_id: str
    status: ConflictStatus
    resolved_by: ReviewerRole
    resolved_at: datetime
    resolution_reason: str


class CriteriaApprovalResult(BaseModel):
    version: CriteriaVersion
    criteria_version_id: str
    approved_by: ReviewerRole
    approved_at: datetime


class OfficialActionRejected(BaseModel):
    code: str
    message: str
    criteria_version_id: str
    missing_conditions: list[str]


def to_jsonable(value: Any) -> Any:
    """Small boundary helper kept here for callers that persist model data."""
    return value.model_dump(mode="json") if isinstance(value, BaseModel) else value
