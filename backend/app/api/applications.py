"""Application upload and processing-status API."""

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from backend.app.models.applications import ApplicationDetail, ApplicationDocument, ApplicationsList
from backend.app.services import applications


router = APIRouter(prefix="/api/applications", tags=["applications"])


@router.get("", response_model=ApplicationsList)
def get_applications() -> ApplicationsList:
    return applications.list_applications()


@router.get("/{application_id}", response_model=ApplicationDetail)
def get_application(application_id: str) -> ApplicationDetail:
    try:
        return applications.get_application(application_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="지원서를 찾을 수 없습니다") from error


@router.get("/{application_id}/document", response_model=ApplicationDocument)
def get_document(application_id: str, run_id: str | None = None) -> ApplicationDocument:
    try:
        return applications.get_document(application_id, run_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="지원서를 찾을 수 없습니다") from error
    except applications.DocumentNotReadyError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/{application_id}/process", response_model=ApplicationDetail)
def reprocess_application(application_id: str) -> ApplicationDetail:
    try:
        return applications.reprocess_application(application_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="재처리할 지원서를 찾을 수 없습니다") from error


@router.post("", response_model=ApplicationDetail, status_code=status.HTTP_201_CREATED)
async def upload_application(
    file: UploadFile = File(...),
    candidate_token: str = Form(...),
    position_name: str = Form(...),
    criteria_version_id: str = Form(...),
) -> ApplicationDetail:
    content = await file.read(applications.MAX_UPLOAD_BYTES + 1)
    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".pdf") or not content.startswith(b"%PDF"):
        raise HTTPException(status_code=415, detail="PDF 파일만 업로드할 수 있습니다")
    if len(content) > applications.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"PDF 파일은 {applications.MAX_UPLOAD_BYTES // (1024 * 1024)}MB 이하만 업로드할 수 있습니다")
    try:
        return applications.upload_pdf(
            filename=filename,
            content_type=file.content_type,
            content=content,
            candidate_token=candidate_token,
            position_name=position_name,
            criteria_version_id=criteria_version_id,
        )
    except applications.InvalidUploadError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
