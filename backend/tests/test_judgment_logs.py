from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import db
from backend.app.main import app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "judgments.db")
    with db.connect() as connection:
        db.initialize_schema(connection)
        connection.execute(
            "INSERT INTO criteria_versions (id, position_name, status, created_at, updated_at) VALUES ('approved-v1', 'B2B 영업 매니저', 'APPROVED', '2026-08-27T00:00:00+00:00', '2026-08-27T00:00:00+00:00')"
        )
        for index, text in enumerate(("콜드 아웃바운드 경험", "CRM 성과 관리"), start=1):
            connection.execute(
                "INSERT INTO criteria_items (id, criteria_version_id, criterion_text, requirement_type, sort_order) VALUES (?, 'approved-v1', ?, '필수', ?)",
                (f"approved-v1-item-{index}", text, index),
            )
            connection.execute(
                """
                INSERT INTO mapping_results
                (id, criteria_version_id, application_id, processing_run_id, source_artifact_id,
                 applicant_label, criterion_item_id, citation, location, location_kind,
                 evidence_status, mapping_status)
                VALUES (?, 'approved-v1', 'APPS-2', 'run-1', 'artifact-1', '후보 · APPS-2', ?, ?, ?, 'EXACT', '충족', 'COMPLETED')
                """,
                (f"mapping-{index}", f"approved-v1-item-{index}", f"근거 {index}", f"p.{index}"),
            )
        connection.commit()
    return TestClient(app)


def review(item_id: str, number: int, status: str = "FULFILLED") -> dict:
    return {
        "criterion_item_id": item_id,
        "status": status,
        "reason_text": f"검토 사유 {number}",
        "citation": f"근거 {number}",
        "source_location": f"p.{number}",
        "edit_reason": "판단 재검토",
    }


def test_official_judgments_keep_hr_hm_separate_and_compare_differences(client: TestClient):
    hr = client.post(
        "/api/criteria/approved-v1/judgments",
        headers={"X-Demo-Role": "HR"},
        json={"application_id": "APPS-2", "reviewer_role": "HR", "document_verdict": "스크리닝 통과", "reviews": [review("approved-v1-item-1", 1)]},
    )
    hm = client.post(
        "/api/criteria/approved-v1/judgments",
        headers={"X-Demo-Role": "HM"},
        json={"application_id": "APPS-2", "reviewer_role": "HM", "document_verdict": "합격 - 필수 역량 충족", "reviews": [review("approved-v1-item-1", 1, "PARTIALLY_FULFILLED")]},
    )

    assert hr.status_code == 200
    assert hm.status_code == 200
    row = next(row for row in hm.json()["rows"] if row["criterion_item_id"].endswith("item-1"))
    assert row["hr_review"]["review_scope"] == "OFFICIAL"
    assert row["hm_review"]["review_scope"] == "OFFICIAL"
    assert "상태" in row["differences"]
    assert hm.json()["hr_document_judgment"]["verdict"] == "스크리닝 통과"
    assert hm.json()["hm_document_judgment"]["verdict"] == "합격 - 필수 역량 충족"


def test_draft_and_incomplete_mapping_are_blocked(client: TestClient):
    with db.connect() as connection:
        connection.execute("DELETE FROM mapping_results WHERE criterion_item_id = 'approved-v1-item-2'")
        connection.commit()
    incomplete = client.post(
        "/api/criteria/approved-v1/judgments",
        headers={"X-Demo-Role": "HR"},
        json={"application_id": "APPS-2", "reviewer_role": "HR", "reviews": [review("approved-v1-item-1", 1)]},
    )
    assert incomplete.status_code == 409

    response = client.post(
        "/api/criteria/approved-v1/judgments",
        headers={"X-Demo-Role": "HR"},
        json={"application_id": "MISSING", "reviewer_role": "HR", "reviews": [review("approved-v1-item-1", 1)]},
    )
    assert response.status_code == 409

    with db.connect() as connection:
        connection.execute("UPDATE criteria_versions SET status = 'DRAFT' WHERE id = 'approved-v1'")
        connection.commit()
    draft_response = client.post(
        "/api/criteria/approved-v1/judgments",
        headers={"X-Demo-Role": "HR"},
        json={"application_id": "APPS-2", "reviewer_role": "HR", "reviews": [review("approved-v1-item-1", 1)]},
    )
    assert draft_response.status_code == 409


def test_missing_citation_is_rejected_unless_unverifiable(client: TestClient):
    missing = review("approved-v1-item-1", 1)
    missing["citation"] = ""
    assert client.post("/api/criteria/approved-v1/judgments", headers={"X-Demo-Role": "HR"}, json={"application_id": "APPS-2", "reviewer_role": "HR", "reviews": [missing]}).status_code == 422

    unverifiable = review("approved-v1-item-2", 2, "UNVERIFIABLE")
    unverifiable["citation"] = ""
    unverifiable["source_location"] = ""
    response = client.post("/api/criteria/approved-v1/judgments", headers={"X-Demo-Role": "HR"}, json={"application_id": "APPS-2", "reviewer_role": "HR", "reviews": [unverifiable]})
    assert response.status_code == 200


def test_other_role_and_invalid_document_verdict_are_rejected(client: TestClient):
    payload = {"application_id": "APPS-2", "reviewer_role": "HM", "reviews": [review("approved-v1-item-1", 1)]}
    assert client.post("/api/criteria/approved-v1/judgments", headers={"X-Demo-Role": "HR"}, json=payload).status_code == 403
    payload["reviewer_role"] = "HR"
    payload["document_verdict"] = "합격 - 필수 역량 충족"
    assert client.post("/api/criteria/approved-v1/judgments", headers={"X-Demo-Role": "HR"}, json=payload).status_code == 409


def test_edit_history_keeps_previous_values(client: TestClient):
    payload = {"application_id": "APPS-2", "reviewer_role": "HR", "reviews": [review("approved-v1-item-1", 1)]}
    assert client.post("/api/criteria/approved-v1/judgments", headers={"X-Demo-Role": "HR"}, json=payload).status_code == 200
    changed = review("approved-v1-item-1", 1, "PARTIALLY_FULFILLED")
    changed["reason_text"] = "변경된 사유"
    response = client.post("/api/criteria/approved-v1/judgments", headers={"X-Demo-Role": "HR"}, json={**payload, "reviews": [changed]})
    assert response.status_code == 200
    saved = next(row["hr_review"] for row in response.json()["rows"] if row["criterion_item_id"].endswith("item-1"))
    assert saved["status"] == "PARTIALLY_FULFILLED"
    assert saved["edit_history"][0]["previous"]["status"] == "FULFILLED"
    assert saved["edit_history"][0]["changed"]["reason_text"] == "변경된 사유"
