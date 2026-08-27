"""Criterion-to-source citation mapping API."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.models.criteria import MappingResponse
from backend.app.services import mapping


router = APIRouter(prefix="/api/mappings", tags=["mapping"])


class MappingRequest(BaseModel):
    application_id: str = Field(min_length=1, max_length=100)
    criteria_version_id: str | None = Field(default=None, min_length=1, max_length=100)


@router.post("", response_model=MappingResponse)
def create_mapping(payload: MappingRequest) -> MappingResponse:
    try:
        return mapping.create_mappings(payload.application_id, payload.criteria_version_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="지원서 또는 기준 버전을 찾을 수 없습니다") from error
    except mapping.MappingNotReadyError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/{application_id}", response_model=MappingResponse)
def get_mapping(application_id: str, criteria_version_id: str | None = None, run_id: str | None = None) -> MappingResponse:
    try:
        return mapping.get_mappings(application_id, criteria_version_id, run_id)
    except mapping.MappingNotFoundError as error:
        raise HTTPException(status_code=404, detail="아직 생성된 기준별 매핑이 없습니다") from error
    except KeyError as error:
        raise HTTPException(status_code=404, detail="지원서 또는 기준 버전을 찾을 수 없습니다") from error
