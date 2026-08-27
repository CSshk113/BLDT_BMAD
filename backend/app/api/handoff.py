"""Official handoff card API."""

from fastapi import APIRouter, Header, HTTPException

from backend.app.models.handoff import HandoffPrerequisiteError, HandoffStateError
from backend.app.services import criteria, handoff


router = APIRouter(prefix="/api/handoff", tags=["handoff"])


@router.post("/generate")
def generate_handoff_card(
    criteria_version_id: str,
    application_id: str | None = None,
    x_demo_role: str = Header(default="LEAD"),
):
    if application_id is None:
        try:
            rejection = criteria.reject_official_action(criteria_version_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="기준 버전을 찾을 수 없습니다") from error
        if rejection:
            raise HTTPException(status_code=403, detail=rejection.model_dump())
        return {"status": "ready", "handoff_unlocked": True, "criteria_version_id": criteria_version_id}
    if x_demo_role != "LEAD":
        raise HTTPException(status_code=403, detail="핸드오프 권한이 없습니다")
    try:
        return handoff.generate_card(criteria_version_id, application_id, x_demo_role)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="기준 버전을 찾을 수 없습니다") from error
    except HandoffPrerequisiteError as error:
        raise HTTPException(status_code=409, detail={"code": "HANDOFF_NOT_READY", "missing_conditions": error.missing_conditions}) from error
    except HandoffStateError as error:
        detail = {"code": "HANDOFF_STATE", "message": str(error), "card": error.card.model_dump(mode="json") if error.card else None}
        raise HTTPException(status_code=409, detail=detail) from error


@router.get("/{card_id}", response_model=handoff.HandoffCard)
def get_handoff_card(card_id: str, x_demo_role: str = Header(default="LEAD")):
    if x_demo_role not in {"LEAD", "HR", "HM"}:
        raise HTTPException(status_code=403, detail="핸드오프 열람 권한이 없습니다")
    try:
        return handoff.get_card(card_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="핸드오프 카드를 찾을 수 없습니다") from error
    except HandoffStateError as error:
        raise HTTPException(status_code=409, detail={"code": "HANDOFF_STATE", "message": str(error)}) from error
