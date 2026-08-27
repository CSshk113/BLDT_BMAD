from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.criteria import router as criteria_router
from backend.app.services.criteria import reject_official_action


app = FastAPI(title="Evidence Handoff API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(criteria_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/handoff/generate")
def generate_handoff(criteria_version_id: str):
    try:
        rejection = reject_official_action(criteria_version_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="기준 버전을 찾을 수 없습니다") from error
    if rejection:
        raise HTTPException(status_code=403, detail=rejection.model_dump())
    return {"status": "ready", "handoff_unlocked": True, "criteria_version_id": criteria_version_id}
