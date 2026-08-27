from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import db
from backend.app.main import app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "handoff.db")
    markdown = tmp_path / "candidate.md"
    markdown.write_text("# 경력\n\n콜드 아웃바운드 경험과 CRM 성과 관리 근거입니다.", encoding="utf-8")
    with db.connect() as connection:
        db.initialize_schema(connection)
        connection.execute("INSERT INTO criteria_versions (id, position_name, status, created_at, updated_at) VALUES ('approved-v1', 'B2B 영업 매니저', 'APPROVED', '2026-08-27T00:00:00+00:00', '2026-08-27T00:00:00+00:00')")
        for index, text in enumerate(("콜드 아웃바운드 경험", "CRM 성과 관리"), start=1):
            item_id = f"approved-v1-item-{index}"
            connection.execute("INSERT INTO criteria_items (id, criteria_version_id, criterion_text, requirement_type, sort_order) VALUES (?, 'approved-v1', ?, '필수', ?)", (item_id, text, index))
        connection.execute("INSERT INTO applications (id, candidate_token, position_name, criteria_version_id, source_type, ledger_metadata_json, created_at, updated_at) VALUES ('APPS-2', '후보081', 'B2B 영업 매니저', 'approved-v1', 'UPLOAD', '{}', '2026-08-27T00:00:00+00:00', '2026-08-27T00:00:00+00:00')")
        connection.execute("INSERT INTO processing_runs (id, application_id, criteria_version_id, status, current_step, parser_model, received_at, completed_at, created_at, updated_at) VALUES ('run-1', 'APPS-2', 'approved-v1', 'COMPLETED', 'MAPPING', 'test', '2026-08-27T00:00:00+00:00', '2026-08-27T00:00:00+00:00', '2026-08-27T00:00:00+00:00', '2026-08-27T00:00:00+00:00')")
        connection.execute("INSERT INTO application_artifacts (id, application_id, processing_run_id, artifact_type, storage_path, original_filename, mime_type, is_current, created_at) VALUES ('artifact-1', 'APPS-2', 'run-1', 'NORMALIZED_MARKDOWN', ?, 'candidate.md', 'text/markdown', 1, '2026-08-27T00:00:00+00:00')", (str(markdown),))
        for index in range(1, 3):
            connection.execute("INSERT INTO mapping_results (id, criteria_version_id, application_id, processing_run_id, source_artifact_id, applicant_label, criterion_item_id, citation, location, location_kind, evidence_status, mapping_status) VALUES (?, 'approved-v1', 'APPS-2', 'run-1', 'artifact-1', '후보081', ?, ?, 'p.1', 'EXACT', '충족', 'COMPLETED')", (f"mapping-{index}", f"approved-v1-item-{index}", "콜드 아웃바운드 경험과 CRM 성과 관리 근거입니다."))
        connection.commit()
    return TestClient(app)


def _save_both_judgments(client: TestClient):
    for role, verdict in (("HR", "스크리닝 통과"), ("HM", "합격 - 필수 역량 충족")):
        response = client.post("/api/criteria/approved-v1/judgments", headers={"X-Demo-Role": role}, json={
            "application_id": "APPS-2", "reviewer_role": role, "document_verdict": verdict,
            "reviews": [
                {"criterion_item_id": "approved-v1-item-1", "status": "FULFILLED", "reason_text": f"{role} 근거 1", "citation": "콜드 아웃바운드 경험과 CRM 성과 관리 근거입니다.", "source_location": "p.1"},
                {"criterion_item_id": "approved-v1-item-2", "status": "FULFILLED", "reason_text": f"{role} 근거 2", "citation": "콜드 아웃바운드 경험과 CRM 성과 관리 근거입니다.", "source_location": "p.1"},
            ],
        })
        assert response.status_code == 200


def test_handoff_card_contains_traceable_payload_and_is_idempotent(client: TestClient):
    _save_both_judgments(client)
    response = client.post("/api/handoff/generate", params={"criteria_version_id": "approved-v1", "application_id": "APPS-2"}, headers={"X-Demo-Role": "LEAD"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["already_exists"] is False
    card = payload["card"]
    assert card["status"] == "READY"
    assert card["payload"]["criteria"]["version_id"] == "approved-v1"
    assert card["payload"]["evidence"][0]["id"] == "mapping-1"
    assert card["payload"]["source_document"]["artifact_id"] == "artifact-1"
    assert len(card["payload"]["judgments"]["rows"]) == 2
    assert card["payload"]["interview_questions"] == []

    duplicate = client.post("/api/handoff/generate", params={"criteria_version_id": "approved-v1", "application_id": "APPS-2"})
    assert duplicate.status_code == 200
    assert duplicate.json()["already_exists"] is True
    assert duplicate.json()["card"]["id"] == card["id"]
    assert client.get(f"/api/handoff/{card['id']}").json()["id"] == card["id"]


def test_handoff_blocks_when_judgment_logs_are_missing(client: TestClient):
    response = client.post("/api/handoff/generate", params={"criteria_version_id": "approved-v1", "application_id": "APPS-2"})

    assert response.status_code == 409
    assert "HR 공식 판단 로그 전체" in response.json()["detail"]["missing_conditions"]
    assert "HM 공식 판단 로그 전체" in response.json()["detail"]["missing_conditions"]
