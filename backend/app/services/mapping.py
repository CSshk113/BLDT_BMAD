"""Source-first criterion mapping for normalized application Markdown."""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
import uuid

from backend.app.db import connect, initialize_schema
from backend.app.models.criteria import (
    CriteriaVersionStatus,
    EvidenceLocationKind,
    EvidenceStatus,
    MappingResponse,
    MappingResult,
    MappingStatus,
)
from backend.app.services.applications import ensure_application_catalog
from backend.app.services.criteria import get_version


class MappingNotReadyError(ValueError):
    """The application has no completed normalized Markdown to map."""


class MappingNotFoundError(KeyError):
    """No completed mapping exists for the requested application/version."""


STOP_WORDS = {
    "및", "또는", "기반", "대한", "있는", "있습니다", "경험", "관리", "운영", "성과", "세일즈",
}


@dataclass(frozen=True)
class EvidenceMatch:
    citation: str
    location: str
    location_kind: EvidenceLocationKind
    status: EvidenceStatus


def _keywords(criterion_text: str) -> list[str]:
    words = re.findall(r"[가-힣A-Za-z0-9+#.]+", criterion_text.lower())
    return [word for word in words if len(word) > 1 and word not in STOP_WORDS]


def _page_number(line: str) -> str | None:
    match = re.search(r"(?:page|페이지)\s*[:#]?\s*(\d+)", line, re.IGNORECASE)
    return match.group(1) if match else None


def _match_evidence(markdown: str, criterion_text: str) -> EvidenceMatch:
    lines = markdown.splitlines()
    full_text = criterion_text.strip()
    matched_keywords = _keywords(criterion_text)
    blocks: list[tuple[int, int, str]] = []
    block_start: int | None = None
    for index, line in enumerate(lines + [""]):
        if line.strip() and block_start is None:
            block_start = index
        if not line.strip() and block_start is not None:
            blocks.append((block_start, index, "\n".join(lines[block_start:index])))
            block_start = None
    candidates: list[tuple[int, int, int, str]] = []
    for start, _, block in blocks:
        lowered = block.lower()
        full_position = lowered.find(full_text.lower()) if full_text else -1
        positions = [(lowered.find(keyword), keyword) for keyword in matched_keywords]
        positions = [(position, keyword) for position, keyword in positions if position >= 0]
        if full_position >= 0:
            candidates.append((100, start, full_position, block))
        elif positions:
            candidates.append((len(positions), start, min(position for position, _ in positions), block))
    if not candidates:
        return EvidenceMatch(
            citation="",
            location="문맥 보기 · 원문에서 확인 가능한 근거가 없습니다",
            location_kind=EvidenceLocationKind.NONE,
            status=EvidenceStatus.UNVERIFIABLE,
        )
    score, line_index, _, citation = max(candidates, key=lambda candidate: (candidate[0], -candidate[1]))
    lowered_citation = citation.lower()
    matched_count = sum(keyword in lowered_citation for keyword in matched_keywords)
    negative_signal = any(signal in lowered_citation for signal in ("없습니다", "없음", "확인되지", "부족", "미충족"))
    status = EvidenceStatus.UNFULFILLED if negative_signal else EvidenceStatus.FULFILLED if score == 100 or matched_count >= 2 else EvidenceStatus.PARTIALLY_FULFILLED

    paragraph = 0
    in_paragraph = False
    for index, line in enumerate(lines):
        if line.strip():
            if not in_paragraph:
                paragraph += 1
            in_paragraph = True
        else:
            in_paragraph = False
        if index >= line_index:
            break
    heading = next(
        (line.strip().lstrip("# ") for line in reversed(lines[: line_index + 1]) if re.match(r"^\s*#{1,6}\s+", line)),
        None,
    )
    page = next((_page_number(line) for line in reversed(lines[: line_index + 1]) if _page_number(line)), None)
    parts = [f"문단 {paragraph}"]
    if heading:
        parts.append(f"헤딩 {heading}")
    if page:
        parts.insert(0, f"p.{page}")
    return EvidenceMatch(
        citation=citation,
        location="문맥 보기 fallback · " + " · ".join(parts),
        location_kind=EvidenceLocationKind.FALLBACK,
        status=status,
    )


def _response_from_rows(rows, *, application_id: str, criteria_version_id: str, criteria_status: CriteriaVersionStatus, run_id: str, artifact_id: str) -> MappingResponse:
    return MappingResponse(
        application_id=application_id,
        criteria_version_id=criteria_version_id,
        criteria_status=criteria_status,
        is_preview=criteria_status == CriteriaVersionStatus.DRAFT,
        processing_run_id=run_id,
        source_artifact_id=artifact_id,
        mappings=[MappingResult(**dict(row)) for row in rows],
    )


def _query_mapping_rows(connection, application_id: str, criteria_version_id: str, run_id: str):
    return connection.execute(
        """
        SELECT m.*, i.criterion_text, i.requirement_type
        FROM mapping_results AS m
        JOIN criteria_items AS i ON i.id = m.criterion_item_id
        WHERE m.application_id = ? AND m.criteria_version_id = ?
          AND m.processing_run_id = ? AND m.mapping_status = 'COMPLETED'
        ORDER BY i.sort_order
        """,
        (application_id, criteria_version_id, run_id),
    ).fetchall()


