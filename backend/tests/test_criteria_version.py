from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import db
from backend.app.main import app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "test.db")
    return TestClient(app)


def test_lists_seeded_draft_with_position_criteria(client: TestClient):
    response = client.get("/api/criteria")

    assert response.status_code == 200
    version = response.json()[0]
    assert version["id"] == "cv-b2b-sales-v4"
    assert version["status"] == "DRAFT"
    assert version["position_name"] == "B2B 영업 매니저 5년 이상 ver.4"
    assert len(version["items"]) == 3


def test_creating_version_keeps_original_and_creates_draft(client: TestClient):
    response = client.post("/api/criteria/cv-b2b-sales-v4/versions")

    assert response.status_code == 201
    created = response.json()
    assert created["id"] != "cv-b2b-sales-v4"
    assert created["status"] == "DRAFT"
    assert [item["criterion_text"] for item in created["items"]] == [
        "콜드 아웃바운드 영업 경험",
        "B2B 세일즈 파이프라인 운영 경험",
        "CRM 또는 세일즈 데이터 기반 성과 관리",
    ]
    assert client.get("/api/criteria/cv-b2b-sales-v4").json()["status"] == "DRAFT"


def test_invalidating_one_version_does_not_touch_another(client: TestClient):
    clone = client.post("/api/criteria/cv-b2b-sales-v4/versions").json()
    clone_item_id = clone["items"][0]["id"]
    with db.connect() as connection:
        connection.execute(
            "INSERT INTO mapping_results VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'COMPLETED')",
            (
                "mapping-clone-1",
                clone["id"],
                "APPS-CLONE",
                "복제 기준 지원자",
                clone_item_id,
                "복제 기준 원문",
                "p.1",
                "원문 확인 가능",
            ),
        )
        connection.commit()

    client.patch(
        "/api/criteria/cv-b2b-sales-v4",
        json={"items": [
            {"criterion_text": "원본 기준 변경"},
            {"criterion_text": "B2B 세일즈 파이프라인 운영 경험"},
            {"criterion_text": "CRM 또는 세일즈 데이터 기반 성과 관리"},
        ]},
    )

    original_preview = client.get("/api/criteria/cv-b2b-sales-v4/preview").json()
    clone_preview = client.get(f"/api/criteria/{clone['id']}/preview").json()
    assert original_preview["mappings"][0]["mapping_status"] == "INVALIDATED"
    assert clone_preview["mappings"][0]["mapping_status"] == "COMPLETED"


def test_changed_draft_invalidates_existing_mapping_and_requires_rerun(client: TestClient):
    response = client.patch(
        "/api/criteria/cv-b2b-sales-v4",
        json={"items": [
            {"criterion_text": "수정된 콜드 아웃바운드 영업 경험"},
            {"criterion_text": "B2B 세일즈 파이프라인 운영 경험"},
            {"criterion_text": "CRM 또는 세일즈 데이터 기반 성과 관리"},
        ]},
    )

    assert response.status_code == 200
    assert response.json()["invalidated_mapping_count"] == 1
    assert response.json()["rerun_required"] is True
    preview = client.get("/api/criteria/cv-b2b-sales-v4/preview").json()
    assert preview["is_preview"] is True
    assert preview["mappings"][0]["mapping_status"] == "INVALIDATED"


def test_draft_cannot_generate_official_handoff(client: TestClient):
    response = client.post(
        "/api/handoff/generate",
        params={"criteria_version_id": "cv-b2b-sales-v4"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "CRITERIA_NOT_APPROVED"
    assert "기준 버전 승인" in response.json()["detail"]["missing_conditions"]


def test_unknown_criteria_version_returns_not_found_for_official_action(client: TestClient):
    response = client.post(
        "/api/handoff/generate",
        params={"criteria_version_id": "cv-missing"},
    )

    assert response.status_code == 404
