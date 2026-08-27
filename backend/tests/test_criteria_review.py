from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import db
from backend.app.main import app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "test.db")
    return TestClient(app)


def test_review_matrix_preserves_independent_roles_and_open_conflicts(client: TestClient):
    response = client.get("/api/criteria/cv-b2b-sales-v4/conflicts")

    assert response.status_code == 200
    payload = response.json()
    assert payload["open_conflict_count"] == 2
    first = payload["rows"][0]
    assert first["conflict_status"] == "OPEN"
    assert first["hr_review"]["reviewer_role"] == "HR"
    assert first["hm_review"]["reviewer_role"] == "HM"
    assert "상태" in first["differences"]


def test_one_sided_review_is_pending_not_conflict(client: TestClient):
    rows = client.get("/api/criteria/cv-b2b-sales-v4/conflicts").json()["rows"]

    one_sided = next(row for row in rows if row["criterion_item_id"].endswith("item-2"))
    assert one_sided["conflict_status"] == "PENDING"
    assert one_sided["hm_review"] is None


def test_reviewer_can_update_only_own_review_log(client: TestClient):
    response = client.post(
        "/api/criteria/cv-b2b-sales-v4/reviews",
        headers={"X-Demo-Role": "HR"},
        json={
            "application_id": "APPS-2",
            "reviewer_role": "HM",
            "reviews": [{
                "criterion_item_id": "cv-b2b-sales-v4-item-1",
                "status": "FULFILLED",
                "reason_text": "변경 시도",
                "source_location": "p.1",
            }],
        },
    )

    assert response.status_code == 403


def test_saving_review_keeps_roles_separate_and_recomputes_conflict(client: TestClient):
    response = client.post(
        "/api/criteria/cv-b2b-sales-v4/reviews",
        headers={"X-Demo-Role": "HM"},
        json={
            "application_id": "APPS-2",
            "reviewer_role": "HM",
            "reviews": [{
                "criterion_item_id": "cv-b2b-sales-v4-item-2",
                "status": "FULFILLED",
                "reason_text": "파이프라인 운영 범위가 확인됩니다.",
                "source_location": "p.3 · 프로젝트",
            }],
        },
    )

    assert response.status_code == 200
    row = next(row for row in response.json()["rows"] if row["criterion_item_id"].endswith("item-2"))
    assert row["hr_review"]["reviewer_role"] == "HR"
    assert row["hm_review"]["reviewer_role"] == "HM"
    assert row["conflict_status"] == "OPEN"


def test_review_requires_reason_and_source_location(client: TestClient):
    response = client.post(
        "/api/criteria/cv-b2b-sales-v4/reviews",
        json={
            "application_id": "APPS-2",
            "reviewer_role": "HR",
            "reviews": [{
                "criterion_item_id": "cv-b2b-sales-v4-item-1",
                "status": "FULFILLED",
                "reason_text": "",
                "source_location": "",
            }],
        },
    )

    assert response.status_code == 422


def test_each_required_evidence_field_is_validated_independently(client: TestClient):
    base_review = {
        "criterion_item_id": "cv-b2b-sales-v4-item-1",
        "status": "FULFILLED",
        "reason_text": "근거",
        "source_location": "p.1",
    }
    base_payload = {"application_id": "APPS-2", "reviewer_role": "HR", "reviews": [base_review]}
    missing_location = {**base_payload, "reviews": [{**base_review, "source_location": "   "}]}
    missing_reason = {**base_payload, "reviews": [{**base_review, "reason_text": "   "}]}

    assert client.post("/api/criteria/cv-b2b-sales-v4/reviews", json=missing_location).status_code == 422
    assert client.post("/api/criteria/cv-b2b-sales-v4/reviews", json=missing_reason).status_code == 422


def test_duplicate_criteria_in_one_submission_is_rejected(client: TestClient):
    payload = {
        "application_id": "APPS-2",
        "reviewer_role": "HR",
        "reviews": [
            {"criterion_item_id": "cv-b2b-sales-v4-item-1", "status": "FULFILLED", "reason_text": "첫 근거", "source_location": "p.1"},
            {"criterion_item_id": "cv-b2b-sales-v4-item-1", "status": "UNFULFILLED", "reason_text": "두 번째 근거", "source_location": "p.2"},
        ],
    }

    assert client.post("/api/criteria/cv-b2b-sales-v4/reviews", json=payload).status_code == 422
