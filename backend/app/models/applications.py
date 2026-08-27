"""Contracts for PDF applications and their processing runs."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProcessingStatus(StrEnum):
    RECEIVED = "RECEIVED"
    PARSING = "PARSING"
    MAPPING = "MAPPING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ProcessingStep(StrEnum):
    RECEIVED = "RECEIVED"
    PARSING = "PARSING"
    MAPPING = "MAPPING"


class ArtifactType(StrEnum):
    ORIGINAL_PDF = "ORIGINAL_PDF"
    LLAMAPARSE_MARKDOWN = "LLAMAPARSE_MARKDOWN"
    NORMALIZED_MARKDOWN = "NORMALIZED_MARKDOWN"


class ApplicationSource(StrEnum):
    UPLOAD = "UPLOAD"
    SAMPLE = "SAMPLE"
    LEDGER_ONLY = "LEDGER_ONLY"


class LedgerMetadata(BaseModel):
    application_id: str | None = None
    channel: str | None = None
    position: str | None = None
    applied_at: str | None = None
    overall_status: str | None = None
    hr_screening: str | None = None
    rejection_reason: str | None = None
    document_review: str | None = None
    first_interview: str | None = None
    second_interview: str | None = None
    final_result: str | None = None
    sample_stage: str | None = None
    sample_name: str | None = None
    sample_file_available: bool = False


class ApplicationArtifact(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    application_id: str
    processing_run_id: str | None = None
    artifact_type: ArtifactType
    original_filename: str
    mime_type: str
    is_current: bool
    created_at: datetime


class ProcessingRunEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: ProcessingStatus
    step: str
    occurred_at: datetime
    detail: str | None = None


class ProcessingRun(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    application_id: str
    criteria_version_id: str
    status: ProcessingStatus
    current_step: str
    parser_model: str
    received_at: datetime
    parsing_started_at: datetime | None = None
    mapping_started_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    failure_step: str | None = None
    failure_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    events: list[ProcessingRunEvent] = Field(default_factory=list)


class ApplicationSummary(BaseModel):
    id: str
    candidate_token: str
    position_name: str
    criteria_version_id: str | None = None
    source_type: ApplicationSource | None = None
    list_status: str
    processing_status: ProcessingStatus | None = None
    current_step: str | None = None
    failed_step: str | None = None
    failure_reason: str | None = None
    last_successful_run_id: str | None = None
    last_successful_artifact_types: list[ArtifactType] = Field(default_factory=list)
    ledger_metadata: LedgerMetadata = Field(default_factory=LedgerMetadata)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ApplicationDetail(ApplicationSummary):
    artifacts: list[ApplicationArtifact] = Field(default_factory=list)
    processing_runs: list[ProcessingRun] = Field(default_factory=list)
    can_review: bool = False


class ApplicationsList(BaseModel):
    items: list[ApplicationSummary] = Field(default_factory=list)
    total_ledger_count: int = 0
    sample_count: int = 0
    uploaded_count: int = 0


class ApplicationUploadInput(BaseModel):
    candidate_token: str = Field(min_length=1, max_length=100)
    position_name: str = Field(min_length=1, max_length=200)
    criteria_version_id: str = Field(min_length=1, max_length=100)

    @field_validator("candidate_token", "position_name", "criteria_version_id")
    @classmethod
    def reject_blank_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("필수 메타데이터는 공백일 수 없습니다")
        return value


class ProcessingFailureResponse(BaseModel):
    code: str
    message: str
    application: ApplicationDetail


def ledger_metadata_from_json(value: str | None) -> LedgerMetadata:
    import json

    try:
        payload: Any = json.loads(value or "{}")
    except json.JSONDecodeError:
        payload = {}
    return LedgerMetadata.model_validate(payload)
