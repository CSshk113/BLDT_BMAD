from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import db
from backend.app.main import app
from backend.app.services.criteria import normalize_source_location


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
    assert payload["application_summary"] == {
        "application_id": "APPS-2",
        "candidate_token": "후보081",
        "position_name": "B2B 영업 매니저 5년 이상 ver.4",
        "source": "원티드",
        "excerpt": '"신규 고객 30개사를 직접 발굴하고 콜드 아웃바운드로 미팅을 만들었습니다."',
        "source_location": "p.2 · 경력기술서",
    }


def test_source_location_normalization_preserves_page_ranges_and_aliases():
    assert normalize_source_location("3페이지 / 프로젝트") == normalize_source_location("p.3 · 프로젝트")
    assert normalize_source_location("페이지 3 프로젝트") == normalize_source_location("page 3 / 프로젝트")
    assert normalize_source_location("p.2-3 · 프로젝트") != normalize_source_location("p.23 · 프로젝트")


def test_same_status_and_location_with_different_wording_is_not_a_conflict(client: TestClient):
    response = client.post(
        "/api/criteria/cv-b2b-sales-v4/reviews",
        headers={"X-Demo-Role": "HM"},
        json={
            "application_id": "APPS-2",
            "reviewer_role": "HM",
            "reviews": [{
                "criterion_item_id": "cv-b2b-sales-v4-item-2",
                "status": "UNVERIFIABLE",
                "reason_text": "운영 도구와 담당 범위는 확인되지 않았습니다.",
                "source_location": "3페이지 / 프로젝트",
            }],
        },
    )

    assert response.status_code == 200
    row = next(row for row in response.json()["rows"] if row["criterion_item_id"].endswith("item-2"))
    assert row["conflict_status"] == "NONE"
    assert row["differences"] == []
    assert row["hr_review"]["reason_text"] != row["hm_review"]["reason_text"]
    assert row["hr_review"]["source_location"] == "p.3 · 프로젝트"
    assert row["hm_review"]["source_location"] == "3페이지 / 프로젝트"


def test_different_normalized_location_remains_a_conflict(client: TestClient):
    response = client.post(
        "/api/criteria/cv-b2b-sales-v4/reviews",
        headers={"X-Demo-Role": "HM"},
        json={
            "application_id": "APPS-2",
            "reviewer_role": "HM",
            "reviews": [{
                "criterion_item_id": "cv-b2b-sales-v4-item-2",
                "status": "UNVERIFIABLE",
                "reason_text": "같은 기준을 확인했습니다.",
                "source_location": "p.4 · 프로젝트",
            }],
        },
    )

    assert response.status_code == 200
    row = next(row for row in response.json()["rows"] if row["criterion_item_id"].endswith("item-2"))
    assert row["conflict_status"] == "OPEN"
    assert row["differences"] == ["원문 위치"]


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
