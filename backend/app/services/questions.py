"""핸드오프 카드의 근거 기반 인터뷰 질문 후보 생성 서비스."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
from typing import Any
from urllib import error as url_error
from urllib import request as url_request
import uuid

from dotenv import load_dotenv

from backend.app.models.handoff import (
    HandoffCard,
    HandoffStateError,
    QuestionCandidate,
    QuestionCandidateStatus,
)


MODEL_NAME = "gpt-5.6-luna"
load_dotenv(Path(__file__).resolve().parents[2] / ".env")
QUESTION_BANK_DIR = Path(__file__).resolve().parents[3] / "HR_data" / "04_internal-docs" / "05_면접설계" / "question-bank" / "영업"
MAX_BANK_ENTRY_CHARS = 12000
PROTECTED_TERMS = (
    "나이", "생년월일", "결혼", "자녀", "임신", "종교", "정치", "출신 지역", "출신지역", "학교",
    "장애", "건강", "가족", "재정", "성별", "국적", "사생활",
)
DECISION_TERMS = ("자동 합격", "자동탈락", "자동 탈락", "합격시키", "탈락시키", "채용 여부", "불합격")
LEADING_PATTERNS = ("그렇죠?", "동의하시죠?", "잘하시죠?", "당연히", "맞다고 생각하시죠?")
STOP_WORDS = {
    "경험", "능력", "여부", "방식", "상황", "고객", "기준", "근거", "확인", "질문", "현재", "관련", "영업", "관리", "hr", "hm",
}


class QuestionGenerationError(RuntimeError):
    """모델 호출 또는 구조화 응답 처리에 실패한 경우."""

    def __init__(self, message: str, *, upstream: bool = False):
        self.upstream = upstream
        super().__init__(message)


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _tokens(value: str) -> set[str]:
    return {token.casefold() for token in re.findall(r"[가-힣A-Za-z0-9]{2,}", value) if token.casefold() not in STOP_WORDS}


def _focus_text(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    criteria = payload.get("criteria", {})
    if not isinstance(criteria, dict):
        criteria = {}
    parts.extend(item.get("criterion_text", "") for item in criteria.get("items", []) if isinstance(item, dict))
    parts.extend(item.get("criterion_text", "") for item in payload.get("insufficient_evidence", []) if isinstance(item, dict))
    parts.extend(field for item in payload.get("differences", []) if isinstance(item, dict) for field in item.get("fields", []) if isinstance(field, str))
    judgments = payload.get("judgments", {})
    if not isinstance(judgments, dict):
        judgments = {}
    for row in judgments.get("rows", []):
        if not isinstance(row, dict):
            continue
        for review_key in ("hr_review", "hm_review"):
            review = row.get(review_key) or {}
            if isinstance(review, dict):
                parts.extend((review.get("reason_text", ""), review.get("citation", "")))
    return " ".join(str(part) for part in parts)


def _read_question_bank() -> list[dict[str, str]]:
    if not QUESTION_BANK_DIR.is_dir():
        return []
    entries: list[dict[str, str]] = []
    for path in sorted(QUESTION_BANK_DIR.glob("*.md")):
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if len(content) > MAX_BANK_ENTRY_CHARS:
            half = MAX_BANK_ENTRY_CHARS // 2
            content = f"{content[:half]}\n\n[중략: 파일 중간 내용 생략]\n\n{content[-half:]}"
        entries.append({"file": path.name, "content": content})
    return entries


def select_question_bank(payload: dict[str, Any]) -> list[dict[str, str]]:
    """현재 카드와 키워드가 겹치는 영업 question-bank만 반환한다."""
    focus = _tokens(_focus_text(payload))
    if not focus:
        return []
    selected = []
    for entry in _read_question_bank():
        if len(focus & _tokens(entry["content"])) >= 2:
            selected.append(entry)
    return selected


def build_generation_prompt(payload: dict[str, Any], bank: list[dict[str, str]]) -> str:
    bank_text = "\n\n".join(f"## {entry['file']}\n{entry['content']}" for entry in bank)
    if not bank_text:
        bank_text = "관련 키워드가 겹치는 영업 question-bank 실제 사용 이력이 없습니다. 후보를 만들지 마세요."
    card_input = {
        "criteria": payload.get("criteria", {}),
        "evidence": payload.get("evidence", []),
        "insufficient_evidence": payload.get("insufficient_evidence", []),
        "reviewer_concerns": payload.get("differences", []),
        "judgments": payload.get("judgments", {}),
    }
    return f"""당신은 구조화 면접 질문 설계자입니다. 반드시 JSON 객체의 questions 배열로만 반환하세요.
