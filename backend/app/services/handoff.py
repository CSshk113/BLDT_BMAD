"""Official handoff card composition and idempotent persistence."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
import uuid

from backend.app.db import connect, initialize_schema
from backend.app.models.handoff import HandoffCard, HandoffGenerationResponse, HandoffPrerequisiteError, HandoffStateError, HandoffStatus
from backend.app.services import criteria


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _card_from_row(row) -> HandoffCard:
    try:
        payload = json.loads(row["payload_json"] or "{}")
    except (json.JSONDecodeError, TypeError) as error:
        raise HandoffStateError("핸드오프 카드 payload가 손상되었습니다") from error
    return HandoffCard(
        id=row["id"], application_id=row["application_id"], criteria_version_id=row["criteria_version_id"],
        status=row["status"], payload=payload, created_by=row["created_by"],
        failure_reason=row["failure_reason"], created_at=row["created_at"], updated_at=row["updated_at"],
    )


def get_card(card_id: str) -> HandoffCard:
    with connect() as connection:
        initialize_schema(connection)
        row = connection.execute("SELECT * FROM handoff_cards WHERE id = ?", (card_id,)).fetchone()
    if row is None:
        raise KeyError(card_id)
    return _card_from_row(row)


def _current_mappings(connection, application_id: str, version_id: str):
    rows = connection.execute(
        """
        SELECT m.*, i.criterion_text, i.requirement_type,
               p.completed_at AS run_completed_at
        FROM mapping_results AS m
        JOIN criteria_items AS i ON i.id = m.criterion_item_id
        LEFT JOIN processing_runs AS p ON p.id = m.processing_run_id
        WHERE m.application_id = ? AND m.criteria_version_id = ? AND m.mapping_status = 'COMPLETED'
          AND p.status = 'COMPLETED'
        ORDER BY CASE WHEN p.completed_at IS NULL THEN 1 ELSE 0 END,
                 p.completed_at DESC, m.id DESC
        """,
        (application_id, version_id),
    ).fetchall()
    selected = {}
    for row in rows:
        selected.setdefault(row["criterion_item_id"], row)
    return selected


def _missing_conditions(connection, version, application_id: str):
    missing: list[str] = []
    application = connection.execute("SELECT criteria_version_id FROM applications WHERE id = ?", (application_id,)).fetchone()
    if application is None or application["criteria_version_id"] != version.id:
        missing.append("지원서 존재 및 기준 버전 일치")
    if version.status != criteria.CriteriaVersionStatus.APPROVED:
        missing.append("기준 버전 승인")
    mappings = _current_mappings(connection, application_id, version.id)
    required_items = {item.id for item in version.items}
    if set(mappings) != required_items:
        missing.append("모든 기준 항목의 처리 완료 매핑")
    artifact = connection.execute(
        """
        SELECT id, processing_run_id, storage_path
        FROM application_artifacts
        WHERE application_id = ? AND artifact_type = 'NORMALIZED_MARKDOWN' AND is_current = 1
        ORDER BY created_at DESC LIMIT 1
        """,
        (application_id,),
    ).fetchone()
    mapping_runs = {row["processing_run_id"] for row in mappings.values()}
    mapping_artifacts = {row["source_artifact_id"] for row in mappings.values()}
    if artifact is None or not Path(artifact["storage_path"]).is_file():
        missing.append("확인 가능한 원문 산출물")
    elif len(mapping_runs) != 1 or artifact["processing_run_id"] not in mapping_runs or mapping_artifacts != {artifact["id"]}:
        missing.append("매핑과 동일한 처리 실행·원문 산출물")
    for role in ("HR", "HM"):
        role_items = connection.execute(
            """
            SELECT DISTINCT criterion_item_id FROM review_logs
            WHERE application_id = ? AND criteria_version_id = ?
              AND reviewer_role = ? AND review_scope = 'OFFICIAL'
            """,
            (application_id, version.id, role),
        ).fetchall()
        if {row["criterion_item_id"] for row in role_items} != required_items:
            missing.append(f"{role} 공식 판단 로그 전체")
        else:
            trace_rows = connection.execute(
                """
                SELECT criterion_item_id, mapping_result_id, processing_run_id, source_artifact_id
                FROM review_logs
                WHERE application_id = ? AND criteria_version_id = ?
                  AND reviewer_role = ? AND review_scope = 'OFFICIAL'
                """,
                (application_id, version.id, role),
            ).fetchall()
            if any(
                row["mapping_result_id"] != mappings[row["criterion_item_id"]]["id"]
                or row["processing_run_id"] != mappings[row["criterion_item_id"]]["processing_run_id"]
                or row["source_artifact_id"] != mappings[row["criterion_item_id"]]["source_artifact_id"]
                for row in trace_rows
            ):
                missing.append(f"{role} 판단 로그의 근거 추적 연결")
    return missing, mappings, artifact


def _read_document(path: str) -> str:
    try:
        content = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValueError("원문 산출물을 읽을 수 없습니다") from error
    if not content.strip():
        raise ValueError("원문 산출물이 비어 있습니다")
    return content


def _build_payload(connection, version, application_id: str, mappings, artifact):
    matrix = criteria.get_judgment_matrix(version.id, application_id)
    application = connection.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
    evidence = []
    insufficient = []
    for item in version.items:
        row = mappings[item.id]
        item_payload = {
            "id": row["id"], "application_id": row["application_id"], "criteria_version_id": row["criteria_version_id"],
            "processing_run_id": row["processing_run_id"], "source_artifact_id": row["source_artifact_id"],
            "criterion_item_id": row["criterion_item_id"], "criterion_text": row["criterion_text"],
            "requirement_type": row["requirement_type"], "citation": row["citation"], "location": row["location"],
            "location_kind": row["location_kind"], "evidence_status": row["evidence_status"],
        }
        evidence.append(item_payload)
        if not row["citation"] or row["evidence_status"] == "확인 불가" or row["location_kind"] == "NONE" or not row["location"]:
            insufficient.append({"criterion_item_id": item.id, "criterion_text": item.criterion_text, "question_needed": True})
    return {
        "application": {
            "id": application_id,
            "candidate_token": application["candidate_token"] if application else application_id,
            "position_name": application["position_name"] if application else version.position_name,
        },
        "source_document": {
            "artifact_id": artifact["id"], "processing_run_id": artifact["processing_run_id"],
            "content": _read_document(artifact["storage_path"]),
        },
        "criteria": {"version_id": version.id, "position_name": version.position_name, "items": [item.model_dump(mode="json") for item in version.items]},
        "evidence": evidence,
        "judgments": matrix.model_dump(mode="json"),
        "differences": [
            {"criterion_item_id": row.criterion_item_id, "fields": row.differences}
            for row in matrix.rows if row.differences
        ],
        "insufficient_evidence": insufficient,
        "interview_questions": [],
        "interview_results": [],
    }


def generate_card(criteria_version_id: str, application_id: str, created_by: str = "LEAD") -> HandoffGenerationResponse:
    version = criteria.get_version(criteria_version_id)
    with connect() as connection:
        initialize_schema(connection)
        existing_row = connection.execute(
            "SELECT * FROM handoff_cards WHERE application_id = ? AND criteria_version_id = ?",
            (application_id, criteria_version_id),
        ).fetchone()
        if existing_row:
            existing = _card_from_row(existing_row)
            if existing.status == HandoffStatus.READY:
                return HandoffGenerationResponse(card=existing, already_exists=True)
            if existing.status == HandoffStatus.PROCESSING:
                raise HandoffStateError("핸드오프 카드 생성이 처리 중입니다", existing)
            raise HandoffStateError("핸드오프 카드 생성이 실패했습니다. 실패 사유를 확인하세요", existing)
        missing, mappings, artifact = _missing_conditions(connection, version, application_id)
        if missing:
            raise HandoffPrerequisiteError(missing)
        timestamp = now_iso()
        card_id = f"handoff-{uuid.uuid4().hex[:12]}"
        try:
            connection.execute(
                """
                INSERT INTO handoff_cards
                (id, application_id, criteria_version_id, status, payload_json, created_by, created_at, updated_at)
                VALUES (?, ?, ?, 'PROCESSING', '{}', ?, ?, ?)
                """,
                (card_id, application_id, criteria_version_id, created_by, timestamp, timestamp),
            )
            connection.commit()
        except sqlite3.IntegrityError:
            existing_row = connection.execute(
                "SELECT * FROM handoff_cards WHERE application_id = ? AND criteria_version_id = ?",
                (application_id, criteria_version_id),
            ).fetchone()
            if existing_row is None:
                raise
            existing = _card_from_row(existing_row)
            if existing.status == HandoffStatus.READY:
                return HandoffGenerationResponse(card=existing, already_exists=True)
            raise HandoffStateError("핸드오프 카드 생성이 이미 처리 중이거나 실패했습니다", existing)
        try:
            payload = _build_payload(connection, version, application_id, mappings, artifact)
            connection.execute(
                "UPDATE handoff_cards SET status = 'READY', payload_json = ?, updated_at = ? WHERE id = ?",
                (json.dumps(payload, ensure_ascii=False), now_iso(), card_id),
            )
            connection.commit()
        except Exception as error:
            failure_reason = str(error) or "핸드오프 payload 생성 실패"
            connection.execute(
                "UPDATE handoff_cards SET status = 'FAILED', failure_reason = ?, updated_at = ? WHERE id = ?",
                (failure_reason, now_iso(), card_id),
            )
            connection.commit()
            failed_row = connection.execute("SELECT * FROM handoff_cards WHERE id = ?", (card_id,)).fetchone()
            raise HandoffStateError("핸드오프 카드 생성이 실패했습니다", _card_from_row(failed_row)) from error
        row = connection.execute("SELECT * FROM handoff_cards WHERE id = ?", (card_id,)).fetchone()
    return HandoffGenerationResponse(card=_card_from_row(row))
