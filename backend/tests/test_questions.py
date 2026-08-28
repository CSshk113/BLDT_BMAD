from pathlib import Path
import json
from urllib import request as url_request

import pytest
from fastapi.testclient import TestClient

from backend.app import db
from backend.app.main import app
from backend.app.services import questions


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "questions.db")
    markdown = tmp_path / "candidate.md"
    markdown.write_text("# 경력\n\n콜드 아웃바운드와 CRM 파이프라인을 관리했습니다.", encoding="utf-8")
    with db.connect() as connection:
        db.initialize_schema(connection)
        connection.execute("INSERT INTO criteria_versions (id, position_name, status, created_at, updated_at) VALUES ('approved-v1', 'B2B 영업 매니저', 'APPROVED', '2026-08-28T00:00:00+00:00', '2026-08-28T00:00:00+00:00')")
        for index, text in enumerate(("콜드 아웃바운드 경험", "CRM 성과 관리"), start=1):
            connection.execute("INSERT INTO criteria_items (id, criteria_version_id, criterion_text, requirement_type, sort_order) VALUES (?, 'approved-v1', ?, '필수', ?)", (f"item-{index}", text, index))
        connection.execute("INSERT INTO applications (id, candidate_token, position_name, criteria_version_id, source_type, ledger_metadata_json, created_at, updated_at) VALUES ('APPS-2', '후보081', 'B2B 영업 매니저', 'approved-v1', 'UPLOAD', '{}', '2026-08-28T00:00:00+00:00', '2026-08-28T00:00:00+00:00')")
        connection.execute("INSERT INTO processing_runs (id, application_id, criteria_version_id, status, current_step, parser_model, received_at, completed_at, created_at, updated_at) VALUES ('run-1', 'APPS-2', 'approved-v1', 'COMPLETED', 'MAPPING', 'test', '2026-08-28T00:00:00+00:00', '2026-08-28T00:00:00+00:00', '2026-08-28T00:00:00+00:00', '2026-08-28T00:00:00+00:00')")
        connection.execute("INSERT INTO application_artifacts (id, application_id, processing_run_id, artifact_type, storage_path, original_filename, mime_type, is_current, created_at) VALUES ('artifact-1', 'APPS-2', 'run-1', 'NORMALIZED_MARKDOWN', ?, 'candidate.md', 'text/markdown', 1, '2026-08-28T00:00:00+00:00')", (str(markdown),))
        for index in range(1, 3):
            connection.execute("INSERT INTO mapping_results (id, criteria_version_id, application_id, processing_run_id, source_artifact_id, applicant_label, criterion_item_id, citation, location, location_kind, evidence_status, mapping_status) VALUES (?, 'approved-v1', 'APPS-2', 'run-1', 'artifact-1', '후보081', ?, ?, 'p.1', 'EXACT', '충족', 'COMPLETED')", (f"mapping-{index}", f"item-{index}", "콜드 아웃바운드와 CRM 파이프라인을 관리했습니다."))
        connection.commit()
    return TestClient(app)


def _save_both_judgments(client: TestClient):
    for role, verdict in (("HR", "스크리닝 통과"), ("HM", "합격 - 필수 역량 충족")):
        response = client.post("/api/criteria/approved-v1/judgments", headers={"X-Demo-Role": role}, json={
            "application_id": "APPS-2", "reviewer_role": role, "document_verdict": verdict,
            "reviews": [
                {"criterion_item_id": "item-1", "status": "FULFILLED", "reason_text": f"{role} 근거 1", "citation": "콜드 아웃바운드와 CRM 파이프라인을 관리했습니다.", "source_location": "p.1"},
                {"criterion_item_id": "item-2", "status": "FULFILLED", "reason_text": f"{role} 근거 2", "citation": "콜드 아웃바운드와 CRM 파이프라인을 관리했습니다.", "source_location": "p.1"},
            ],
        })
        assert response.status_code == 200


def _create_card(client: TestClient) -> str:
    _save_both_judgments(client)
    response = client.post("/api/handoff/generate", params={"criteria_version_id": "approved-v1", "application_id": "APPS-2"}, headers={"X-Demo-Role": "LEAD"})
    assert response.status_code == 200
    return response.json()["card"]["id"]


