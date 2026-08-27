"""Criteria version and Draft preview business rules."""

from datetime import UTC, datetime
import uuid

from backend.app.db import connect, initialize_schema
from backend.app.models.criteria import (
    CriteriaItem,
    CriteriaApprovalResult,
    CriteriaMutationResult,
    CriteriaVersion,
    CriteriaVersionStatus,
    DraftPreview,
    ConflictRow,
    ConflictResolution,
    ConflictResolutionInput,
    ConflictStatus,
    MappingStatus,
    OfficialActionRejected,
    PreviewMapping,
    ReviewInput,
    ReviewLog,
    ReviewMatrix,
    ReviewSubmission,
    ReviewStatus,
    ReviewerRole,
)


POSITION_NAME = "B2B 영업 매니저 5년 이상 ver.4"
DEFAULT_ITEMS = (
    ("콜드 아웃바운드 영업 경험", "필수"),
    ("B2B 세일즈 파이프라인 운영 경험", "필수"),
    ("CRM 또는 세일즈 데이터 기반 성과 관리", "우대"),
)
DEMO_APPLICATION_ID = "APPS-2"

DEMO_REVIEWS = (
    ("HR", 1, "FULFILLED", "신규 고객 발굴 경험이 명시되어 있습니다.", "p.2 · 경력기술서"),
    ("HM", 1, "PARTIALLY_FULFILLED", "콜드 아웃바운드 방식과 기간을 추가 확인해야 합니다.", "p.2 · 경력기술서"),
    ("HR", 2, "UNVERIFIABLE", "파이프라인 운영 도구와 담당 범위가 확인되지 않습니다.", "p.3 · 프로젝트"),
    ("HR", 3, "PARTIALLY_FULFILLED", "성과 수치는 있으나 CRM 사용 근거가 부족합니다.", "p.3 · 프로젝트"),
    ("HM", 3, "UNFULFILLED", "CRM 또는 세일즈 데이터 운영 경험이 원문에 없습니다.", "p.3 · 프로젝트"),
)


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def ensure_seed_data() -> None:
    with connect() as connection:
        initialize_schema(connection)
        existing = connection.execute("SELECT id FROM criteria_versions LIMIT 1").fetchone()
        if existing:
            _ensure_demo_reviews(connection, existing["id"])
            connection.commit()
            return
        timestamp = now_iso()
        version_id = "cv-b2b-sales-v4"
        connection.execute(
            "INSERT INTO criteria_versions (id, position_name, status, created_at, updated_at, approved_at, approved_by) VALUES (?, ?, 'DRAFT', ?, ?, NULL, NULL)",
            (version_id, POSITION_NAME, timestamp, timestamp),
        )
        for index, (text, requirement_type) in enumerate(DEFAULT_ITEMS):
            item_id = f"{version_id}-item-{index + 1}"
            connection.execute(
                "INSERT INTO criteria_items VALUES (?, ?, ?, ?, ?)",
                (item_id, version_id, text, requirement_type, index),
            )
        connection.execute(
            """
            INSERT INTO mapping_results
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'COMPLETED')
            """,
            (
                "mapping-demo-1",
                version_id,
                "APPS-2",
                "대표 지원자 · APPS-2",
                f"{version_id}-item-1",
                '"신규 고객 30개사를 직접 발굴하고 콜드 아웃바운드로 미팅을 만들었습니다."',
                "p.2 · 경력기술서",
                "원문 확인 가능",
            ),
        )
        _ensure_demo_reviews(connection, version_id)
        connection.commit()


