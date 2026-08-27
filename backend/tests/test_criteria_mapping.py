from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import db
from backend.app.main import app
from backend.app.services import applications
from backend.app.services.llamaparse import ParsedDocument


class MappingParser:
    def parse(self, file_path: Path) -> ParsedDocument:
        assert file_path.exists()
        return ParsedDocument(
            "# 경력기술서\n\nB2B 영업 파이프라인을 운영했습니다.\n\nPage 2\n고객과의 협업 내용을 기록했습니다.",
            parser_model="mapping-test-parser",
        )


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "mapping.db")
    monkeypatch.setattr(applications, "UPLOAD_ROOT", tmp_path / "uploads")
    return TestClient(app)


def upload_completed_application(client: TestClient) -> str:
    response = client.post(
        "/api/applications",
        files={"file": ("resume.pdf", b"%PDF-1.7 demo", "application/pdf")},
        data={
            "candidate_token": "후보-mapping-001",
            "position_name": "B2B 영업 매니저 5년 이상",
            "criteria_version_id": "cv-b2b-sales-v4",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_mapping_links_each_criterion_to_verified_source_text(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(applications, "LlamaParseAdapter", lambda: MappingParser())
    application_id = upload_completed_application(client)

    response = client.post("/api/mappings", json={"application_id": application_id, "criteria_version_id": "cv-b2b-sales-v4"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_preview"] is True
    assert payload["criteria_status"] == "DRAFT"
    assert len(payload["mappings"]) == 3
    assert {mapping["processing_run_id"] for mapping in payload["mappings"]} == {payload["processing_run_id"]}
    assert any(mapping["citation"] and "B2B 영업 파이프라인" in mapping["citation"] for mapping in payload["mappings"])
    assert any(mapping["evidence_status"] == "확인 불가" and mapping["location_kind"] == "NONE" for mapping in payload["mappings"])
    assert all(mapping["mapping_status"] == "COMPLETED" for mapping in payload["mappings"])
    with db.connect() as connection:
        artifact = connection.execute(
            "SELECT storage_path FROM application_artifacts WHERE id = ?",
            (payload["source_artifact_id"],),
        ).fetchone()
    markdown = Path(artifact["storage_path"]).read_text(encoding="utf-8")
    assert all(not mapping["citation"] or mapping["citation"] in markdown for mapping in payload["mappings"])


def test_mapping_get_rejects_unknown_run(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(applications, "LlamaParseAdapter", lambda: MappingParser())
    application_id = upload_completed_application(client)
    client.post("/api/mappings", json={"application_id": application_id})

    response = client.get(f"/api/mappings/{application_id}?run_id=run-missing")

    assert response.status_code == 404
    assert "아직 생성된 기준별 매핑" in response.json()["detail"]


def test_mapping_rejects_application_without_completed_markdown(client: TestClient):
    response = client.post("/api/mappings", json={"application_id": "APPS-2", "criteria_version_id": "cv-b2b-sales-v4"})

    assert response.status_code == 409
    assert "처리 완료된 실행" in response.json()["detail"]