def _model_response():
    return {"questions": [{
        "original_question": "신규 고객을 발굴한 경험을 구체적으로 말씀해 주세요.",
        "current_question": "연이 없는 신규 고객을 발굴해 첫 미팅으로 연결한 경험을 상황·행동·결과 순서로 말씀해 주세요.",
        "reason": "콜드 아웃바운드 실행 경험과 실제 기여를 확인하기 위해서입니다.",
        "criterion_item_ids": ["item-1"],
        "evidence_ids": ["mapping-1"],
        "question_type": "BEI",
    }]}


def _two_model_response():
    response = _model_response()
    response["questions"].append({
        "original_question": "CRM 성과를 관리한 경험을 말씀해 주세요.",
        "current_question": "CRM 파이프라인 지표를 바꾸고 결과를 확인한 경험을 구체적으로 말씀해 주세요.",
        "reason": "성과 관리 방식과 실제 결과를 확인하기 위해서입니다.",
        "criterion_item_ids": ["item-2"],
        "evidence_ids": ["mapping-2"],
        "question_type": "BEI",
    })
    return response


def test_question_generation_uses_related_question_bank_and_stores_candidates(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    card_id = _create_card(client)
    captured: dict[str, str] = {}

    def fake_model(prompt: str):
        captured["prompt"] = prompt
        return _model_response()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(questions, "request_model", fake_model)
    response = client.post(f"/api/questions/{card_id}/generate", headers={"X-Demo-Role": "LEAD"})

    assert response.status_code == 200
    assert "실제 사용 질문" in captured["prompt"]
    assert "고객 발굴" in captured["prompt"]
    assert "## 고객발굴.md" in captured["prompt"]
    assert "## 가격협상.md" not in captured["prompt"]
    candidate = response.json()["candidates"][0]
    assert candidate["status"] == "CANDIDATE"
    assert candidate["criterion_item_ids"] == ["item-1"]
    assert client.get(f"/api/questions/{card_id}").json()["candidates"][0]["id"] == candidate["id"]


def test_question_generation_does_not_store_partial_candidates_when_model_fails(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    card_id = _create_card(client)
    monkeypatch.setattr(questions, "request_model", lambda _prompt: (_ for _ in ()).throw(questions.QuestionGenerationError("모델 중단")))

    response = client.post(f"/api/questions/{card_id}/generate", headers={"X-Demo-Role": "LEAD"})

    assert response.status_code == 503
    assert client.get(f"/api/questions/{card_id}").json()["candidates"] == []


def test_question_generation_skips_model_when_no_related_bank_exists(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    card_id = _create_card(client)
    monkeypatch.setattr(questions, "select_question_bank", lambda _payload: [])
    monkeypatch.setattr(questions, "request_model", lambda _prompt: pytest.fail("관련 question-bank가 없으면 모델을 호출하지 않아야 합니다"))

    response = client.post(f"/api/questions/{card_id}/generate", headers={"X-Demo-Role": "LEAD"})

    assert response.status_code == 200
    assert response.json()["candidates"] == []


def test_question_generation_rejects_unsafe_candidate_without_mutating_card(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    card_id = _create_card(client)
    unsafe = _model_response()
    unsafe["questions"][0]["current_question"] = "결혼 여부와 신규 고객 경험을 말씀해 주세요."
    monkeypatch.setattr(questions, "request_model", lambda _prompt: unsafe)

    response = client.post(f"/api/questions/{card_id}/generate", headers={"X-Demo-Role": "LEAD"})

    assert response.status_code == 422
    assert client.get(f"/api/questions/{card_id}").json()["candidates"] == []


@pytest.mark.parametrize("status", ["PROCESSING", "FAILED"])
def test_question_generation_requires_ready_handoff_card(client: TestClient, status: str):
    card_id = _create_card(client)
    with db.connect() as connection:
        connection.execute("UPDATE handoff_cards SET status = ?, failure_reason = ? WHERE id = ?", (status, "테스트 실패" if status == "FAILED" else None, card_id))
        connection.commit()

    response = client.post(f"/api/questions/{card_id}/generate", headers={"X-Demo-Role": "LEAD"})

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "QUESTION_GATE"


def test_question_candidates_support_edit_soft_delete_and_lead_selection(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    card_id = _create_card(client)
    monkeypatch.setattr(questions, "request_model", lambda _prompt: _model_response())
    candidate = client.post(f"/api/questions/{card_id}/generate", headers={"X-Demo-Role": "LEAD"}).json()["candidates"][0]

    edit = client.patch(f"/api/questions/{card_id}/{candidate['id']}", headers={"X-Demo-Role": "HR"}, json={
        "current_question": "연이 없는 신규 고객을 발굴해 첫 미팅으로 연결한 경험과 본인의 행동을 말씀해 주세요.",
        "edit_reason": "행동 확인을 더 분명하게 수정",
    })
    assert edit.status_code == 200
    assert edit.json()["edit_history"][0]["reason"] == "행동 확인을 더 분명하게 수정"

    selected = client.post(f"/api/questions/{card_id}/{candidate['id']}/select", headers={"X-Demo-Role": "LEAD"}, json={"selected": True})
    assert selected.status_code == 200
    assert selected.json()["status"] == "SELECTED"
    assert client.get(f"/api/questions/{card_id}?selected_only=true").json()["selected_question_ids"] == [candidate["id"]]

    deleted = client.delete(f"/api/questions/{card_id}/{candidate['id']}", headers={"X-Demo-Role": "HM"})
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "DELETED"
    assert client.get(f"/api/questions/{card_id}").json()["candidates"] == []


def test_selected_only_returns_only_selected_candidate_and_roles_are_restricted(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    card_id = _create_card(client)
    monkeypatch.setattr(questions, "request_model", lambda _prompt: _two_model_response())
    candidates = client.post(f"/api/questions/{card_id}/generate", headers={"X-Demo-Role": "LEAD"}).json()["candidates"]

    selected = client.post(f"/api/questions/{card_id}/{candidates[0]['id']}/select", headers={"X-Demo-Role": "LEAD"}, json={"selected": True})
    assert selected.status_code == 200
    filtered = client.get(f"/api/questions/{card_id}?selected_only=true").json()
    assert [candidate["id"] for candidate in filtered["candidates"]] == [candidates[0]["id"]]
    assert client.patch(f"/api/questions/{card_id}/{candidates[0]['id']}", headers={"X-Demo-Role": "LEAD"}, json={"current_question": "질문을 수정해 주세요.", "edit_reason": "수정"}).status_code == 403
    assert client.post(f"/api/questions/{card_id}/{candidates[1]['id']}/select", headers={"X-Demo-Role": "HR"}, json={"selected": True}).status_code == 403
    assert client.delete(f"/api/questions/{card_id}/{candidates[1]['id']}", headers={"X-Demo-Role": "LEAD"}).status_code == 403


def test_question_endpoints_enforce_roles_and_ready_gate(client: TestClient):
    response = client.post("/api/questions/missing-card/generate", headers={"X-Demo-Role": "HR"})
    assert response.status_code == 403

    response = client.get("/api/questions/missing-card", headers={"X-Demo-Role": "LEAD"})
    assert response.status_code == 404


def test_model_request_uses_fixed_model_and_server_credentials(monkeypatch: pytest.MonkeyPatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"questions": []}'

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("OPENAI_API_KEY", "server-secret")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")
    monkeypatch.setattr(url_request, "urlopen", fake_urlopen)

    questions.request_model("테스트 프롬프트")

    assert captured["request"].full_url == "https://example.test/v1/chat/completions"
    assert captured["request"].get_header("Authorization") == "Bearer server-secret"
    body = json.loads(captured["request"].data)
    assert body["model"] == "gpt-5.6-luna"
    assert "temperature" not in body
    assert body["response_format"] == {"type": "json_object"}


def test_model_response_parser_accepts_chat_completion_envelope_and_rejects_invalid_shapes():
    assert questions._response_content({"choices": [{"message": {"content": '{"questions": []}'}}]}) == []
    with pytest.raises(questions.QuestionGenerationError):
        questions._response_content({"choices": [None]})
