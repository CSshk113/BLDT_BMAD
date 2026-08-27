"""Criteria calibration API."""

from fastapi import APIRouter, HTTPException, status

from backend.app.models.criteria import CriteriaVersionUpdate
from backend.app.services import criteria


router = APIRouter(prefix="/api/criteria", tags=["criteria"])


@router.get("", response_model=list)
def get_criteria_versions():
    return criteria.list_versions()


@router.get("/{version_id}")
def get_criteria_version(version_id: str):
    try:
        return criteria.get_version(version_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="기준 버전을 찾을 수 없습니다") from error


@router.post("/{version_id}/versions", status_code=status.HTTP_201_CREATED)
def create_version(version_id: str):
    try:
        return criteria.create_draft_version(version_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="원본 기준 버전을 찾을 수 없습니다") from error


@router.patch("/{version_id}")
def update_criteria(version_id: str, payload: CriteriaVersionUpdate):
    try:
        return criteria.update_draft(version_id, [item.criterion_text for item in payload.items])
    except KeyError as error:
        raise HTTPException(status_code=404, detail="기준 버전을 찾을 수 없습니다") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/{version_id}/preview")
def get_preview(version_id: str):
    try:
        return criteria.get_preview(version_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="기준 버전을 찾을 수 없습니다") from error

