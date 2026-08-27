---
title: '원문 위치와 판단 사유의 의미 비교'
type: 'feature'
created: '2026-08-28'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'fc46517'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** HR과 HM이 같은 근거를 가리켜도 한쪽은 `프로젝트, 페이지 3`, 다른 쪽은 `페이지 3, 프로젝트`처럼 위치 순서를 다르게 쓰면 원문 위치 불일치가 발생한다. 판단 사유도 같은 의미를 다른 표현으로 작성하면 불필요한 불일치로 처리된다.

**Approach:** 서버가 `gpt-5.6-luna`로 두 검토자의 원문 위치와 판단 사유가 의미상 같은지 비교한다. 상태 차이는 기존처럼 별도로 충돌로 처리하며, LLM 호출 실패 시 위치는 결정적 정규화로 비교하고 사유 표현 차이는 승인 차단에 사용하지 않는다.

## Boundaries & Constraints

**Always:** LLM은 의미 동등성만 반환하고 상태의 옳고 그름, 합격·탈락, 새로운 근거를 판단하지 않는다. HR/HM의 원문 사유와 위치는 그대로 보존한다. API 키와 모델 호출은 서버에서만 수행하며 백엔드 전용 `.env` 파일의 `OPENAI_API_KEY`와 선택적 `OPENAI_BASE_URL` 또는 기존 LLM 환경변수에서 읽는다. 실제 `.env` 파일은 저장소에 커밋하지 않고 `.env.example`만 관리한다. LLM 응답은 구조화된 두 boolean 값으로 검증한다.

**Ask First:** 없음.

**Never:** 브라우저에서 LLM을 호출하거나 API 키를 노출하지 않는다. 실제 비밀값을 `.env.example`, 소스 코드, 로그, 저장소에 기록하지 않는다. LLM이 상태 차이 또는 실제로 다른 위치를 임의로 일치 처리하지 않는다. 사유를 자동으로 합치거나 한쪽 기록으로 덮어쓰지 않는다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| ORDER_ONLY_LOCATION | `프로젝트, 페이지 3` vs `페이지 3, 프로젝트` | 원문 위치 차이를 충돌로 추가하지 않음 | LLM 실패 시 위치 토큰 정규화 fallback |
| SEMANTIC_REASON | 같은 상태·근거를 다른 문장으로 작성 | 판단 사유 차이를 충돌로 추가하지 않음 | LLM 실패 시 기존 비차단 동작 유지 |
| DIFFERENT_MEANING | 같은 상태지만 위치 또는 사유의 의미가 다름 | 해당 차이를 표시하고 기존 해결 절차 유지 | LLM 응답이 불명확하면 보수적으로 충돌 |
| STATUS_DIFFERENCE | 위치·사유가 같아도 상태가 다름 | `상태` 충돌 유지 | 의미 비교 결과로 상태 충돌을 덮지 않음 |

</frozen-after-approval>

## Code Map

