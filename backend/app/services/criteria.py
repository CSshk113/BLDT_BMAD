"""Criteria version and Draft preview business rules."""

from datetime import UTC, datetime
import uuid

from backend.app.db import connect, initialize_schema
from backend.app.models.criteria import (
    CriteriaItem,
    CriteriaMutationResult,
    CriteriaVersion,
    CriteriaVersionStatus,
    DraftPreview,
    MappingStatus,
    OfficialActionRejected,
    PreviewMapping,
)


POSITION_NAME = "B2B 영업 매니저 5년 이상 ver.4"
DEFAULT_ITEMS = (
    ("콜드 아웃바운드 영업 경험", "필수"),
    ("B2B 세일즈 파이프라인 운영 경험", "필수"),
    ("CRM 또는 세일즈 데이터 기반 성과 관리", "우대"),
)


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def ensure_seed_data() -> None:
    with connect() as connection:
        initialize_schema(connection)
        existing = connection.execute("SELECT id FROM criteria_versions LIMIT 1").fetchone()
        if existing:
            return
        timestamp = now_iso()
        version_id = "cv-b2b-sales-v4"
        connection.execute(
            "INSERT INTO criteria_versions VALUES (?, ?, 'DRAFT', ?, ?, NULL)",
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
        connection.commit()


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
            "INSERT INTO criteria_versions VALUES (?, ?, 'DRAFT', ?, ?, NULL)",
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
