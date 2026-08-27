"""Criteria version contracts for the calibration gate."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CriteriaVersionStatus(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    ARCHIVED = "ARCHIVED"


class MappingStatus(StrEnum):
    RECEIVED = "RECEIVED"
    COMPLETED = "COMPLETED"
    INVALIDATED = "INVALIDATED"


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


class OfficialActionRejected(BaseModel):
    code: str
    message: str
    criteria_version_id: str
    missing_conditions: list[str]


def to_jsonable(value: Any) -> Any:
    """Small boundary helper kept here for callers that persist model data."""
    return value.model_dump(mode="json") if isinstance(value, BaseModel) else value