def create_mappings_for_run(connection, *, application, version, run_id: str, artifact_id: str, markdown: str):
    """Create criterion mappings inside the document-processing transaction."""
    connection.execute(
        "UPDATE mapping_results SET mapping_status = 'INVALIDATED' WHERE application_id = ? AND criteria_version_id = ? AND mapping_status = 'COMPLETED'",
        (application["id"], version.id),
    )
    for item in version.items:
        evidence = _match_evidence(markdown, item.criterion_text)
        connection.execute(
            """
            INSERT INTO mapping_results
            (id, criteria_version_id, application_id, processing_run_id, source_artifact_id,
             applicant_label, criterion_item_id, citation, location, location_kind,
             evidence_status, mapping_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'COMPLETED')
            """,
            (
                f"mapping-{uuid.uuid4().hex[:12]}", version.id, application["id"], run_id, artifact_id,
                f"{application['candidate_token']} · {application['id']}", item.id, evidence.citation,
                evidence.location, evidence.location_kind, evidence.status,
            ),
        )
    return _query_mapping_rows(connection, application["id"], version.id, run_id)


def create_mappings(application_id: str, criteria_version_id: str | None = None) -> MappingResponse:
    ensure_application_catalog()
    version_id = criteria_version_id or ""
    version = get_version(version_id) if version_id else None
    with connect() as connection:
        initialize_schema(connection)
        application = connection.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
        if application is None:
            raise KeyError(application_id)
        version_id = version_id or application["criteria_version_id"]
        version = version or get_version(version_id)
        if application["criteria_version_id"] != version_id:
            raise MappingNotReadyError("지원서와 기준 버전이 일치하지 않습니다")
        run = connection.execute(
            "SELECT * FROM processing_runs WHERE application_id = ? AND criteria_version_id = ? AND status = 'COMPLETED' ORDER BY completed_at DESC, created_at DESC LIMIT 1",
            (application_id, version_id),
        ).fetchone()
        if run is None:
            raise MappingNotReadyError("처리 완료된 실행이 필요합니다")
        artifact = connection.execute(
            "SELECT * FROM application_artifacts WHERE application_id = ? AND artifact_type = 'NORMALIZED_MARKDOWN' AND processing_run_id = ? AND is_current = 1 LIMIT 1",
            (application_id, run["id"]),
        ).fetchone()
        if run is None or artifact is None:
            raise MappingNotReadyError("처리 완료된 정규화 Markdown이 필요합니다")
        markdown_path = Path(artifact["storage_path"])
        if not markdown_path.is_file():
            raise MappingNotReadyError("정규화 Markdown 파일을 찾을 수 없습니다")
        try:
            markdown = markdown_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise MappingNotReadyError("정규화 Markdown을 읽을 수 없습니다") from error
        if not markdown.strip():
            raise MappingNotReadyError("정규화 Markdown이 비어 있습니다")
        rows = create_mappings_for_run(
            connection,
            application=application,
            version=version,
            run_id=run["id"],
            artifact_id=artifact["id"],
            markdown=markdown,
        )
        connection.commit()
    return _response_from_rows(rows, application_id=application_id, criteria_version_id=version_id, criteria_status=version.status, run_id=run["id"], artifact_id=artifact["id"])


def get_mappings(application_id: str, criteria_version_id: str | None = None, run_id: str | None = None) -> MappingResponse:
    ensure_application_catalog()
    with connect() as connection:
        initialize_schema(connection)
        application = connection.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
        if application is None:
            raise KeyError(application_id)
        version_id = criteria_version_id or application["criteria_version_id"]
        version = get_version(version_id)
        if application["criteria_version_id"] != version_id:
            raise MappingNotFoundError(application_id)
        selected_run = connection.execute(
            "SELECT id FROM processing_runs WHERE id = COALESCE(?, id) AND application_id = ? AND criteria_version_id = ? AND status = 'COMPLETED' ORDER BY completed_at DESC, created_at DESC LIMIT 1",
            (run_id, application_id, version_id),
        ).fetchone()
        if selected_run is None:
            raise MappingNotFoundError(application_id)
        selected_run_id = selected_run["id"]
        artifact = connection.execute(
            "SELECT id FROM application_artifacts WHERE application_id = ? AND artifact_type = 'NORMALIZED_MARKDOWN' AND processing_run_id = ? AND is_current = 1 ORDER BY created_at DESC LIMIT 1",
            (application_id, selected_run_id),
        ).fetchone()
        rows = _query_mapping_rows(connection, application_id, version_id, selected_run_id)
        if not rows or artifact is None:
            raise MappingNotFoundError(application_id)
    return _response_from_rows(rows, application_id=application_id, criteria_version_id=version_id, criteria_status=version.status, run_id=selected_run_id, artifact_id=artifact["id"])
