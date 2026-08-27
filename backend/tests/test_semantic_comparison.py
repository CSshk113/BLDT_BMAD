import json

import pytest

from backend.app.services import semantic_comparison


def test_location_token_fallback_ignores_expression_order_and_preserves_ranges():
    assert semantic_comparison.normalize_location_tokens("프로젝트, 페이지 3") == semantic_comparison.normalize_location_tokens("페이지 3, 프로젝트")
    assert semantic_comparison.normalize_location_tokens("p.2-3 · 프로젝트") != semantic_comparison.normalize_location_tokens("p.23 · 프로젝트")


def test_compare_expressions_uses_structured_llm_response(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    captured: list[str] = []

    def fake_request(prompt: str):
        captured.append(prompt)
        return {"choices": [{"message": {"content": json.dumps({"location_equivalent": True, "reason_equivalent": True})}}]}

    monkeypatch.setattr(semantic_comparison, "request_model", fake_request)

    result = semantic_comparison.compare_expressions(
        hr_location="프로젝트, 페이지 3",
        hm_location="페이지 3, 프로젝트",
        hr_reason="파이프라인 경험을 확인했습니다.",
        hm_reason="세일즈 파이프라인 운영 이력이 보입니다.",
    )

    assert result.location_equivalent is True
    assert result.reason_equivalent is True
    assert result.used_llm is True
    assert "프로젝트, 페이지 3" in captured[0]


def test_llm_failure_keeps_reason_difference_non_blocking(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        semantic_comparison,
        "request_model",
        lambda _prompt: (_ for _ in ()).throw(semantic_comparison.SemanticComparisonError("연결 실패")),
    )

    result = semantic_comparison.compare_expressions(
        hr_location="p.3 · 프로젝트",
        hm_location="3페이지 / 프로젝트",
        hr_reason="운영 도구를 확인했습니다.",
        hm_reason="전혀 다른 근거입니다.",
    )

    assert result.location_equivalent is True
    assert result.reason_equivalent is True
    assert result.used_llm is False


def test_invalid_llm_response_fails_closed(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(semantic_comparison, "request_model", lambda _prompt: {"unexpected": True})

    result = semantic_comparison.compare_expressions(
        hr_location="p.3 · 프로젝트",
        hm_location="페이지 3, 프로젝트",
        hr_reason="운영 도구를 확인했습니다.",
        hm_reason="운영 도구를 확인했습니다.",
    )

    assert result.location_equivalent is False
    assert result.reason_equivalent is False
    assert result.used_llm is True


def test_malformed_nested_llm_response_fails_closed(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(semantic_comparison, "request_model", lambda _prompt: {"choices": [{"message": None}]})

    result = semantic_comparison.compare_expressions(
        hr_location="p.3 · 프로젝트",
        hm_location="페이지 3, 프로젝트",
        hr_reason="같은 근거입니다.",
        hm_reason="같은 근거입니다.",
    )

    assert result.location_equivalent is False
    assert result.reason_equivalent is False


def test_model_cannot_override_different_page_numbers(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        semantic_comparison,
        "request_model",
        lambda _prompt: {"location_equivalent": True, "reason_equivalent": True},
    )

    result = semantic_comparison.compare_expressions(
        hr_location="p.3 · 프로젝트",
        hm_location="p.4 · 프로젝트",
        hr_reason="같은 근거입니다.",
        hm_reason="같은 근거입니다.",
    )

    assert result.location_equivalent is False
