"""Official handoff card composition and idempotent persistence."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
import uuid

from backend.app.db import connect, initialize_schema
from backend.app.models.handoff import (
    HandoffCard,
    HandoffGenerationResponse,
    HandoffPrerequisiteError,
    HandoffStateError,
    HandoffStatus,
    DecisionRecord,
    FinalDecisionInput,
    InterviewVerification,
    InterviewVerificationInput,
    QuestionCandidate,
    QuestionCandidateEditInput,
    QuestionCandidateListResponse,
    QuestionCandidateStatus,
)
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
        "final_decision": None,
        "audit_timeline": [
            {
                "event_type": "CRITERIA_APPROVED",
                "target_id": version.id,
                "actor": version.approved_by or "SYSTEM",
                "timestamp": (version.approved_at or version.updated_at).isoformat(),
                "source": "SYSTEM",
                "summary": "승인된 기준 버전 적용",
            },
            {
                "event_type": "HANDOFF_READY",
                "target_id": application_id,
                "actor": "SYSTEM",
                "timestamp": now_iso(),
                "source": "SYSTEM",
                "summary": "공식 핸드오프 카드 생성",
            },
        ],
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


def _question_candidates(payload: dict) -> list[QuestionCandidate]:
    values = payload.get("interview_questions", [])
    if not isinstance(values, list):
        raise HandoffStateError("핸드오프 카드의 질문 후보 payload가 손상되었습니다")
    try:
        return [QuestionCandidate.model_validate(value) for value in values]
    except ValueError as error:
        raise HandoffStateError("핸드오프 카드의 질문 후보 payload가 손상되었습니다") from error


def list_question_candidates(card_id: str, *, selected_only: bool = False) -> QuestionCandidateListResponse:
    card = get_card(card_id)
    if card.status != HandoffStatus.READY:
        raise HandoffStateError("READY 상태의 핸드오프 카드만 질문 후보를 조회할 수 있습니다", card)
    candidates = _question_candidates(card.payload)
    candidates = [candidate for candidate in candidates if candidate.status != QuestionCandidateStatus.DELETED]
    if selected_only:
        candidates = [candidate for candidate in candidates if candidate.status == QuestionCandidateStatus.SELECTED]
    return QuestionCandidateListResponse(
        card_id=card_id,
        candidates=candidates,
        selected_question_ids=[candidate.id for candidate in candidates if candidate.status == QuestionCandidateStatus.SELECTED],
    )


def generate_question_candidates(card_id: str, actor_role: str = "LEAD") -> QuestionCandidateListResponse:
    from backend.app.services import questions

    with connect() as connection:
        initialize_schema(connection)
        row = connection.execute("SELECT * FROM handoff_cards WHERE id = ?", (card_id,)).fetchone()
        if row is None:
            raise KeyError(card_id)
        card = _card_from_row(row)
        if card.status != HandoffStatus.READY:
            raise HandoffStateError("READY 상태의 핸드오프 카드만 질문을 생성할 수 있습니다", card)
        generated = questions.generate_candidates(card)
        payload = dict(card.payload)
        current = _question_candidates(payload)
        payload["interview_questions"] = [
            candidate.model_dump(mode="json") for candidate in [*current, *generated]
        ]
        _append_audit(payload, "QUESTION_CANDIDATES_GENERATED", card_id, actor_role, "인터뷰 질문 후보 생성 요청")
        result = connection.execute(
            "UPDATE handoff_cards SET payload_json = ?, updated_at = ? WHERE id = ? AND status = 'READY'",
            (json.dumps(payload, ensure_ascii=False), now_iso(), card_id),
        )
        if result.rowcount != 1:
            raise HandoffStateError("핸드오프 카드가 변경되어 질문 후보를 저장하지 못했습니다", card)
        connection.commit()
    return list_question_candidates(card_id)


def _mutate_question(card_id: str, question_id: str, mutate, actor_role: str) -> QuestionCandidate:
    if actor_role not in {"HR", "HM"}:
        raise PermissionError("질문 후보 수정 권한이 없습니다")
    with connect() as connection:
        initialize_schema(connection)
        row = connection.execute("SELECT * FROM handoff_cards WHERE id = ?", (card_id,)).fetchone()
        if row is None:
            raise KeyError(card_id)
        card = _card_from_row(row)
        if card.status != HandoffStatus.READY:
            raise HandoffStateError("READY 상태의 핸드오프 카드만 질문 후보를 수정할 수 있습니다", card)
        candidates = _question_candidates(card.payload)
        target = next((candidate for candidate in candidates if candidate.id == question_id), None)
        if target is None:
            raise KeyError(question_id)
        if target.status == QuestionCandidateStatus.DELETED:
            raise HandoffStateError("삭제된 질문 후보는 수정할 수 없습니다", card)
        if _decision_record(card.payload) is not None:
            raise HandoffStateError("최종 결정 이후 질문 후보를 수정할 수 없습니다", card)
        if any(result.question_id == question_id for result in _verification_results(card.payload)):
            raise HandoffStateError("면접 검증 결과가 있는 질문 후보는 수정할 수 없습니다", card)
        changed = mutate(target, candidates, card.payload)
        payload = dict(card.payload)
        payload["interview_questions"] = [candidate.model_dump(mode="json") for candidate in candidates]
        result = connection.execute(
            "UPDATE handoff_cards SET payload_json = ?, updated_at = ? WHERE id = ? AND status = 'READY'",
            (json.dumps(payload, ensure_ascii=False), now_iso(), card_id),
        )
        if result.rowcount != 1:
            raise HandoffStateError("핸드오프 카드가 변경되어 질문 후보를 저장하지 못했습니다", card)
        connection.commit()
    return changed


def update_question_candidate(card_id: str, question_id: str, payload: QuestionCandidateEditInput, actor_role: str) -> QuestionCandidate:
    from backend.app.services.questions import validate_candidate

    if not payload.edit_reason.strip():
        raise ValueError("변경 사유를 입력하세요")

    def mutate(target: QuestionCandidate, candidates: list[QuestionCandidate], card_payload: dict) -> QuestionCandidate:
        previous = target.current_question
        target.current_question = payload.current_question.strip()
        try:
            validate_candidate(target, card_payload, [candidate for candidate in candidates if candidate.id != target.id])
        except Exception:
            target.current_question = previous
            raise
        target.edit_history.append({
            "previous_question": previous,
            "new_question": target.current_question,
            "actor": actor_role,
            "timestamp": now_iso(),
            "reason": payload.edit_reason.strip(),
        })
        return target

    return _mutate_question(card_id, question_id, mutate, actor_role)


def delete_question_candidate(card_id: str, question_id: str, actor_role: str) -> QuestionCandidate:
    def mutate(target: QuestionCandidate, _candidates: list[QuestionCandidate], _card_payload: dict) -> QuestionCandidate:
        target.status = QuestionCandidateStatus.DELETED
        target.edit_history.append({
            "action": "DELETE",
            "actor": actor_role,
            "timestamp": now_iso(),
            "reason": "질문 후보 삭제",
        })
        return target

    return _mutate_question(card_id, question_id, mutate, actor_role)


def select_question_candidate(card_id: str, question_id: str, selected: bool, actor_role: str) -> QuestionCandidate:
    if actor_role != "LEAD":
        raise PermissionError("질문 후보 선택 권한이 없습니다")
    with connect() as connection:
        initialize_schema(connection)
        row = connection.execute("SELECT * FROM handoff_cards WHERE id = ?", (card_id,)).fetchone()
        if row is None:
            raise KeyError(card_id)
        card = _card_from_row(row)
        if card.status != HandoffStatus.READY:
            raise HandoffStateError("READY 상태의 핸드오프 카드만 질문 후보를 선택할 수 있습니다", card)
        if _decision_record(card.payload) is not None:
            raise HandoffStateError("최종 결정 이후 질문 선택 상태를 변경할 수 없습니다", card)
        candidates = _question_candidates(card.payload)
        target = next((candidate for candidate in candidates if candidate.id == question_id), None)
        if target is None:
            raise KeyError(question_id)
        if target.status == QuestionCandidateStatus.DELETED:
            raise HandoffStateError("삭제된 질문 후보는 선택할 수 없습니다", card)
        target.status = QuestionCandidateStatus.SELECTED if selected else QuestionCandidateStatus.CANDIDATE
        payload = dict(card.payload)
        payload["interview_questions"] = [candidate.model_dump(mode="json") for candidate in candidates]
        _append_audit(payload, "QUESTION_CANDIDATE_SELECTED" if selected else "QUESTION_CANDIDATE_UNSELECTED", question_id, actor_role, "인터뷰 질문 선택 상태 변경")
        result = connection.execute(
            "UPDATE handoff_cards SET payload_json = ?, updated_at = ? WHERE id = ? AND status = 'READY'",
            (json.dumps(payload, ensure_ascii=False), now_iso(), card_id),
        )
        if result.rowcount != 1:
            raise HandoffStateError("핸드오프 카드가 변경되어 질문 선택 상태를 저장하지 못했습니다", card)
        connection.commit()
    return target


def _require_interview_card(card: HandoffCard) -> None:
    if card.status != HandoffStatus.READY:
        raise HandoffStateError("READY 상태의 핸드오프 카드만 면접 결과를 기록할 수 있습니다", card)
    version = criteria.get_version(card.criteria_version_id)
    if version.status != criteria.CriteriaVersionStatus.APPROVED:
        raise HandoffStateError("승인된 기준 버전의 핸드오프만 면접 결과를 기록할 수 있습니다", card)


def _verification_results(payload: dict) -> list[InterviewVerification]:
    values = payload.get("interview_results", [])
    if not isinstance(values, list):
        raise HandoffStateError("핸드오프 카드의 면접 결과 payload가 손상되었습니다")
    try:
        results = [InterviewVerification.model_validate(value) for value in values]
    except ValueError as error:
        raise HandoffStateError("핸드오프 카드의 면접 결과 payload가 손상되었습니다") from error
    if len({result.question_id for result in results}) != len(results):
        raise HandoffStateError("핸드오프 카드에 중복된 면접 결과가 있습니다")
    return results


def _selected_questions(payload: dict) -> list[QuestionCandidate]:
    return [candidate for candidate in _question_candidates(payload) if candidate.status == QuestionCandidateStatus.SELECTED]


def _initial_hypothesis(payload: dict, question: QuestionCandidate) -> str:
    parts = [question.reason]
    insufficient_values = payload.get("insufficient_evidence", [])
    insufficient = [
        item["criterion_text"]
        for item in (insufficient_values if isinstance(insufficient_values, list) else [])
        if isinstance(item, dict) and item.get("criterion_item_id") in question.criterion_item_ids
    ]
    difference_values = payload.get("differences", [])
    differences = [
        item.get("criterion_item_id")
        for item in (difference_values if isinstance(difference_values, list) else [])
        if isinstance(item, dict) and item.get("criterion_item_id") in question.criterion_item_ids
    ]
    judgment_data = payload.get("judgments", {})
    judgment_rows = judgment_data.get("rows", []) if isinstance(judgment_data, dict) else []
    for row in judgment_rows if isinstance(judgment_rows, list) else []:
        if not isinstance(row, dict) or row.get("criterion_item_id") not in question.criterion_item_ids:
            continue
        for role, label in (("hr_review", "HR"), ("hm_review", "HM")):
            review = row.get(role)
            if isinstance(review, dict) and (review.get("status") or review.get("reason_text")):
                parts.append(f"{label}: {review.get('status', '미입력')} · {review.get('reason_text', '')}".strip(" ·"))
    if insufficient:
        parts.append(f"서류 근거 부족: {', '.join(insufficient)}")
    if differences:
        parts.append(f"검토자 이견 기준: {', '.join(differences)}")
    return " · ".join(part for part in parts if part)


def _audit_timeline(payload: dict) -> list[dict]:
    timeline = payload.get("audit_timeline", [])
    if not isinstance(timeline, list) or not all(isinstance(event, dict) for event in timeline):
        raise HandoffStateError("핸드오프 카드의 감사 타임라인 payload가 손상되었습니다")
    return timeline


def _append_audit(payload: dict, event_type: str, target_id: str, actor: str, summary: str) -> None:
    timeline = _audit_timeline(payload)
    timeline.extend([
        {
            "event_type": event_type,
            "target_id": target_id,
            "actor": actor,
            "timestamp": now_iso(),
            "source": "HUMAN",
            "summary": summary,
        }
    ])
    payload["audit_timeline"] = timeline


def save_interview_verification(card_id: str, payload: InterviewVerificationInput, actor_role: str) -> HandoffCard:
    if actor_role != "LEAD":
        raise PermissionError("면접 검증 결과 기록 권한이 없습니다")
    result_text = payload.interview_result.strip()
    if not result_text:
        raise ValueError("면접 검증 결과를 입력하세요")
    with connect() as connection:
        initialize_schema(connection)
        row = connection.execute("SELECT * FROM handoff_cards WHERE id = ?", (card_id,)).fetchone()
        if row is None:
            raise KeyError(card_id)
        original_updated_at = row["updated_at"]
        card = _card_from_row(row)
        _require_interview_card(card)
        if _decision_record(card.payload) is not None:
            raise HandoffStateError("최종 결정 이후 면접 검증 결과를 수정할 수 없습니다", card)
        selected = _selected_questions(card.payload)
        question = next((item for item in selected if item.id == payload.question_id), None)
        if question is None:
            raise HandoffStateError("선택된 질문만 면접 검증 결과를 기록할 수 있습니다", card)
        results = _verification_results(card.payload)
        current = next((item for item in results if item.question_id == payload.question_id), None)
        timestamp = now_iso()
        if current is None:
            current = InterviewVerification(
                id=f"verification-{uuid.uuid4().hex[:12]}",
                question_id=question.id,
                original_question=question.original_question,
                current_question=question.current_question,
                criterion_item_ids=question.criterion_item_ids,
                evidence_ids=question.evidence_ids,
                initial_hypothesis=_initial_hypothesis(card.payload, question),
                interview_result=result_text,
                recorded_by=actor_role,
                recorded_at=timestamp,
            )
            results.append(current)
            event_type = "INTERVIEW_VERIFICATION_RECORDED"
            summary = "면접 검증 결과 기록"
        else:
            if payload.edit_reason is None or not payload.edit_reason.strip():
                raise ValueError("검증 결과 변경 사유를 입력하세요")
            previous = current.interview_result
            current.interview_result = result_text
            current.recorded_by = actor_role
            current.recorded_at = datetime.fromisoformat(timestamp)
            current.edit_history.append({
                "previous_result": previous,
                "new_result": result_text,
                "actor": actor_role,
                "timestamp": timestamp,
                "reason": payload.edit_reason.strip(),
            })
            event_type = "INTERVIEW_VERIFICATION_UPDATED"
            summary = "면접 검증 결과 수정"
        next_payload = dict(card.payload)
        next_payload["interview_results"] = [item.model_dump(mode="json") for item in results]
        _append_audit(next_payload, event_type, payload.question_id, actor_role, summary)
        updated_at = now_iso()
        updated = connection.execute(
            "UPDATE handoff_cards SET payload_json = ?, updated_at = ? WHERE id = ? AND status = 'READY' AND updated_at = ?",
            (json.dumps(next_payload, ensure_ascii=False), updated_at, card_id, original_updated_at),
        )
        if updated.rowcount != 1:
            raise HandoffStateError("핸드오프 카드가 변경되어 면접 결과를 저장하지 못했습니다", card)
        connection.commit()
        saved = connection.execute("SELECT * FROM handoff_cards WHERE id = ?", (card_id,)).fetchone()
    return _card_from_row(saved)


def _decision_record(payload: dict) -> DecisionRecord | None:
    value = payload.get("final_decision")
    if value is None:
        return None
    try:
        return DecisionRecord.model_validate(value)
    except ValueError as error:
        raise HandoffStateError("핸드오프 카드의 최종 결정 payload가 손상되었습니다") from error


def save_final_decision(card_id: str, payload: FinalDecisionInput, actor_role: str) -> HandoffCard:
    if actor_role != "LEAD":
        raise PermissionError("최종 결정 기록 권한이 없습니다")
    reason = payload.reason.strip()
    if not reason:
        raise ValueError("최종 결정 사유를 입력하세요")
    with connect() as connection:
        initialize_schema(connection)
        row = connection.execute("SELECT * FROM handoff_cards WHERE id = ?", (card_id,)).fetchone()
        if row is None:
            raise KeyError(card_id)
        original_updated_at = row["updated_at"]
        card = _card_from_row(row)
        _require_interview_card(card)
        selected = _selected_questions(card.payload)
        if not selected:
            raise HandoffStateError("인터뷰에 선택된 질문이 없습니다", card)
        results = _verification_results(card.payload)
        result_ids = {item.question_id for item in results}
        missing = [item.id for item in selected if item.id not in result_ids]
        if missing:
            raise HandoffStateError(f"선택 질문의 면접 검증 결과가 누락되었습니다: {', '.join(missing)}", card)
        selected_by_id = {item.id: item for item in selected}
        for result in results:
            question = selected_by_id.get(result.question_id)
            if question is None or result.current_question != question.current_question or result.criterion_item_ids != question.criterion_item_ids or result.evidence_ids != question.evidence_ids:
                raise HandoffStateError("면접 검증 결과의 질문·기준·근거 연결이 최신 선택 질문과 다릅니다", card)
        current = _decision_record(card.payload)
        timestamp = now_iso()
        if current is None:
            current = DecisionRecord(
                id=f"decision-{uuid.uuid4().hex[:12]}",
                decision=payload.decision,
                reason=reason,
                actor=actor_role,
                decided_at=timestamp,
                criteria_version_id=card.criteria_version_id,
            )
            event_type = "FINAL_DECISION_RECORDED"
            summary = f"사람의 최종 결정 기록: {payload.decision.value}"
        else:
            if payload.edit_reason is None or not payload.edit_reason.strip():
                raise ValueError("최종 결정 변경 사유를 입력하세요")
            previous = {"decision": current.decision.value, "reason": current.reason}
            current.edit_history.append({
                "previous_value": previous,
                "new_value": {"decision": payload.decision.value, "reason": reason},
                "actor": actor_role,
                "timestamp": timestamp,
                "reason": payload.edit_reason.strip(),
            })
            current.decision = payload.decision
            current.reason = reason
            current.actor = actor_role
            current.decided_at = datetime.fromisoformat(timestamp)
            event_type = "FINAL_DECISION_UPDATED"
            summary = f"사람의 최종 결정 수정: {payload.decision.value}"
        next_payload = dict(card.payload)
        next_payload["final_decision"] = current.model_dump(mode="json")
        _append_audit(next_payload, event_type, current.id, actor_role, summary)
        updated_at = now_iso()
        updated = connection.execute(
            "UPDATE handoff_cards SET payload_json = ?, updated_at = ? WHERE id = ? AND status = 'READY' AND updated_at = ?",
            (json.dumps(next_payload, ensure_ascii=False), updated_at, card_id, original_updated_at),
        )
        if updated.rowcount != 1:
            raise HandoffStateError("핸드오프 카드가 변경되어 최종 결정을 저장하지 못했습니다", card)
        connection.commit()
        saved = connection.execute("SELECT * FROM handoff_cards WHERE id = ?", (card_id,)).fetchone()
    return _card_from_row(saved)