- `backend/app/services/semantic_comparison.py` -- 서버 전용 LLM 의미 비교와 구조화 응답 검증
- `backend/app/services/criteria.py` -- 교정 행의 상태·위치·사유 비교와 deterministic fallback 결합 지점
- `frontend/src/lib/criteria-api.ts` -- 브라우저 fallback용 위치 토큰 정규화 계약
- `backend/tests/test_criteria_review.py` -- LLM 의미 비교 결과에 따른 충돌 계산 테스트
- `backend/tests/test_semantic_comparison.py` -- 모델 응답 파싱·실패 fallback 단위 테스트
- `frontend/src/app/calibration/page.test.tsx` -- 데모 화면의 기존 충돌·표본 표시 회귀 테스트

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/services/semantic_comparison.py`, `backend/.env.example` -- 백엔드 전용 `.env`의 API 설정으로 `gpt-5.6-luna`을 호출하고 JSON 응답 검증·실패 신호·결정적 fallback 계약을 구현 -- 비밀값을 브라우저와 저장소에서 분리한다.
- [x] `backend/app/services/criteria.py` -- 상태 차이는 우선 유지하고 위치·사유 의미 비교 결과만 차이 목록에 반영 -- 순서가 다른 동일 위치와 유사 표현을 불필요하게 막지 않는다.
- [x] `frontend/src/lib/criteria-api.ts` -- 서버와 동일한 위치 토큰 정규화 규칙을 fallback에 적용 -- 오프라인 데모에서도 위치 순서 차이를 재현하지 않는다.
- [x] `backend/tests/test_semantic_comparison.py`, `backend/tests/test_criteria_review.py` -- 성공·실패·의미 차이·상태 차이와 원본 보존을 검증 -- 회귀를 방지한다.
- [x] `frontend/src/app/calibration/page.test.tsx` -- 기존 교정 표본과 충돌 표시 회귀를 확인 -- 데모 화면을 보호한다.

**Acceptance Criteria:**
- Given 두 검토자의 상태가 같고 위치가 `프로젝트, 페이지 3`과 `페이지 3, 프로젝트`일 때, when 의미 비교를 실행하면, then `원문 위치` 차이를 추가하지 않는다.
- Given 두 검토자의 상태와 위치 의미가 같고 판단 사유의 문장 표현만 다를 때, when 의미 비교를 실행하면, then `판단 사유` 차이를 추가하지 않고 두 원문을 각각 보존한다.
- Given 두 검토자의 상태가 같지만 LLM이 위치 또는 사유를 의미상 다르다고 반환할 때, when 교정 행을 계산하면, then 해당 차이를 표시하고 기존 충돌 해결 흐름을 유지한다.
- Given LLM API 키가 없거나 호출·응답 검증에 실패할 때, when 교정 행을 계산하면, then 서버는 위치 토큰 정규화를 사용하고 사유 표현 차이만으로 승인 게이트를 막지 않는다.
- Given 두 검토자의 상태가 다를 때, when LLM이 두 표현을 같다고 반환해도, then `상태` 충돌은 반드시 유지한다.

## Design Notes

LLM 비교는 교정 API의 서버 경계에서 수행하며, 프롬프트는 두 위치와 두 사유의 의미 동등성만 묻는다. 모델 응답은 `location_equivalent`, `reason_equivalent` 두 boolean으로 제한한다. 네트워크가 없는 테스트·데모 환경에서도 위치 순서와 페이지 별칭은 토큰 정렬로 재현 가능하게 처리하고, 사유는 기존의 비차단 동작을 유지한다.

## Verification

**Commands:**
- `uv run --project backend --group dev pytest backend/tests/test_semantic_comparison.py backend/tests/test_criteria_review.py` -- expected: 의미 비교·충돌 계산 테스트 통과
- `npm run test -- --run src/app/calibration/page.test.tsx` -- expected: 교정 화면 테스트 통과
- `npx tsc --noEmit` -- expected: TypeScript 오류 없음
- `npm run build` -- expected: 프로덕션 빌드 성공

## Suggested Review Order

**의미 비교 경계**

- 위치·사유 의미 비교와 모델 실패 fallback을 한 곳에서 관리합니다.
  [`semantic_comparison.py:111`](../../backend/app/services/semantic_comparison.py#L111)

- 구조화 응답을 검증하고 잘못된 응답은 보수적으로 닫습니다.
  [`semantic_comparison.py:83`](../../backend/app/services/semantic_comparison.py#L83)

- 백엔드 `.env`에서만 모델 키를 읽고 브라우저 노출을 차단합니다.
  [`semantic_comparison.py:59`](../../backend/app/services/semantic_comparison.py#L59)

**충돌 계산과 fallback**

- 상태 차이를 우선 보존하고 의미 비교 결과만 표현 차이에 반영합니다.
  [`criteria.py:363`](../../backend/app/services/criteria.py#L363)

- 네트워크 없는 fallback도 위치 순서와 페이지 범위를 안정적으로 처리합니다.
  [`criteria-api.ts:261`](../../frontend/src/lib/criteria-api.ts#L261)

**검증과 설정**

- LLM 성공·실패·잘못된 응답과 페이지 안전장치를 검증합니다.
  [`test_semantic_comparison.py:13`](../../backend/tests/test_semantic_comparison.py#L13)

- 실제 API 경계에서 의미 차이가 충돌 목록에 반영되는지 검증합니다.
  [`test_criteria_review.py:71`](../../backend/tests/test_criteria_review.py#L71)

- API 설정 예시와 비밀값 제외 규칙을 제공합니다.
  [`backend/.env.example:2`](../../backend/.env.example#L2)
