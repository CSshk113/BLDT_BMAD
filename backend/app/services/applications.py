"""PDF application intake and processing lifecycle for the MVP."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import uuid

from backend.app.db import connect, initialize_schema
from backend.app.models.applications import (
    ApplicationArtifact,
    ApplicationDetail,
    ApplicationDocument,
    ApplicationSource,
    ApplicationSummary,
    ApplicationsList,
    ApplicationUploadInput,
    ArtifactType,
    LedgerMetadata,
    ProcessingRun,
    ProcessingRunEvent,
    ProcessingStatus,
    ledger_metadata_from_json,
)
from backend.app.services.criteria import ensure_seed_data, get_version
from backend.app.services.llamaparse import DocumentParser, LlamaParseAdapter, ParserError, normalize_markdown


PROJECT_ROOT = Path(__file__).resolve().parents[3]
HR_DATA_ROOT = Path(os.getenv("HR_DATA_ROOT", str(PROJECT_ROOT / "HR_data")))
UPLOAD_ROOT = Path(os.getenv("UPLOAD_ROOT", str(PROJECT_ROOT / "data" / "uploads")))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
DEMO_POSITION = "B2B 영업 매니저 5년 이상"


class InvalidUploadError(ValueError):
    """The request is not an admissible PDF upload."""


class DocumentNotReadyError(ValueError):
    """The requested application has no readable completed Markdown artifact."""


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _sample_catalog() -> dict[str, dict[str, str | bool]]:
    mapping_path = HR_DATA_ROOT / "03_resumes" / "표본매핑표.csv"
    if not mapping_path.is_file():
        return {}
    samples: dict[str, dict[str, str | bool]] = {}
    with mapping_path.open("r", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            token = row.get("후보토큰", "").strip()
            if not token:
                continue
            files = list((HR_DATA_ROOT / "03_resumes").glob(f"{token}_*_이력서.pdf"))
            samples[token] = {
                "name": row.get("가상이름", "").strip(),
                "stage": row.get("구간", "").strip(),
                "file_available": bool(files),
                "file_path": str(files[0]) if files else None,
            }
    return samples


def ensure_application_catalog() -> None:
    """Load the provided ledger/sample join into the local demo database."""
    ledger_path = HR_DATA_ROOT / "01_ledger" / "지원접수원장_178건.csv"
    if not ledger_path.is_file():
        return
    ensure_seed_data()
    samples = _sample_catalog()
    with ledger_path.open("r", encoding="utf-8-sig", newline="") as stream:
        ledger_rows = list(csv.DictReader(stream))
    with connect() as connection:
        initialize_schema(connection)
        for row in ledger_rows:
            application_id = row.get("ID", "").strip()
            token = row.get("이름", "").strip()
            if not application_id or not token:
                continue
            sample = samples.get(token)
            source_type = ApplicationSource.SAMPLE if sample and sample["file_available"] else ApplicationSource.LEDGER_ONLY
            metadata = LedgerMetadata(
                application_id=application_id,
                channel=row.get("채용 채널", "").strip() or None,
                position=row.get("포지션", "").strip() or None,
                applied_at=row.get("지원일", "").strip() or None,
                overall_status=row.get("현황", "").strip() or None,
                hr_screening=row.get("HR", "").strip() or None,
                rejection_reason=row.get("불합격 사유", "").strip() or None,
                document_review=row.get("서류심사", "").strip() or None,
                first_interview=row.get("1차면접", "").strip() or None,
                second_interview=row.get("2차면접", "").strip() or None,
                final_result=row.get("최종결과", "").strip() or None,
                sample_stage=str(sample["stage"]) if sample else None,
                sample_name=str(sample["name"]) if sample else None,
                sample_file_available=bool(sample and sample["file_available"]),
            )
            connection.execute(
                """
                INSERT INTO applications
                (id, candidate_token, position_name, criteria_version_id, source_type,
                 ledger_metadata_json, created_at, updated_at)
                VALUES (?, ?, ?, 'cv-b2b-sales-v4', ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  candidate_token = excluded.candidate_token,
                  position_name = excluded.position_name,
                  source_type = excluded.source_type,
                  ledger_metadata_json = excluded.ledger_metadata_json,
                  updated_at = excluded.updated_at
                """,
                (
                    application_id,
                    token,
                    row.get("포지션", "").strip() or DEMO_POSITION,
                    source_type,
                    json.dumps(metadata.model_dump(mode="json"), ensure_ascii=False),
                    now_iso(),
                    now_iso(),
                ),
            )
            if sample and sample["file_available"]:
                sample_path = Path(str(sample["file_path"]))
                existing_artifact = connection.execute(
                    "SELECT id FROM application_artifacts WHERE application_id = ? AND artifact_type = ? AND is_current = 1",
                    (application_id, ArtifactType.ORIGINAL_PDF),
                ).fetchone()
                if not existing_artifact:
                    _write_artifact(
                        connection,
                        application_id=application_id,
                        run_id=None,
                        artifact_type=ArtifactType.ORIGINAL_PDF,
                        path=sample_path,
                        original_filename=sample_path.name,
                        mime_type="application/pdf",
                        promote=True,
                    )
        connection.commit()


def _artifact_from_row(row) -> ApplicationArtifact:
    return ApplicationArtifact(
        id=row["id"],
        application_id=row["application_id"],
        processing_run_id=row["processing_run_id"],
        artifact_type=row["artifact_type"],
        original_filename=row["original_filename"],
        mime_type=row["mime_type"],
        is_current=bool(row["is_current"]),
        created_at=row["created_at"],
    )


def _run_from_row(connection, row) -> ProcessingRun:
    events = connection.execute(
        "SELECT status, step, occurred_at, detail FROM processing_run_events WHERE processing_run_id = ? ORDER BY id",
        (row["id"],),
    ).fetchall()
    return ProcessingRun(
        id=row["id"],
        application_id=row["application_id"],
        criteria_version_id=row["criteria_version_id"],
        status=row["status"],
        current_step=row["current_step"],
        parser_model=row["parser_model"],
        received_at=row["received_at"],
        parsing_started_at=row["parsing_started_at"],
        mapping_started_at=row["mapping_started_at"],
        completed_at=row["completed_at"],
        failed_at=row["failed_at"],
        failure_step=row["failure_step"],
        failure_reason=row["failure_reason"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        events=[ProcessingRunEvent(**dict(event)) for event in events],
    )


def _detail_from_row(connection, row) -> ApplicationDetail:
    runs = connection.execute(
        "SELECT * FROM processing_runs WHERE application_id = ? ORDER BY created_at DESC",
        (row["id"],),
    ).fetchall()
    artifacts = connection.execute(
        "SELECT id, application_id, processing_run_id, artifact_type, original_filename, mime_type, is_current, created_at "
        "FROM application_artifacts WHERE application_id = ? ORDER BY created_at DESC",
        (row["id"],),
    ).fetchall()
    summary = _summary_from_row(connection, row, runs=runs, artifacts=artifacts)
    return ApplicationDetail(
        **summary.model_dump(),
        artifacts=[_artifact_from_row(artifact) for artifact in artifacts],
        processing_runs=[_run_from_row(connection, run) for run in runs],
        can_review=summary.processing_status == ProcessingStatus.COMPLETED,
    )


def _summary_from_row(connection, row, *, runs=None, artifacts=None) -> ApplicationSummary:
    runs = runs if runs is not None else connection.execute(
        "SELECT * FROM processing_runs WHERE application_id = ? ORDER BY created_at DESC LIMIT 10",
        (row["id"],),
    ).fetchall()
    artifacts = artifacts if artifacts is not None else connection.execute(
        "SELECT artifact_type FROM application_artifacts WHERE application_id = ? AND is_current = 1 ORDER BY artifact_type",
        (row["id"],),
    ).fetchall()
    latest = runs[0] if runs else None
    source_type = ApplicationSource(row["source_type"])
    if source_type == ApplicationSource.LEDGER_ONLY:
        list_status = "원장 데이터만 있음"
    elif latest is None:
        list_status = "처리 대기"
    elif latest["status"] == ProcessingStatus.COMPLETED:
        list_status = "처리 완료"
    elif latest["status"] == ProcessingStatus.FAILED:
        list_status = "처리 실패"
    else:
        list_status = "처리 중"
    return ApplicationSummary(
        id=row["id"],
        candidate_token=row["candidate_token"],
        position_name=row["position_name"],
        criteria_version_id=row["criteria_version_id"],
        source_type=source_type,
        list_status=list_status,
        processing_status=latest["status"] if latest else None,
        current_step=latest["current_step"] if latest else None,
        failed_step=latest["failure_step"] if latest else None,
        failure_reason=latest["failure_reason"] if latest else None,
        last_successful_run_id=next((run["id"] for run in runs if run["status"] == ProcessingStatus.COMPLETED), None),
        last_successful_artifact_types=[artifact["artifact_type"] for artifact in artifacts],
        ledger_metadata=ledger_metadata_from_json(row["ledger_metadata_json"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def list_applications() -> ApplicationsList:
    ensure_application_catalog()
    with connect() as connection:
        rows = connection.execute("SELECT * FROM applications ORDER BY id DESC").fetchall()
        items = [_summary_from_row(connection, row) for row in rows]
        ledger_items = [item for item in items if item.source_type != ApplicationSource.UPLOAD]
        return ApplicationsList(
            items=items,
            total_ledger_count=len(ledger_items),
            sample_count=len({item.candidate_token for item in items if item.source_type == ApplicationSource.SAMPLE}),
            uploaded_count=sum(item.source_type == ApplicationSource.UPLOAD for item in items),
        )


def get_application(application_id: str) -> ApplicationDetail:
    ensure_application_catalog()
    with connect() as connection:
        row = connection.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
        if row is None:
            raise KeyError(application_id)
        return _detail_from_row(connection, row)


def get_document(application_id: str, run_id: str | None = None) -> ApplicationDocument:
    """Return only completed normalized Markdown, never its server path."""
    ensure_application_catalog()
    with connect() as connection:
        application = connection.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
        if application is None:
            raise KeyError(application_id)
        if run_id is not None:
            completed_run = connection.execute(
                "SELECT * FROM processing_runs WHERE id = ? AND application_id = ? AND status = 'COMPLETED'",
                (run_id, application_id),
            ).fetchone()
        else:
            completed_run = connection.execute(
                "SELECT * FROM processing_runs WHERE application_id = ? AND status = 'COMPLETED' ORDER BY completed_at DESC, created_at DESC LIMIT 1",
                (application_id,),
            ).fetchone()
        if completed_run is None:
            raise DocumentNotReadyError("완료된 Markdown 산출물이 없어 원문을 열 수 없습니다")
        artifact = connection.execute(
            "SELECT id, storage_path FROM application_artifacts WHERE application_id = ? AND processing_run_id = ? AND artifact_type = ? AND is_current = 1 ORDER BY created_at DESC LIMIT 1",
            (application_id, completed_run["id"], ArtifactType.NORMALIZED_MARKDOWN),
        ).fetchone()
        if artifact is None:
            raise DocumentNotReadyError("선택한 처리 실행의 정규화 Markdown이 없습니다")
        try:
            content = Path(artifact["storage_path"]).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise DocumentNotReadyError("원문 산출물을 읽을 수 없습니다") from error
        if not content.strip():
            raise DocumentNotReadyError("원문 산출물이 비어 있어 검토할 수 없습니다")
        return ApplicationDocument(
            application_id=application_id,
            criteria_version_id=completed_run["criteria_version_id"],
            processing_run_id=completed_run["id"],
            artifact_id=artifact["id"],
            source_type=ArtifactType.NORMALIZED_MARKDOWN,
            content=content,
        )


def _write_artifact(connection, *, application_id: str, run_id: str | None, artifact_type: ArtifactType, path: Path, original_filename: str, mime_type: str, promote: bool = False) -> None:
    if promote:
        connection.execute(
            "UPDATE application_artifacts SET is_current = 0 WHERE application_id = ? AND artifact_type = ?",
            (application_id, artifact_type),
        )
    connection.execute(
        """
        INSERT INTO application_artifacts
        (id, application_id, processing_run_id, artifact_type, storage_path, original_filename, mime_type, is_current, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (f"artifact-{uuid.uuid4().hex[:12]}", application_id, run_id, artifact_type, str(path), original_filename, mime_type, 1 if promote else 0, now_iso()),
    )


def _promote_run_artifacts(connection, application_id: str, run_id: str) -> None:
    for artifact_type in (ArtifactType.LLAMAPARSE_MARKDOWN, ArtifactType.NORMALIZED_MARKDOWN):
        connection.execute(
            "UPDATE application_artifacts SET is_current = 0 WHERE application_id = ? AND artifact_type = ?",
            (application_id, artifact_type),
        )
        connection.execute(
            "UPDATE application_artifacts SET is_current = 1 WHERE application_id = ? AND processing_run_id = ? AND artifact_type = ?",
            (application_id, run_id, artifact_type),
        )


def _record_event(connection, run_id: str, status: ProcessingStatus, step: str, detail: str | None = None) -> None:
    connection.execute(
        "INSERT INTO processing_run_events (processing_run_id, status, step, occurred_at, detail) VALUES (?, ?, ?, ?, ?)",
        (run_id, status, step, now_iso(), detail),
    )


def _set_run_status(connection, run_id: str, status: ProcessingStatus, *, step: str, detail: str | None = None, failure_reason: str | None = None) -> None:
    timestamp = now_iso()
    timestamp_column = {
        ProcessingStatus.PARSING: "parsing_started_at",
        ProcessingStatus.MAPPING: "mapping_started_at",
        ProcessingStatus.COMPLETED: "completed_at",
        ProcessingStatus.FAILED: "failed_at",
    }.get(status)
    assignments = ["status = ?", "current_step = ?", "updated_at = ?"]
    values: list[str | None] = [status, step, timestamp]
    if timestamp_column:
        assignments.append(f"{timestamp_column} = ?")
        values.append(timestamp)
    if status == ProcessingStatus.FAILED:
        assignments.extend(["failure_step = ?", "failure_reason = ?"])
        values.extend([step, failure_reason or detail or "처리 실패"])
    values.append(run_id)
    connection.execute(f"UPDATE processing_runs SET {', '.join(assignments)} WHERE id = ?", values)
    _record_event(connection, run_id, status, step, detail or failure_reason)


def process_application(application_id: str, run_id: str, parser: DocumentParser | None = None) -> ApplicationDetail:
    parser = parser or LlamaParseAdapter()
    failure_step = "PARSING"
    with connect() as connection:
        application = connection.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
        original = connection.execute(
            "SELECT * FROM application_artifacts WHERE application_id = ? AND artifact_type = ? AND is_current = 1 ORDER BY created_at DESC LIMIT 1",
            (application_id, ArtifactType.ORIGINAL_PDF),
        ).fetchone()
        if application is None or original is None:
            raise KeyError(application_id)
        try:
            _set_run_status(connection, run_id, ProcessingStatus.PARSING, step="PARSING")
            parsed = parser.parse(Path(original["storage_path"]))
            if not parsed.markdown.strip():
                raise ParserError("LlamaParse가 빈 Markdown을 반환했습니다")
            connection.execute("UPDATE processing_runs SET parser_model = ? WHERE id = ?", (parsed.parser_model, run_id))
            run_dir = UPLOAD_ROOT / application_id / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            original_stem = Path(original["original_filename"]).stem
            markdown_path = run_dir / f"{original_stem}.llamaparse.md"
            normalized_path = run_dir / f"{original_stem}.normalized.md"
            markdown_path.write_text(parsed.markdown, encoding="utf-8")
            _write_artifact(connection, application_id=application_id, run_id=run_id, artifact_type=ArtifactType.LLAMAPARSE_MARKDOWN, path=markdown_path, original_filename=f"{original['original_filename']}.llamaparse.md", mime_type="text/markdown")
            failure_step = "MAPPING"
            _set_run_status(connection, run_id, ProcessingStatus.MAPPING, step="MAPPING")
            normalized_markdown = normalize_markdown(parsed.markdown)
            normalized_path.write_text(normalized_markdown, encoding="utf-8")
            _write_artifact(connection, application_id=application_id, run_id=run_id, artifact_type=ArtifactType.NORMALIZED_MARKDOWN, path=normalized_path, original_filename=f"{original['original_filename']}.normalized.md", mime_type="text/markdown")
            normalized_artifact = connection.execute(
                "SELECT id FROM application_artifacts WHERE application_id = ? AND processing_run_id = ? AND artifact_type = 'NORMALIZED_MARKDOWN' ORDER BY created_at DESC LIMIT 1",
                (application_id, run_id),
            ).fetchone()
            if normalized_artifact is None:
                raise ValueError("정규화 Markdown 산출물 등록에 실패했습니다")
            from backend.app.services import mapping

            mapping.create_mappings_for_run(
                connection,
                application=application,
                version=get_version(application["criteria_version_id"]),
                run_id=run_id,
                artifact_id=normalized_artifact["id"],
                markdown=normalized_markdown,
            )
            _set_run_status(connection, run_id, ProcessingStatus.COMPLETED, step="COMPLETED")
            _promote_run_artifacts(connection, application_id, run_id)
        except Exception as error:
            _set_run_status(connection, run_id, ProcessingStatus.FAILED, step=failure_step, detail=str(error), failure_reason=str(error))
        connection.execute("UPDATE applications SET updated_at = ? WHERE id = ?", (now_iso(), application_id))
        connection.commit()
    return get_application(application_id)


def upload_pdf(*, filename: str, content_type: str | None, content: bytes, candidate_token: str, position_name: str, criteria_version_id: str, parser: DocumentParser | None = None) -> ApplicationDetail:
    normalized_name = Path(filename or "").name
    if not normalized_name.lower().endswith(".pdf") or not content.startswith(b"%PDF"):
        raise InvalidUploadError("PDF 파일만 업로드할 수 있습니다")
    if len(content) > MAX_UPLOAD_BYTES:
        raise InvalidUploadError(f"PDF 파일은 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB 이하만 업로드할 수 있습니다")
    validated = ApplicationUploadInput(candidate_token=candidate_token, position_name=position_name, criteria_version_id=criteria_version_id)
    try:
        get_version(validated.criteria_version_id)
    except KeyError as error:
        raise InvalidUploadError("기준 버전을 찾을 수 없습니다") from error
    application_id = f"UPLOAD-{uuid.uuid4().hex[:10]}"
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    timestamp = now_iso()
    target_dir = UPLOAD_ROOT / application_id / run_id
    target_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = target_dir / normalized_name
    pdf_path.write_bytes(content)
    with connect() as connection:
        initialize_schema(connection)
        connection.execute(
            "INSERT INTO applications (id, candidate_token, position_name, criteria_version_id, source_type, ledger_metadata_json, created_at, updated_at) VALUES (?, ?, ?, ?, 'UPLOAD', '{}', ?, ?)",
            (application_id, validated.candidate_token, validated.position_name, validated.criteria_version_id, timestamp, timestamp),
        )
        connection.execute(
            "INSERT INTO processing_runs (id, application_id, criteria_version_id, status, current_step, parser_model, received_at, created_at, updated_at) VALUES (?, ?, ?, 'RECEIVED', 'RECEIVED', 'llamaparse', ?, ?, ?)",
            (run_id, application_id, validated.criteria_version_id, timestamp, timestamp, timestamp),
        )
        _record_event(connection, run_id, ProcessingStatus.RECEIVED, "RECEIVED")
        _write_artifact(connection, application_id=application_id, run_id=run_id, artifact_type=ArtifactType.ORIGINAL_PDF, path=pdf_path, original_filename=normalized_name, mime_type="application/pdf", promote=True)
        connection.commit()
    return process_application(application_id, run_id, parser)


def reprocess_application(application_id: str, parser: DocumentParser | None = None) -> ApplicationDetail:
    """Create a new run without replacing the last successful artifacts."""
    with connect() as connection:
        application = connection.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
        original = connection.execute(
            "SELECT id FROM application_artifacts WHERE application_id = ? AND artifact_type = ? AND is_current = 1 LIMIT 1",
            (application_id, ArtifactType.ORIGINAL_PDF),
        ).fetchone()
        if application is None or original is None:
            raise KeyError(application_id)
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        timestamp = now_iso()
        connection.execute(
            "INSERT INTO processing_runs (id, application_id, criteria_version_id, status, current_step, parser_model, received_at, created_at, updated_at) VALUES (?, ?, ?, 'RECEIVED', 'RECEIVED', 'llamaparse', ?, ?, ?)",
            (run_id, application_id, application["criteria_version_id"], timestamp, timestamp, timestamp),
        )
        _record_event(connection, run_id, ProcessingStatus.RECEIVED, "RECEIVED", "재처리 요청")
        connection.execute("UPDATE applications SET updated_at = ? WHERE id = ?", (timestamp, application_id))
        connection.commit()
    return process_application(application_id, run_id, parser)
