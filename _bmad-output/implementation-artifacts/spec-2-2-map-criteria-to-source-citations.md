---
title: 'Story 2.2 - 기준별 원문 인용구 매핑'
type: 'feature'
created: '2026-08-27'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'd9cbc9565da9e587d26ffa3aea1e29a80ef626e2'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-2-1-pdf-upload-and-llamaparse-markdown-conversion.md'
  - '{project-root}/_bmad-output/planning-artifacts/epics.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Story 2.1은 지원서 원본과 Markdown을 저장하지만, 직무 기준별로 어떤 원문이 근거인지 확인하거나 다시 추적할 수 없다.

**Approach:** 처리 완료된 정규화 Markdown과 기준 버전을 입력으로 받아 각 필수·우대 기준에 대한 원문 인용구, 근거 상태, 위치 정보를 저장하고 API로 제공한다. 인용구는 정규화 Markdown에서 검증되는 부분 문자열만 사용하며, 정확한 PDF 좌표가 없으면 문단·헤딩·페이지·주변 문맥 fallback을 명시한다.

## Boundaries & Constraints

**Always:** 지원서 ID·기준 항목 ID·기준 버전 ID·처리 실행 ID를 모든 매핑에 저장한다. 인용구는 저장된 정규화 Markdown에서 실제로 찾을 수 있어야 하며, 기준별 상태는 `충족`, `부분 충족`, `미충족`, `확인 불가` 중 하나로 명시한다. 근거가 없거나 위치가 불안정하면 이를 성공한 위치 매핑으로 가장하지 않는다. `DRAFT` 결과는 `미리보기`로 표시하고 승인된 공식 결과와 구분한다.

**Ask First:** 없음.

**Never:** AI가 새로 쓴 요약문을 인용구로 저장하지 않는다. 자동 합격·탈락, 점수, 순위, 확률을 만들지 않는다. 처리 중·실패한 실행의 Markdown을 완료된 근거로 사용하지 않는다. Story 2.3의 스플릿 뷰·하이라이트 UI는 구현하지 않는다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 매핑 성공 | `COMPLETED` 실행, 정규화 Markdown, 기준 버전 | 기준 항목별 원문 인용구·상태·위치 저장 | N/A |
| 근거 없음 | 기준 항목과 일치하는 원문 없음 | 빈 인용구 대신 `확인 불가`와 안내 문구 저장 | 생성 문장 금지 |
| 위치 fallback | 페이지·좌표를 안정적으로 얻지 못함 | 스니펫·문단·헤딩·주변 문맥과 `문맥 보기` 표시 | 위치 매핑 성공으로 표시하지 않음 |
| 미완료 실행 | `PARSING`, `MAPPING`, `FAILED` 실행 | 매핑 생성·조회 대상에서 제외 | 완료 실행 필요 안내 |
| 기준 수정 | 같은 기준 버전의 기존 매핑이 `INVALIDATED` | 이전 결과와 새 실행 결과를 섞지 않음 | 재실행 안내 |

</frozen-after-approval>

## Code Map