def _ensure_demo_reviews(connection, version_id: str) -> None:
    existing = connection.execute(
        "SELECT COUNT(*) AS count FROM review_logs WHERE criteria_version_id = ?",
        (version_id,),
    ).fetchone()["count"]
    if existing:
        return
    items = connection.execute(
        "SELECT id FROM criteria_items WHERE criteria_version_id = ? ORDER BY sort_order",
        (version_id,),
    ).fetchall()
    for reviewer_role, item_number, review_status, reason_text, source_location in DEMO_REVIEWS:
        if item_number > len(items):
            continue
        timestamp = now_iso()
        item_id = items[item_number - 1]["id"]
        connection.execute(
            """
            INSERT INTO review_logs
            (id, criteria_version_id, application_id, criterion_item_id, reviewer_role,
             review_status, reason_text, source_location, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"review-demo-{version_id}-{reviewer_role.lower()}-{item_number}",
                version_id,
                DEMO_APPLICATION_ID,
                item_id,
                reviewer_role,
                review_status,
                reason_text,
                source_location,
                timestamp,
                timestamp,
            ),
        )


def _row_to_version(connection, row) -> CriteriaVersion:
    items = connection.execute(
        "SELECT * FROM criteria_items WHERE criteria_version_id = ? ORDER BY sort_order",
        (row["id"],),
    ).fetchall()
    return CriteriaVersion(
        id=row["id"],
        position_name=row["position_name"],
        status=row["status"],
        items=[CriteriaItem(**dict(item)) for item in items],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        approved_at=row["approved_at"],
        approved_by=row["approved_by"],
    )


def list_versions() -> list[CriteriaVersion]:
    ensure_seed_data()
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM criteria_versions ORDER BY updated_at DESC"
        ).fetchall()
        return [_row_to_version(connection, row) for row in rows]


def get_version(version_id: str) -> CriteriaVersion:
    ensure_seed_data()
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM criteria_versions WHERE id = ?", (version_id,)
        ).fetchone()
        if not row:
            raise KeyError(version_id)
        return _row_to_version(connection, row)


def create_draft_version(source_version_id: str) -> CriteriaVersion:
    source = get_version(source_version_id)
    version_id = f"cv-{uuid.uuid4().hex[:10]}"
    timestamp = now_iso()
    with connect() as connection:
        initialize_schema(connection)
        connection.execute(
            "INSERT INTO criteria_versions (id, position_name, status, created_at, updated_at, approved_at, approved_by) VALUES (?, ?, 'DRAFT', ?, ?, NULL, NULL)",
            (version_id, source.position_name, timestamp, timestamp),
        )
        for index, item in enumerate(source.items):
            connection.execute(
                "INSERT INTO criteria_items VALUES (?, ?, ?, ?, ?)",
                (f"{version_id}-item-{index + 1}", version_id, item.criterion_text, item.requirement_type, index),
            )
        connection.commit()
    return get_version(version_id)


def update_draft(version_id: str, item_texts: list[str]) -> CriteriaMutationResult:
    version = get_version(version_id)
    if version.status != CriteriaVersionStatus.DRAFT:
        raise ValueError("APPROVED 또는 ARCHIVED 기준은 직접 수정할 수 없습니다")
    if len(item_texts) != len(version.items):
        raise ValueError("기준 항목 수는 현재 MVP에서 변경할 수 없습니다")
    changed = any(new != old.criterion_text for new, old in zip(item_texts, version.items))
    timestamp = now_iso()
    invalidated_count = 0
    with connect() as connection:
        for item, text in zip(version.items, item_texts):
            connection.execute(
                "UPDATE criteria_items SET criterion_text = ? WHERE id = ?",
                (text, item.id),
            )
        connection.execute(
            "UPDATE criteria_versions SET updated_at = ? WHERE id = ?",
            (timestamp, version_id),
        )
        if changed:
            result = connection.execute(
                "UPDATE mapping_results SET mapping_status = 'INVALIDATED' "
                "WHERE criteria_version_id = ? AND mapping_status != 'INVALIDATED'",
                (version_id,),
            )
            invalidated_count = result.rowcount
        connection.commit()
    return CriteriaMutationResult(
        version=get_version(version_id),
        invalidated_mapping_count=invalidated_count,
        rerun_required=changed and invalidated_count > 0,
    )


def get_preview(version_id: str) -> DraftPreview:
    version = get_version(version_id)
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM mapping_results WHERE criteria_version_id = ? ORDER BY id",
            (version_id,),
        ).fetchall()
    return DraftPreview(
        criteria_version_id=version.id,
        criteria_status=version.status,
        is_preview=version.status == CriteriaVersionStatus.DRAFT,
        mappings=[PreviewMapping(**dict(row)) for row in rows],
    )


def _row_to_review(row) -> ReviewLog:
    return ReviewLog(
        id=row["id"],
        criteria_version_id=row["criteria_version_id"],
        application_id=row["application_id"],
        criterion_item_id=row["criterion_item_id"],
        reviewer_role=row["reviewer_role"],
        status=row["review_status"],
        reason_text=row["reason_text"],
        source_location=row["source_location"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def get_review_matrix(version_id: str, application_id: str = DEMO_APPLICATION_ID) -> ReviewMatrix:
    version = get_version(version_id)
    ensure_seed_data()
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT * FROM review_logs
            WHERE criteria_version_id = ? AND application_id = ?
            ORDER BY updated_at, id
            """,
            (version_id, application_id),
        ).fetchall()
        resolution_rows = connection.execute(
            "SELECT * FROM conflict_resolutions WHERE criteria_version_id = ? AND application_id = ?",
            (version_id, application_id),
        ).fetchall()
    resolutions = {
        row["criterion_item_id"]: ConflictResolution(
            id=row["id"],
            criteria_version_id=row["criteria_version_id"],
            application_id=row["application_id"],
            criterion_item_id=row["criterion_item_id"],
            status=row["status"],
            resolved_by=row["resolved_by"],
            resolved_at=row["resolved_at"],
            resolution_reason=row["resolution_reason"],
        )
        for row in resolution_rows
    }
    by_item: dict[str, dict[ReviewerRole, ReviewLog]] = {}
    for row in rows:
        review = _row_to_review(row)
        by_item.setdefault(review.criterion_item_id, {})[review.reviewer_role] = review

    matrix_rows: list[ConflictRow] = []
    for item in version.items:
        reviews = by_item.get(item.id, {})
        hr_review = reviews.get(ReviewerRole.HR)
        hm_review = reviews.get(ReviewerRole.HM)
        differences: list[str] = []
        if hr_review and hm_review:
            if hr_review.status != hm_review.status:
                differences.append("상태")
            if hr_review.source_location != hm_review.source_location:
                differences.append("원문 위치")
            if hr_review.reason_text != hm_review.reason_text:
                differences.append("판단 사유")
        conflict_status = (
            ConflictStatus.OPEN
            if differences
            else ConflictStatus.NONE
            if hr_review and hm_review
            else ConflictStatus.PENDING
        )
        resolution = resolutions.get(item.id)
        if resolution and differences:
            conflict_status = ConflictStatus.RESOLVED
        matrix_rows.append(
            ConflictRow(
                criterion_item_id=item.id,
                criterion_text=item.criterion_text,
                requirement_type=item.requirement_type,
                conflict_status=conflict_status,
                differences=differences,
                hr_review=hr_review,
                hm_review=hm_review,
                resolution=resolution,
            )
        )
    return ReviewMatrix(
        criteria_version_id=version.id,
        application_id=application_id,
        rows=matrix_rows,
        open_conflict_count=sum(row.conflict_status == ConflictStatus.OPEN for row in matrix_rows),
    )


