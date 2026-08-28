from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import db
from backend.app.main import app
from backend.app.services import applications
from backend.app.services.llamaparse import ParsedDocument, ParserError


class FakeParser:
    def __init__(self, markdown: str = "# 후보\n\nB2B 영업 경험이 있습니다."):
        self.markdown = markdown

    def parse(self, file_path: Path) -> ParsedDocument:
        assert file_path.exists()
        return ParsedDocument(self.markdown, parser_model="fake-llamaparse")


class FailingParser:
    def parse(self, file_path: Path) -> ParsedDocument:
        raise ParserError("테스트 파서 실패")


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "test.db")
    monkeypatch.setattr(applications, "UPLOAD_ROOT", tmp_path / "uploads")
    return TestClient(app)


def upload(client: TestClient, *, filename="candidate.pdf", content=b"%PDF-1.7 demo", parser=None):
    if parser is not None:
        original = applications.upload_pdf
        applications.upload_pdf = lambda **kwargs: original(**kwargs, parser=parser)
    try:
        return client.post(
            "/api/applications",
            files={"file": (filename, content, "application/pdf")},
            data={
                "candidate_token": "후보-upload-001",
                "position_name": "B2B 영업 매니저 5년 이상",
                "criteria_version_id": "cv-b2b-sales-v4",
            },
        )
    finally:
        if parser is not None:
            applications.upload_pdf = original


def test_catalog_distinguishes_ledger_and_resume_samples(client: TestClient):
    response = client.get("/api/applications")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_ledger_count"] == 178
    assert payload["sample_count"] == 20
    assert any(item["source_type"] == "LEDGER_ONLY" and item["list_status"] == "원장 데이터만 있음" for item in payload["items"])
    assert any(item["source_type"] == "SAMPLE" for item in payload["items"])
    sample = next(item for item in payload["items"] if item["id"] == "APPS-28")
    assert sample["candidate_token"] == "후보068"
    assert sample["ledger_metadata"]["sample_name"] == "한서준"
    assert sample["ledger_metadata"]["channel"] == "그룹바이"
    assert sample["ledger_metadata"]["position"] == "B2B 영업 매니저 (5년 이상)"
    assert sample["ledger_metadata"]["overall_status"] == "채용"


def test_non_pdf_is_rejected_before_creating_an_application(client: TestClient):
    response = upload(client, filename="candidate.docx", content=b"not a pdf")

    assert response.status_code == 415
    assert client.get("/api/applications").json()["uploaded_count"] == 0


def test_pdf_upload_stores_original_and_markdown_artifacts(client: TestClient):
    response = upload(client, parser=FakeParser())

    assert response.status_code == 201
    payload = response.json()
    assert payload["processing_status"] == "COMPLETED"
    assert [event["status"] for event in payload["processing_runs"][0]["events"]] == ["RECEIVED", "PARSING", "MAPPING", "COMPLETED"]
    assert {artifact["artifact_type"] for artifact in payload["artifacts"]} == {"ORIGINAL_PDF", "LLAMAPARSE_MARKDOWN", "NORMALIZED_MARKDOWN"}
    assert payload["processing_runs"][0]["parser_model"] == "fake-llamaparse"
    run_id = payload["processing_runs"][0]["id"]
    with db.connect() as connection:
        rows = connection.execute(
            "SELECT * FROM application_artifacts WHERE application_id = ? ORDER BY artifact_type",
            (payload["id"],),
        ).fetchall()
    assert {row["application_id"] for row in rows} == {payload["id"]}
    assert {row["processing_run_id"] for row in rows if row["artifact_type"] != "ORIGINAL_PDF"} == {run_id}
    stored = {row["artifact_type"]: Path(row["storage_path"]).read_text(encoding="utf-8") for row in rows}
    assert stored["LLAMAPARSE_MARKDOWN"] == "# 후보\n\nB2B 영업 경험이 있습니다."
    assert stored["NORMALIZED_MARKDOWN"] == stored["LLAMAPARSE_MARKDOWN"] + "\n"


