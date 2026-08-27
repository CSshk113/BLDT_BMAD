from pathlib import Path
import json

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


def _create_card(client: TestClient) -> str:
    _save_both_judgments(client)
    response = client.post("/api/handoff/generate", params={"criteria_version_id": "approved-v1", "application_id": "APPS-2"}, headers={"X-Demo-Role": "LEAD"})
    assert response.status_code == 200
    return response.json()["card"]["id"]


def _add_selected_question(client: TestClient, card_id: str, status: str = "SELECTED") -> str:
    question = {
        "id": "question-1",
        "original_question": "신규 고객을 발굴한 경험을 말씀해 주세요.",
        "current_question": "신규 고객을 발굴해 첫 미팅으로 연결한 경험을 말씀해 주세요.",
        "reason": "콜드 아웃바운드 실행 경험 확인",
        "criterion_item_ids": ["approved-v1-item-1"],
        "evidence_ids": ["mapping-1"],
        "question_type": "BEI",
        "status": status,
        "created_at": "2026-08-28T00:00:00+00:00",
        "edit_history": [],
    }
    card = client.get(f"/api/handoff/{card_id}").json()
    payload = card["payload"]
    payload["interview_questions"] = [question]
    with db.connect() as connection:
        connection.execute("UPDATE handoff_cards SET payload_json = ? WHERE id = ?", (json.dumps(payload, ensure_ascii=False), card_id))
        connection.commit()
    return question["id"]


def test_interview_verification_and_final_decision_preserve_comparison_and_audit(client: TestClient):
    card_id = _create_card(client)
    question_id = _add_selected_question(client, card_id)

    verification = client.post(f"/api/handoff/{card_id}/verifications", headers={"X-Demo-Role": "LEAD"}, json={
        "question_id": question_id,
        "interview_result": "3개 고객군을 직접 발굴했고 첫 미팅 전환 과정을 설명했습니다.",
    })
    assert verification.status_code == 200
    saved_card = verification.json()
    result = saved_card["payload"]["interview_results"][0]
    assert result["id"].startswith("verification-")
    assert result["question_id"] == question_id
    assert result["original_question"] == "신규 고객을 발굴한 경험을 말씀해 주세요."
    assert result["current_question"] == "신규 고객을 발굴해 첫 미팅으로 연결한 경험을 말씀해 주세요."
    assert result["criterion_item_ids"] == ["approved-v1-item-1"]
    assert result["evidence_ids"] == ["mapping-1"]
    assert result["initial_hypothesis"].startswith("콜드 아웃바운드 실행 경험 확인")
    assert result["interview_result"].startswith("3개 고객군")
    assert result["recorded_by"] == "LEAD"
    assert saved_card["payload"]["judgments"]["rows"][0]["hr_review"]["status"] == "FULFILLED"

    decision = client.post(f"/api/handoff/{card_id}/decision", headers={"X-Demo-Role": "LEAD"}, json={
        "decision": "인재풀 등록",
        "reason": "현재 포지션과의 적합성은 추가 확인이 필요하지만 후속 접촉 가치가 있습니다.",
    })
    assert decision.status_code == 200
    decision_card = decision.json()
    assert decision_card["payload"]["final_decision"]["decision"] == "인재풀 등록"
    assert decision_card["payload"]["final_decision"]["criteria_version_id"] == "approved-v1"
    assert all(event["source"] in {"HUMAN", "SYSTEM"} for event in decision_card["payload"]["audit_timeline"])
    assert decision_card["payload"]["audit_timeline"][-1]["source"] == "HUMAN"
    assert any(event["event_type"] == "FINAL_DECISION_RECORDED" for event in decision_card["payload"]["audit_timeline"])


def test_final_decision_gate_and_official_vocab(client: TestClient):
    card_id = _create_card(client)
    blocked = client.post(f"/api/handoff/{card_id}/decision", headers={"X-Demo-Role": "LEAD"}, json={"decision": "채용", "reason": "결정"})
    assert blocked.status_code == 409
    assert "선택된 질문" in blocked.json()["detail"]["message"]

    question_id = _add_selected_question(client, card_id)
    blocked = client.post(f"/api/handoff/{card_id}/decision", headers={"X-Demo-Role": "LEAD"}, json={"decision": "채용", "reason": "결정"})
    assert blocked.status_code == 409
    assert question_id in blocked.json()["detail"]["message"]

    invalid = client.post(f"/api/handoff/{card_id}/decision", headers={"X-Demo-Role": "LEAD"}, json={"decision": "자동 합격", "reason": "결정"})
    assert invalid.status_code == 422


