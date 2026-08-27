from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import db
from backend.app.main import app


VERSION_ID = "cv-b2b-sales-v4"
ITEM_1 = f"{VERSION_ID}-item-1"
ITEM_2 = f"{VERSION_ID}-item-2"
ITEM_3 = f"{VERSION_ID}-item-3"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "test.db")
    return TestClient(app)


def resolve(client: TestClient, item_id: str):
    return client.post(
        f"/api/criteria/{VERSION_ID}/conflicts",
        headers={"X-Demo-Role": "HR"},
        json={
            "application_id": "APPS-2",
            "criterion_item_id": item_id,
            "resolution_reason": "원문 범위와 역할 차이를 확인하고 HR·HM 판단을 각각 보존합니다.",
        },
    )


def complete_pending_review(client: TestClient):
    return client.post(
        f"/api/criteria/{VERSION_ID}/reviews",
        headers={"X-Demo-Role": "HM"},
        json={
            "application_id": "APPS-2",
            "reviewer_role": "HM",
            "reviews": [{
                "criterion_item_id": ITEM_2,
                "status": "UNVERIFIABLE",
                "reason_text": "파이프라인 운영 도구와 담당 범위가 확인되지 않습니다.",
                "source_location": "p.3 · 프로젝트",
            }],
        },
    )


def test_approval_is_blocked_when_open_conflicts_remain(client: TestClient):
    response = client.post(f"/api/criteria/{VERSION_ID}/approve", headers={"X-Demo-Role": "HR"})

    assert response.status_code == 409
    assert "열린 충돌" in response.json()["detail"]
    assert client.get(f"/api/criteria/{VERSION_ID}").json()["status"] == "DRAFT"


def test_approval_is_blocked_when_reviews_are_still_pending(client: TestClient):
    assert resolve(client, ITEM_1).status_code == 200
    assert resolve(client, ITEM_3).status_code == 200

    response = client.post(f"/api/criteria/{VERSION_ID}/approve", headers={"X-Demo-Role": "HR"})

    assert response.status_code == 409
    assert "양쪽 검토 완료" in response.json()["detail"]


def test_mutating_gate_endpoints_require_a_reviewer_role(client: TestClient):
    approval = client.post(f"/api/criteria/{VERSION_ID}/approve")
    resolution = client.post(
        f"/api/criteria/{VERSION_ID}/conflicts",
        json={"application_id": "APPS-2", "criterion_item_id": ITEM_1, "resolution_reason": "역할 헤더 누락"},
    )

    assert approval.status_code == 403
    assert resolution.status_code == 403


def test_hr_can_resolve_conflict_without_overwriting_review_logs(client: TestClient):
    response = resolve(client, ITEM_1)

    assert response.status_code == 200
    row = response.json()["rows"][0]
    assert row["conflict_status"] == "RESOLVED"
    assert row["resolution"]["resolved_by"] == "HR"
    assert row["resolution"]["resolution_reason"].startswith("원문 범위")
    assert row["hr_review"]["reviewer_role"] == "HR"
    assert row["hm_review"]["reviewer_role"] == "HM"

    # Re-submit with the HM role to verify the server-side permission boundary.
    forbidden = client.post(
        f"/api/criteria/{VERSION_ID}/conflicts",
        headers={"X-Demo-Role": "HM"},
        json={"application_id": "APPS-2", "criterion_item_id": ITEM_3, "resolution_reason": "HM 해결 시도"},
    )
    assert forbidden.status_code == 403


def test_approval_requires_all_reviews_then_unlocks_handoff(client: TestClient):
    assert resolve(client, ITEM_1).status_code == 200
    assert resolve(client, ITEM_3).status_code == 200
    assert complete_pending_review(client).status_code == 200

    approval = client.post(f"/api/criteria/{VERSION_ID}/approve", headers={"X-Demo-Role": "HR"})

    assert approval.status_code == 200
    payload = approval.json()
    assert payload["criteria_version_id"] == VERSION_ID
    assert payload["approved_by"] == "HR"
    assert payload["approved_at"]
    assert payload["version"]["status"] == "APPROVED"
    assert payload["version"]["approved_by"] == "HR"

    handoff = client.post("/api/handoff/generate", params={"criteria_version_id": VERSION_ID})
    assert handoff.status_code == 200
    assert handoff.json() == {"status": "ready", "handoff_unlocked": True, "criteria_version_id": VERSION_ID}


def test_changed_review_reopens_a_resolved_conflict(client: TestClient):
    assert resolve(client, ITEM_1).status_code == 200

    changed_review = client.post(
        f"/api/criteria/{VERSION_ID}/reviews",
        headers={"X-Demo-Role": "HR"},
        json={
            "application_id": "APPS-2",
            "reviewer_role": "HR",
            "reviews": [{
                "criterion_item_id": ITEM_1,
                "status": "UNFULFILLED",
                "reason_text": "변경된 검토 결과로 다시 확인해야 합니다.",
                "source_location": "p.4 · 경력기술서",
            }],
        },
    )

    assert changed_review.status_code == 200
    assert changed_review.json()["rows"][0]["conflict_status"] == "OPEN"
    assert changed_review.json()["rows"][0]["resolution"] is None


def test_unchanged_review_keeps_a_resolved_conflict(client: TestClient):
    assert resolve(client, ITEM_1).status_code == 200

    unchanged_review = client.post(
        f"/api/criteria/{VERSION_ID}/reviews",
        headers={"X-Demo-Role": "HR"},
        json={
            "application_id": "APPS-2",
            "reviewer_role": "HR",
            "reviews": [{
                "criterion_item_id": ITEM_1,
                "status": "FULFILLED",
                "reason_text": "신규 고객 발굴 경험이 명시되어 있습니다.",
                "source_location": "p.2 · 경력기술서",
            }],
        },
    )

    assert unchanged_review.status_code == 200
    assert unchanged_review.json()["rows"][0]["conflict_status"] == "RESOLVED"
    assert unchanged_review.json()["rows"][0]["resolution"] is not None