- `backend/app/db.py` -- 기준별 매핑 결과와 인용구 위치를 저장하는 무결성 경계
- `backend/app/models/criteria.py` -- 기준 항목·기준 상태·기존 매핑 계약과 상태 어휘
- `backend/app/services/criteria.py` -- 기준 버전·항목 조회 및 Draft 미리보기 재사용 지점
- `backend/app/services/applications.py` -- 완료된 정규화 Markdown과 처리 실행 조회 재사용 지점
- `backend/app/api/criteria.py` -- 기존 기준·미리보기 API 패턴과 오류 응답
- `backend/app/main.py` -- 매핑 라우터 등록 지점
- `frontend/src/lib/criteria-api.ts` -- 기준/매핑 API 타입과 호출 패턴
- `frontend/src/app/calibration/page.tsx`, `frontend/src/components/criteria/*` -- 기준 상태·근거 표시 UI 패턴
- `HR_data/03_resumes/표본매핑표.csv` -- 후보 토큰과 비식별 표본 연결 기준
- `backend/tests/test_criteria_mapping.py`, `frontend/src/components/criteria/criteria-mapping.test.tsx` -- 매핑·fallback·Draft 표시 검증

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/db.py`, `backend/app/models/criteria.py` -- 매핑 결과에 지원서·기준·실행 추적 ID, 인용구, 위치/fallback, 근거 상태를 저장하는 계약을 추가한다 -- 이후 원문 추적성을 보장한다.
- [x] `backend/app/services/mapping.py`, `backend/app/services/applications.py` -- 완료된 정규화 Markdown만 대상으로 기준별 원문 부분 문자열을 찾고 위치/fallback을 계산한다 -- 생성 요약과 미완료 결과를 차단한다.
- [x] `backend/app/api/mapping.py`, `backend/app/main.py` -- 지원서 기준별 매핑 실행·조회 API를 연결한다 -- Draft 미리보기와 오류 상태를 일관되게 반환한다.
- [x] `frontend/src/lib/mapping-api.ts`, `frontend/src/components/criteria/MappingResults.tsx` -- 기준별 인용구·상태·위치·fallback과 미리보기 배지를 표시한다 -- Story 2.3에서 선택 가능한 데이터 계약을 제공한다.
- [x] `backend/tests/test_criteria_mapping.py`, `frontend/src/components/criteria/criteria-mapping.test.tsx` -- 성공·근거 없음·fallback·미완료·Draft 시나리오를 검증한다 -- 원문 추적성 회귀를 막는다.

**Acceptance Criteria:**
- Given 처리 완료된 정규화 Markdown과 기준 버전이 있을 때, when 매핑을 실행하면, then 모든 필수·우대 기준에 매핑 결과를 만들고 지원서 ID·기준 버전 ID·기준 항목 ID·처리 실행 ID를 저장해야 한다.
- Given 매핑 결과에 근거가 있을 때, when 결과를 조회하면, then 인용구가 정규화 Markdown의 실제 부분 문자열이고 AI 생성 요약문이 아니어야 한다.
- Given 원문 인용구를 확인할 수 있을 때, when 위치를 저장하면, then 가능한 페이지·문단·헤딩을 연결하고 원본 PDF와 Markdown의 지원서 추적 정보를 유지해야 한다.
- Given 정확한 PDF 위치를 얻을 수 없을 때, when 결과를 생성하면, then 스니펫·페이지·주변 문맥을 `문맥 보기` fallback으로 제공하고 위치 성공으로 표시하지 않아야 한다.
- Given 원문에 근거가 없을 때, when 결과를 조회하면, then `확인 불가`와 `원문에서 확인 가능한 근거가 없습니다`를 표시하고 빈 인용구나 추정 문장을 저장하지 않아야 한다.
- Given 결과가 `DRAFT` 기준에 연결되어 있을 때, when HM이 조회하면, then `미리보기`로 표시하고 공식 결과처럼 보이는 표현을 사용하지 않아야 한다.
- Given 실행이 처리 중이거나 실패했을 때, when 매핑 API를 호출하면, then 매핑을 생성하지 않고 완료 실행이 필요하다는 상태를 반환해야 한다.

## Design Notes

- 인용구 원문 검증을 먼저 수행한 뒤 위치 정보를 붙인다. 위치 정보가 없는 경우에도 근거 문자열과 fallback 문맥은 보존하되 성공 좌표처럼 보이지 않게 한다.
- 기준 항목별 매핑은 재실행 단위로 저장하며, 기준 텍스트 수정으로 무효화된 기존 결과를 새 실행이 덮어쓰지 않도록 한다.

## Verification

**Commands:**
- `uv run --project backend --group dev pytest` -- expected: 기존 기준 테스트와 매핑 성공·fallback·미완료 테스트 통과
- `npm test` (from `frontend`) -- expected: 기준 매핑 표시와 기존 화면 테스트 통과
- `npm run build` (from `frontend`) -- expected: Next.js production build succeeds

## Suggested Review Order

**매핑 진입과 준비 상태**

- 매핑 API가 지원서·기준 버전 입력과 처리 준비 오류를 하나의 경계로 다룬다.
  [`mapping.py:18`](../../backend/app/api/mapping.py#L18)

- 완료된 실행과 동일 실행의 현재 Markdown만 선택해 교차 매핑을 막는다.
  [`mapping.py:144`](../../backend/app/services/mapping.py#L144)

**원문 근거 보존**

- 기준별 키워드는 같은 문단 안에서만 평가하고 실제 Markdown 블록을 인용한다.
  [`mapping.py:54`](../../backend/app/services/mapping.py#L54)

- 매핑 결과에 기준·실행·원문 산출물 추적 ID와 fallback 상태를 저장한다.
  [`db.py:37`](../../backend/app/db.py#L37)

- API 응답은 충족·부분 충족·미충족·확인 불가와 Draft 미리보기를 구분한다.
  [`criteria.py:96`](../../backend/app/models/criteria.py#L96)

**검토 화면과 회귀 검증**

- 기준별 인용구와 문맥 보기 fallback을 사람이 확인할 수 있게 표시한다.
  [`MappingResults.tsx:11`](../../frontend/src/components/criteria/MappingResults.tsx#L11)

- 실제 지원서 ID로 매핑을 실행하고 처리 준비 오류를 안내한다.
  [`page.tsx:12`](../../frontend/src/app/mapping/page.tsx#L12)

- 원문 부분 문자열·Draft·미완료 실행·알 수 없는 실행 ID를 검증한다.
  [`test_criteria_mapping.py:42`](../../backend/tests/test_criteria_mapping.py#L42)

- 매핑 결과 UI의 Draft 및 fallback 표시를 검증한다.
  [`criteria-mapping.test.tsx:6`](../../frontend/src/components/criteria/criteria-mapping.test.tsx#L6)