현재 공식 핸드오프 카드의 입력:
{json.dumps(card_input, ensure_ascii=False, indent=2)}

관련 직군의 실제 사용 질문·의도·평가 포인트:
{bank_text}

규칙:
- 카드의 기준과 저장된 원문 근거로만 구체적이고 검증 가능한 비유도 질문을 만드세요.
- 후보마다 criterion_item_ids와 evidence_ids를 카드 입력의 실제 id로 연결하세요.
- 원 질문(original_question), 현재 질문(current_question), 이유(reason), 질문 유형(question_type: BEI/SJT/KNOWLEDGE)을 포함하세요.
- original_question과 current_question은 최소 12자 이상의 구체적인 완결형 한국어 질문으로 작성하고, `?`, `요`, `까요`, `나요`, `주세요` 중 하나로 끝내세요. Markdown과 따옴표는 붙이지 마세요.
- 보호 특성·사생활·자동 합격/탈락 판단을 묻지 마세요. 질문 수는 고정하지 않습니다.
- 응답 형식: {{"questions":[{{"original_question":"...","current_question":"...","reason":"...","criterion_item_ids":["..."],"evidence_ids":["..."],"question_type":"BEI"}}]}}
"""


def _endpoint() -> str:
    base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1"
    return f"{base_url.rstrip('/')}/chat/completions"


def request_model(prompt: str) -> Any:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key:
        raise QuestionGenerationError("LLM API 키가 서버 환경변수에 없습니다")
    body = json.dumps({
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "JSON 배열만 반환합니다."},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    try:
        request = url_request.Request(_endpoint(), data=body, headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }, method="POST")
        with url_request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except url_error.HTTPError as exc:
        upstream_message = ""
        try:
            raw_body = exc.read().decode("utf-8")
            parsed_body = json.loads(raw_body)
            if isinstance(parsed_body, dict):
                error_body = parsed_body.get("error")
                if isinstance(error_body, dict):
                    upstream_message = str(error_body.get("message") or error_body.get("type") or "")
                elif isinstance(parsed_body.get("detail"), str):
                    upstream_message = parsed_body["detail"]
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            pass
        suffix = f": {upstream_message[:240]}" if upstream_message else ""
        raise QuestionGenerationError(f"질문 생성 모델 요청이 거부되었습니다 (HTTP {exc.code}){suffix}", upstream=True) from exc
    except (url_error.URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise QuestionGenerationError("질문 생성 모델을 사용할 수 없습니다", upstream=True) from exc


def _response_content(response: Any) -> Any:
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        if isinstance(response.get("candidates"), list):
            return response["candidates"]
        choices = response.get("choices")
        if isinstance(choices, list) and choices:
            if not isinstance(choices[0], dict):
                raise QuestionGenerationError("모델 응답의 choices 형식이 올바르지 않습니다", upstream=True)
            message = choices[0].get("message", {})
            content = message.get("content", "") if isinstance(message, dict) else ""
            if isinstance(content, list):
                content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
            if not isinstance(content, str):
                raise QuestionGenerationError("모델 응답의 content 형식이 올바르지 않습니다", upstream=True)
            content = content.strip().removeprefix("```json").removesuffix("```").strip()
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as exc:
                raise QuestionGenerationError("모델 응답이 JSON 형식이 아닙니다", upstream=True) from exc
            return _response_content(parsed)
        if isinstance(response.get("output"), list):
            texts = [item.get("content", []) for item in response["output"] if isinstance(item, dict)]
            joined = "".join(part.get("text", "") for group in texts for part in group if isinstance(part, dict))
            try:
                return _response_content(json.loads(joined))
            except (json.JSONDecodeError, TypeError) as exc:
                raise QuestionGenerationError("모델 응답이 JSON 형식이 아닙니다", upstream=True) from exc
        if isinstance(response.get("questions"), list):
            return response["questions"]
    raise QuestionGenerationError("모델 응답에 질문 후보 배열이 없습니다", upstream=True)


def _clean_question(value: str) -> str:
    """모델이 붙인 Markdown/인용부호만 제거하고 질문 문장은 보존한다."""
    return value.strip().strip("`*_\"'“”‘’")


def _normalize_candidate(raw: dict[str, Any], payload: dict[str, Any], created_at: str) -> QuestionCandidate:
    if not isinstance(raw, dict):
        raise QuestionGenerationError("질문 후보 형식이 올바르지 않습니다", upstream=True)
    original = _clean_question(str(raw.get("original_question") or raw.get("question") or ""))
    current = _clean_question(str(raw.get("current_question") or raw.get("question") or original))
    criteria_ids = raw.get("criterion_item_ids") or raw.get("criteria_ids") or raw.get("linked_criteria_ids") or []
    evidence_ids = raw.get("evidence_ids") or raw.get("linked_evidence_ids") or []
    if raw.get("criterion_item_id"):
        criteria_ids = [raw["criterion_item_id"]]
    if raw.get("evidence_id"):
        evidence_ids = [raw["evidence_id"]]
    if not isinstance(criteria_ids, list) or not isinstance(evidence_ids, list):
        raise QuestionGenerationError("질문 후보 연결 ID 형식이 올바르지 않습니다", upstream=True)
    criterion_ids = [str(value) for value in criteria_ids]
    evidence_ids = [str(value) for value in evidence_ids]
    candidate = QuestionCandidate(
        id=f"question-{uuid.uuid4().hex[:12]}",
        original_question=original,
        current_question=current,
        reason=str(raw.get("reason") or raw.get("question_reason") or "카드의 미검증 근거를 확인하기 위한 질문").strip(),
        criterion_item_ids=criterion_ids,
        evidence_ids=evidence_ids,
        question_type=str(raw.get("question_type") or raw.get("type") or "BEI").strip().upper(),
        status=QuestionCandidateStatus.CANDIDATE,
        created_at=created_at,
        edit_history=[],
    )
    validate_candidate(candidate, payload)
    return candidate


def validate_candidate(candidate: QuestionCandidate, payload: dict[str, Any], existing: list[QuestionCandidate] | None = None) -> None:
    question = candidate.current_question
    normalized_question = re.sub(r"\s+", "", question).casefold()
    if any(re.sub(r"\s+", "", term).casefold() in normalized_question for term in PROTECTED_TERMS):
        raise ValueError("보호 특성·사생활을 묻는 질문은 저장할 수 없습니다")
    if any(re.sub(r"\s+", "", term).casefold() in normalized_question for term in DECISION_TERMS):
        raise ValueError("자동 합격·탈락 판단을 유도하는 질문은 저장할 수 없습니다")
    if any(pattern in question for pattern in LEADING_PATTERNS):
        raise ValueError("유도 질문은 저장할 수 없습니다")
    question_like = bool(re.search(r"(?:[?？]|요|까요|나요|습니까|ㅂ니까|세요|십시오|주세요)[.!。！？\"”’'`]*$", question))
    if len(question) < 12 or not question_like:
        raise ValueError("질문은 구체적이고 검증 가능한 문장이어야 합니다")
    criteria_section = payload.get("criteria", {})
    criteria_items = criteria_section.get("items", []) if isinstance(criteria_section, dict) else []
    evidence_items = payload.get("evidence", [])
    criteria_ids = {item.get("id") for item in criteria_items if isinstance(item, dict)}
    evidence_ids = {item.get("id") for item in evidence_items if isinstance(item, dict)}
    if not set(candidate.criterion_item_ids) <= criteria_ids or not candidate.criterion_item_ids:
        raise ValueError("질문 후보의 연결 기준이 현재 카드에 없습니다")
    if not set(candidate.evidence_ids) <= evidence_ids or not candidate.evidence_ids:
        raise ValueError("질문 후보의 참조 근거가 현재 카드에 없습니다")
    if candidate.question_type not in {"BEI", "SJT", "KNOWLEDGE"}:
        raise ValueError("질문 유형은 BEI, SJT 또는 KNOWLEDGE여야 합니다")
    normalized = re.sub(r"\s+", "", question).lower()
    for previous in existing or []:
        if re.sub(r"\s+", "", previous.current_question).lower() == normalized:
            raise ValueError("중복 질문 후보는 저장할 수 없습니다")


def generate_candidates(card: HandoffCard) -> list[QuestionCandidate]:
    if card.status.value != "READY":
        raise HandoffStateError("READY 상태의 핸드오프 카드만 질문을 생성할 수 있습니다", card)
    bank = select_question_bank(card.payload)
    if not bank:
        return []
    prompt = build_generation_prompt(card.payload, bank)
    response = request_model(prompt)
    raw_candidates = _response_content(response)
    if not isinstance(raw_candidates, list):
        raise QuestionGenerationError("모델 응답이 질문 후보 배열이 아닙니다", upstream=True)
    generated_at = now_iso()
    existing = [QuestionCandidate.model_validate(item) for item in card.payload.get("interview_questions", [])]
    candidates = []
    for raw in raw_candidates:
        candidate = _normalize_candidate(raw, card.payload, generated_at)
        validate_candidate(candidate, card.payload, existing + candidates)
        candidates.append(candidate)
    return candidates