def test_failed_reprocessing_preserves_last_successful_markdown(client: TestClient):
    first = upload(client, parser=FakeParser())
    application_id = first.json()["id"]
    previous = {artifact["artifact_type"] for artifact in first.json()["artifacts"]}
    with db.connect() as connection:
        previous_rows = connection.execute(
            "SELECT artifact_type, storage_path FROM application_artifacts WHERE application_id = ? AND is_current = 1",
            (application_id,),
        ).fetchall()
    previous_content = {
        row["artifact_type"]: Path(row["storage_path"]).read_text(encoding="utf-8")
        for row in previous_rows
        if row["artifact_type"] == "NORMALIZED_MARKDOWN"
    }

    original = applications.process_application
    try:
        applications.process_application = lambda application_id, run_id, parser=None: original(application_id, run_id, parser=FailingParser())
        response = client.post(f"/api/applications/{application_id}/process")
    finally:
        applications.process_application = original

    assert response.status_code == 200
    payload = response.json()
    assert payload["processing_status"] == "FAILED"
    assert payload["failure_reason"] == "테스트 파서 실패"
    assert payload["failed_step"] == "PARSING"
    assert previous.issubset({artifact["artifact_type"] for artifact in payload["artifacts"]})
    assert any(artifact["is_current"] and artifact["artifact_type"] == "NORMALIZED_MARKDOWN" for artifact in payload["artifacts"])
    with db.connect() as connection:
        current = connection.execute(
            "SELECT storage_path FROM application_artifacts WHERE application_id = ? AND artifact_type = 'NORMALIZED_MARKDOWN' AND is_current = 1",
            (application_id,),
        ).fetchone()
    assert Path(current["storage_path"]).read_text(encoding="utf-8") == previous_content["NORMALIZED_MARKDOWN"]


def test_existing_sample_original_pdf_starts_a_new_run_without_creating_an_upload(client: TestClient):
    before = client.get("/api/applications/APPS-179")

    assert before.status_code == 200
    initial = before.json()
    assert initial["source_type"] == "SAMPLE"
    assert initial["processing_status"] is None
    assert any(artifact["artifact_type"] == "ORIGINAL_PDF" and artifact["is_current"] for artifact in initial["artifacts"])

    original = applications.process_application
    try:
        applications.process_application = lambda application_id, run_id, parser=None: original(application_id, run_id, parser=FakeParser())
        response = client.post("/api/applications/APPS-179/process")
    finally:
        applications.process_application = original

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "APPS-179"
    assert payload["source_type"] == "SAMPLE"
    assert payload["processing_status"] == "COMPLETED"
    run = payload["processing_runs"][0]
    assert run["application_id"] == "APPS-179"
    assert [event["status"] for event in run["events"]] == ["RECEIVED", "PARSING", "MAPPING", "COMPLETED"]
    assert {artifact["processing_run_id"] for artifact in payload["artifacts"] if artifact["artifact_type"] != "ORIGINAL_PDF"} == {run["id"]}
    assert {artifact["processing_run_id"] for artifact in payload["artifacts"] if artifact["artifact_type"] == "ORIGINAL_PDF"} == {None}
    assert not any(application["id"].startswith("UPLOAD-") for application in client.get("/api/applications").json()["items"])


def test_mapping_failure_records_mapping_step(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    first = upload(client, parser=FakeParser())
    monkeypatch.setattr(applications, "normalize_markdown", lambda _: (_ for _ in ()).throw(ValueError("정규화 실패")))

    result = applications.reprocess_application(first.json()["id"], parser=FakeParser())

    assert result.processing_status == "FAILED"
    assert result.failed_step == "MAPPING"
    assert result.failure_reason == "정규화 실패"


def test_document_endpoint_returns_markdown_for_the_requested_completed_run(client: TestClient):
    response = upload(client, parser=FakeParser("# 후보\n\n정확한 원문 문장입니다."))
    application_id = response.json()["id"]
    run_id = response.json()["processing_runs"][0]["id"]

    document = client.get(f"/api/applications/{application_id}/document", params={"run_id": run_id})

    assert document.status_code == 200
    payload = document.json()
    with db.connect() as connection:
        artifact = connection.execute(
            "SELECT id FROM application_artifacts WHERE application_id = ? AND processing_run_id = ? AND artifact_type = 'NORMALIZED_MARKDOWN' AND is_current = 1",
            (application_id, run_id),
        ).fetchone()
    assert payload == {
        "application_id": application_id,
        "criteria_version_id": "cv-b2b-sales-v4",
        "processing_run_id": run_id,
        "artifact_id": artifact["id"],
        "source_type": "NORMALIZED_MARKDOWN",
        "content": "# 후보\n\n정확한 원문 문장입니다.\n",
    }


def test_document_endpoint_blocks_incomplete_processing(client: TestClient):
    response = upload(client, parser=FailingParser())

    document = client.get(f"/api/applications/{response.json()['id']}/document")

    assert document.status_code == 409
