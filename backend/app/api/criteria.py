"""Criteria calibration API."""

from fastapi import APIRouter, Header, HTTPException, status

from backend.app.models.criteria import CriteriaVersionUpdate, ReviewMatrix, ReviewSubmission, ReviewerRole
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


@router.get("/{version_id}/conflicts", response_model=ReviewMatrix)
def get_conflicts(version_id: str, application_id: str = "APPS-2") -> ReviewMatrix:
    try:
        return criteria.get_review_matrix(version_id, application_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="기준 버전을 찾을 수 없습니다") from error


@router.post("/{version_id}/reviews", response_model=ReviewMatrix)
def save_reviews(
    version_id: str,
    payload: ReviewSubmission,
    x_demo_role: ReviewerRole | None = Header(default=None),
):
    actor_role = x_demo_role or payload.reviewer_role
    try:
        return criteria.save_reviews(version_id, payload, actor_role)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="기준 버전을 찾을 수 없습니다") from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