def save_reviews(version_id: str, submission: ReviewSubmission, actor_role: ReviewerRole) -> ReviewMatrix:
    version = get_version(version_id)
    if version.status != CriteriaVersionStatus.DRAFT:
        raise ValueError("승인된 기준에는 교정 검토를 추가할 수 없습니다")
    if actor_role != submission.reviewer_role:
        raise PermissionError("다른 검토자의 ReviewLog는 수정할 수 없습니다")
    item_ids = {item.id for item in version.items}
    if any(review.criterion_item_id not in item_ids for review in submission.reviews):
        raise ValueError("기준 버전에 속하지 않은 항목입니다")
    timestamp = now_iso()
    with connect() as connection:
        for review in submission.reviews:
            existing = connection.execute(
                """
                SELECT id, created_at, review_status, reason_text, source_location FROM review_logs
                WHERE criteria_version_id = ? AND application_id = ?
                  AND criterion_item_id = ? AND reviewer_role = ?
                """,
                (version_id, submission.application_id, review.criterion_item_id, submission.reviewer_role),
            ).fetchone()
            if existing:
                connection.execute(
                    """
                    UPDATE review_logs
                    SET review_status = ?, reason_text = ?, source_location = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (review.status, review.reason_text, review.source_location, timestamp, existing["id"]),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO review_logs
                    (id, criteria_version_id, application_id, criterion_item_id, reviewer_role,
                     review_status, reason_text, source_location, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"review-{uuid.uuid4().hex[:12]}",
                        version_id,
                        submission.application_id,
                        review.criterion_item_id,
                        submission.reviewer_role,
                        review.status,
                        review.reason_text,
                        review.source_location,
                        timestamp,
                        timestamp,
                    ),
                )
            review_changed = (
                not existing
                or existing["review_status"] != review.status
                or existing["reason_text"] != review.reason_text
                or existing["source_location"] != review.source_location
            )
            if review_changed:
                # A changed review can reopen a previously resolved disagreement.
                # Keep the ReviewLog, but require a fresh HR resolution.
                connection.execute(
                    "DELETE FROM conflict_resolutions "
                    "WHERE criteria_version_id = ? AND application_id = ? AND criterion_item_id = ?",
                    (version_id, submission.application_id, review.criterion_item_id),
                )
        connection.commit()
    return get_review_matrix(version_id, submission.application_id)


def reject_official_action(version_id: str) -> OfficialActionRejected | None:
    version = get_version(version_id)
    if version.status == CriteriaVersionStatus.APPROVED:
        return None
    return OfficialActionRejected(
        code="CRITERIA_NOT_APPROVED",
        message="기준 버전이 승인되기 전에는 공식 핸드오프와 최종 결정을 사용할 수 없습니다.",
        criteria_version_id=version.id,
        missing_conditions=["HM 검토 완료", "열린 충돌 0건", "기준 버전 승인"],
    )


def resolve_conflict(version_id: str, payload: ConflictResolutionInput, actor_role: ReviewerRole) -> ReviewMatrix:
    version = get_version(version_id)
    if version.status != CriteriaVersionStatus.DRAFT:
        raise ValueError("승인된 기준의 충돌은 변경할 수 없습니다")
    if actor_role != ReviewerRole.HR:
        raise PermissionError("충돌 해결은 HR만 수행할 수 있습니다")
    matrix = get_review_matrix(version_id, payload.application_id)
    row = next((candidate for candidate in matrix.rows if candidate.criterion_item_id == payload.criterion_item_id), None)
    if row is None:
        raise ValueError("기준 버전에 속하지 않은 항목입니다")
    if row.conflict_status != ConflictStatus.OPEN:
        raise ValueError("열린 충돌 항목만 해결할 수 있습니다")
    timestamp = now_iso()
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO conflict_resolutions
            (id, criteria_version_id, application_id, criterion_item_id, status, resolved_by, resolved_at, resolution_reason)
            VALUES (?, ?, ?, ?, 'RESOLVED', 'HR', ?, ?)
            ON CONFLICT(criteria_version_id, application_id, criterion_item_id)
            DO UPDATE SET status = 'RESOLVED', resolved_by = 'HR', resolved_at = excluded.resolved_at, resolution_reason = excluded.resolution_reason
            """,
            (
                f"resolution-{uuid.uuid4().hex[:12]}",
                version_id,
                payload.application_id,
                payload.criterion_item_id,
                timestamp,
                payload.resolution_reason,
            ),
        )
        connection.commit()
    return get_review_matrix(version_id, payload.application_id)


