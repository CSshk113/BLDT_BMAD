"""핸드오프 인터뷰 질문 후보 API."""

from fastapi import APIRouter, Header, HTTPException

from backend.app.models.handoff import (
    HandoffStateError,
    QuestionCandidate,
    QuestionCandidateEditInput,
    QuestionCandidateGenerationResponse,
    QuestionCandidateListResponse,
    QuestionCandidateSelectionInput,
)
from backend.app.services import handoff
from backend.app.services.questions import QuestionGenerationError


router = APIRouter(prefix="/api/questions", tags=["questions"])
READ_ROLES = {"LEAD", "HR", "HM"}


def _require_read_role(role: str) -> None:
    if role not in READ_ROLES:
        raise HTTPException(status_code=403, detail="질문 후보 열람 권한이 없습니다")


@router.post("/{card_id}/generate", response_model=QuestionCandidateListResponse)
def generate_questions(card_id: str, x_demo_role: str = Header(default="LEAD")):
    if x_demo_role != "LEAD":
        raise HTTPException(status_code=403, detail="질문 후보 생성 권한이 없습니다")
    try:
        return handoff.generate_question_candidates(card_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="핸드오프 카드를 찾을 수 없습니다") from error
    except HandoffStateError as error:
        raise HTTPException(status_code=409, detail={"code": "QUESTION_GATE", "message": str(error), "card": error.card.model_dump(mode="json") if error.card else None}) from error
    except QuestionGenerationError as error:
        raise HTTPException(status_code=503 if not error.upstream else 502, detail={"code": "QUESTION_MODEL_UNAVAILABLE", "message": str(error), "retryable": True}) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": "QUESTION_VALIDATION_FAILED", "message": str(error)}) from error


@router.get("/{card_id}", response_model=QuestionCandidateListResponse)
def list_questions(card_id: str, selected_only: bool = False, x_demo_role: str = Header(default="LEAD")):
    _require_read_role(x_demo_role)
    try:
        return handoff.list_question_candidates(card_id, selected_only=selected_only)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="핸드오프 카드를 찾을 수 없습니다") from error
    except HandoffStateError as error:
        raise HTTPException(status_code=409, detail={"code": "QUESTION_STATE", "message": str(error)}) from error


@router.patch("/{card_id}/{question_id}", response_model=QuestionCandidate)
def edit_question(card_id: str, question_id: str, payload: QuestionCandidateEditInput, x_demo_role: str = Header(default="LEAD")):
    try:
        return handoff.update_question_candidate(card_id, question_id, payload, x_demo_role)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="질문 후보를 찾을 수 없습니다") from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except HandoffStateError as error:
        raise HTTPException(status_code=409, detail={"code": "QUESTION_STATE", "message": str(error)}) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": "QUESTION_VALIDATION_FAILED", "message": str(error)}) from error


@router.delete("/{card_id}/{question_id}", response_model=QuestionCandidate)
def delete_question(card_id: str, question_id: str, x_demo_role: str = Header(default="LEAD")):
    try:
        return handoff.delete_question_candidate(card_id, question_id, x_demo_role)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="질문 후보를 찾을 수 없습니다") from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except HandoffStateError as error:
        raise HTTPException(status_code=409, detail={"code": "QUESTION_STATE", "message": str(error)}) from error


@router.post("/{card_id}/{question_id}/select", response_model=QuestionCandidate)
def select_question(card_id: str, question_id: str, payload: QuestionCandidateSelectionInput, x_demo_role: str = Header(default="LEAD")):
    try:
        return handoff.select_question_candidate(card_id, question_id, payload.selected, x_demo_role)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="질문 후보를 찾을 수 없습니다") from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except HandoffStateError as error:
        raise HTTPException(status_code=409, detail={"code": "QUESTION_STATE", "message": str(error)}) from error