def test_interview_and_decision_edits_require_reason_and_preserve_history(client: TestClient):
    card_id = _create_card(client)
    question_id = _add_selected_question(client, card_id)
    first = client.post(f"/api/handoff/{card_id}/verifications", headers={"X-Demo-Role": "LEAD"}, json={"question_id": question_id, "interview_result": "첫 결과"})
    assert first.status_code == 200
    missing_reason = client.post(f"/api/handoff/{card_id}/verifications", headers={"X-Demo-Role": "LEAD"}, json={"question_id": question_id, "interview_result": "수정 결과"})
    assert missing_reason.status_code == 422
    updated = client.post(f"/api/handoff/{card_id}/verifications", headers={"X-Demo-Role": "LEAD"}, json={"question_id": question_id, "interview_result": "수정 결과", "edit_reason": "면접 사실을 보완"})
    assert updated.status_code == 200
    assert updated.json()["payload"]["interview_results"][0]["edit_history"][0]["previous_result"] == "첫 결과"

    decision = client.post(f"/api/handoff/{card_id}/decision", headers={"X-Demo-Role": "LEAD"}, json={"decision": "채용", "reason": "검증 결과가 충분합니다."})
    assert decision.status_code == 200
    missing_reason = client.post(f"/api/handoff/{card_id}/decision", headers={"X-Demo-Role": "LEAD"}, json={"decision": "종료", "reason": "변경 결정"})
    assert missing_reason.status_code == 422
    revised = client.post(f"/api/handoff/{card_id}/decision", headers={"X-Demo-Role": "LEAD"}, json={"decision": "종료", "reason": "전형을 종료합니다.", "edit_reason": "추가 검토 후 결정 변경"})
    assert revised.status_code == 200
    assert revised.json()["payload"]["final_decision"]["edit_history"][0]["new_value"]["decision"] == "종료"


def test_interview_and_decision_are_lead_only(client: TestClient):
    card_id = _create_card(client)
    question_id = _add_selected_question(client, card_id)
    assert client.post(f"/api/handoff/{card_id}/verifications", headers={"X-Demo-Role": "HR"}, json={"question_id": question_id, "interview_result": "결과"}).status_code == 403
    assert client.post(f"/api/handoff/{card_id}/decision", headers={"X-Demo-Role": "HM"}, json={"decision": "채용", "reason": "사유"}).status_code == 403


def test_interview_gate_rejects_unselected_question_and_nonofficial_card(client: TestClient):
    card_id = _create_card(client)
    question_id = _add_selected_question(client, card_id, status="CANDIDATE")
    rejected = client.post(f"/api/handoff/{card_id}/verifications", headers={"X-Demo-Role": "LEAD"}, json={"question_id": question_id, "interview_result": "결과"})
    assert rejected.status_code == 409
    assert client.get(f"/api/handoff/{card_id}").json()["payload"]["interview_results"] == []

    with db.connect() as connection:
        row = connection.execute("SELECT payload_json FROM handoff_cards WHERE id = ?", (card_id,)).fetchone()
        payload = json.loads(row["payload_json"])
        payload["interview_questions"][0]["status"] = "SELECTED"
        connection.execute("UPDATE handoff_cards SET payload_json = ? WHERE id = ?", (json.dumps(payload, ensure_ascii=False), card_id))
        connection.execute("UPDATE criteria_versions SET status = 'DRAFT' WHERE id = 'approved-v1'")
        connection.commit()
    rejected = client.post(f"/api/handoff/{card_id}/verifications", headers={"X-Demo-Role": "LEAD"}, json={"question_id": question_id, "interview_result": "결과"})
    assert rejected.status_code == 409


def test_blank_interview_and_decision_reasons_are_rejected(client: TestClient):
    card_id = _create_card(client)
    question_id = _add_selected_question(client, card_id)
    blank_result = client.post(f"/api/handoff/{card_id}/verifications", headers={"X-Demo-Role": "LEAD"}, json={"question_id": question_id, "interview_result": "   "})
    assert blank_result.status_code == 422
    assert client.get(f"/api/handoff/{card_id}").json()["payload"]["interview_results"] == []

    result = client.post(f"/api/handoff/{card_id}/verifications", headers={"X-Demo-Role": "LEAD"}, json={"question_id": question_id, "interview_result": "확인 결과"})
    assert result.status_code == 200
    blank_reason = client.post(f"/api/handoff/{card_id}/decision", headers={"X-Demo-Role": "LEAD"}, json={"decision": "채용", "reason": "   "})
    assert blank_reason.status_code == 422