def approve_criteria(version_id: str, actor_role: ReviewerRole) -> CriteriaApprovalResult:
    version = get_version(version_id)
    if actor_role != ReviewerRole.HR:
        raise PermissionError("기준 승인은 HR만 수행할 수 있습니다")
    if version.status != CriteriaVersionStatus.DRAFT:
        raise ValueError("DRAFT 기준만 승인할 수 있습니다")
    matrix = get_review_matrix(version_id)
    pending_rows = [row for row in matrix.rows if row.conflict_status == ConflictStatus.PENDING]
    open_rows = [row for row in matrix.rows if row.conflict_status == ConflictStatus.OPEN]
    if open_rows or pending_rows:
        missing = []
        if open_rows:
            missing.append(f"열린 충돌 {len(open_rows)}건 해결")
        if pending_rows:
            missing.append(f"양쪽 검토 완료 {len(pending_rows)}건")
        raise ValueError("승인 조건이 충족되지 않았습니다: " + " · ".join(missing))
    timestamp = now_iso()
    with connect() as connection:
        connection.execute(
            "UPDATE criteria_versions SET status = 'APPROVED', approved_at = ?, approved_by = 'HR', updated_at = ? WHERE id = ?",
            (timestamp, timestamp, version_id),
        )
        connection.commit()
    approved = get_version(version_id)
    return CriteriaApprovalResult(
        version=approved,
        criteria_version_id=approved.id,
        approved_by=ReviewerRole.HR,
        approved_at=approved.approved_at,
    )
