---
title: 'Story 3.2 JSON 기반 핸드오프 카드 생성'
type: 'feature'
created: '2026-08-27'
status: 'done'
review_loop_iteration: 0
baseline_commit: '77c9dc69fad8cf6d959824d41bd01adeb8232e02'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-3-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-3-1-record-judgment-logs-and-hr-hm-differences.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Story 3.1의 판단 로그가 저장되어도 현업 리더가 지원서 원문·기준·근거·HR/HM 의견 차이를 한 화면에서 확인할 수 있는 전달 단위가 없다.

**Approach:** 승인된 기준, 처리 완료 매핑, 원문 문맥, 양쪽 공식 판단을 하나의 `HandoffCard.payload_json`으로 구성한다. 동일 지원서·기준 조합은 중복 생성하지 않고, 생성 조건이 부족하면 누락 조건을 명확히 반환한다.

## Boundaries & Constraints

**Always:** 공식 카드는 `APPROVED` 기준, 모든 기준 항목의 `COMPLETED` 매핑, 원문 산출물, HR·HM의 모든 공식 Item 판단 로그가 있을 때만 생성한다. payload에는 지원서 ID·기준 버전·기준 항목·인용구·위치·매핑/산출물 추적 ID·양쪽 판단·차이·근거 부족 항목을 보존한다. 질문·면접 결과 영역은 Story 3.3/3.4가 확장할 JSON 구조로 유지한다. 생성자·시각·상태를 카드 메타데이터에 기록한다.

**Ask First:** 없음. 기존 `payload_json` flattening 결정과 Story 3.1 계약을 따른다.

**Never:** 미승인 기준이나 불완전한 매핑/로그로 부분 카드를 만들지 않는다. HR/HM 판단을 대표 결론으로 통합하지 않는다. 질문·면접 결과를 이번 스토리에서 AI로 생성하거나 자동 결론으로 채우지 않는다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | 승인 기준·완료 매핑·원문·HR/HM 로그 | READY 카드와 추적 가능한 JSON payload 생성 | N/A |
| MISSING_GATE | 기준 미승인, 매핑/원문/로그 일부 누락 | 카드·질문 후보를 만들지 않고 누락 조건을 모두 표시 | HTTP 409 |
| DUPLICATE | 동일 지원서·기준의 READY 카드 존재 | 새 카드를 만들지 않고 기존 카드와 생성 상태 반환 | HTTP 200 |
| PROCESSING | 동일 조합의 PROCESSING 카드 존재 | 중복 생성 차단 | HTTP 409 |
| FAILED | 생성 중 오류가 기록된 카드 존재 | 실패 사유와 대상 버전·지원서 표시 | HTTP 409 |

</frozen-after-approval>

## Code Map

- `backend/app/db.py` -- 기존 SQLite 스키마와 마이그레이션 경계; `handoff_cards`와 JSON payload 저장 지점.
- `backend/app/services/criteria.py` -- Story 3.1의 공식 판단 게이트·비교 결과와 `get_judgment_matrix` 재사용 지점.
- `backend/app/services/mapping.py` -- 완료 매핑·현재 처리 실행·원문 artifact 추적 규칙 재사용 지점.
- `backend/app/services/applications.py` -- 완료된 정규화 Markdown 문맥을 읽는 기존 문서 계약.
- `backend/app/main.py` -- 기존 `/api/handoff/generate` 호환 잠금 응답; 상세 카드 생성 라우트 분리/연결 지점.
- `backend/app/models/criteria.py` -- Story 3.1 판단·근거 응답 구조; 카드 payload에 포함할 입력 모델.
- `frontend/src/lib/criteria-api.ts` -- 기존 핸드오프 잠금 API; 상세 카드 API 호출 패턴 확장 지점.
- `frontend/src/applications/page.tsx` -- 처리 완료 지원서에서 실제 핸드오프 화면으로 이동할 링크 지점.
- `backend/tests/test_criteria_approval.py` -- 기존 잠금 호환 테스트; 새 카드 API 테스트는 별도 파일로 추가.

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/db.py` -- `handoff_cards` 테이블과 기존 DB 마이그레이션을 추가 -- 카드 상태·중복 키·payload를 안전하게 보존한다.
- [x] `backend/app/models/handoff.py` -- 카드 메타데이터·생성 응답·payload 계약을 정의 -- 질문/면접 확장 영역을 JSON으로 표현한다.
- [x] `backend/app/services/handoff.py` -- 공식 생성 게이트, payload 구성, 차이·근거 부족 투영, 중복/처리/실패 상태를 구현 -- 부분 카드와 대표 결론을 방지한다.
- [x] `backend/app/api/handoff.py` -- 생성·조회 API와 역할/오류 계약을 연결 -- LEAD의 카드 열람 흐름을 제공한다.
- [x] `backend/app/main.py` -- 기존 잠금 응답과 새 상세 생성 라우트의 호환을 유지 -- 이전 Story 테스트를 깨뜨리지 않는다.
- [x] `frontend/src/lib/handoff-api.ts` -- 카드 생성·조회 타입과 요청 함수를 추가 -- UI가 생성 상태와 누락 조건을 표시하게 한다.
- [x] `frontend/src/app/handoff/page.tsx` -- 원문·기준·근거·HR/HM 판단 차이를 한 화면에 표시 -- 발표 클릭 데모의 핸드오프 단계를 완성한다.
- [x] `frontend/src/applications/page.tsx` -- 처리 완료 지원서 상세에 핸드오프 진입 링크를 추가 -- 실제 플로우를 연결한다.
- [x] `backend/tests/test_handoff.py` -- 성공·게이트·중복·payload 추적성을 검증 -- I/O 행렬과 AC를 회귀 방지한다.

**Acceptance Criteria:**
- Given 승인 기준·완료 지원서·전체 근거·HR/HM 로그가 있을 때, when LEAD가 생성하면, then 지원서 ID·기준 버전·생성자·시각이 저장된 READY 카드가 생성된다.
- Given 승인/완료/근거/로그가 하나라도 없을 때, when 생성하면, then 누락 조건을 각각 표시하고 카드나 질문 후보를 부분 결과로 만들지 않는다.
- Given READY 카드가 있을 때, when LEAD가 열면, then 원문 문맥, 적용 기준, HR/HM 판단·사유·근거, 의견 차이, 근거 부족 항목과 질문 확장 영역을 한 화면에서 확인한다.
- Given payload를 조회할 때, when 근거를 확인하면, then 지원서·기준 항목·`criteria_version_id`·매핑·처리 실행·원문 산출물 ID 연결을 잃지 않는다.
- Given 동일 지원서·기준 카드가 존재할 때, when 다시 생성하면, then 중복 카드 없이 기존 카드와 상태를 반환한다.
- Given 생성 처리 중 또는 실패 상태일 때, when 조회하면, then 대상 지원서·기준 버전·실패 사유를 표시하고 성공 카드처럼 보이지 않는다.
- Given HR/HM 판단 차이가 있을 때, when 카드를 조회하면, then 한쪽을 대표 결론으로 선택하거나 자동 통합하지 않는다.

## Design Notes

`payload_json`에는 `source_document`, `criteria`, `evidence`, `judgments`, `differences`, `insufficient_evidence`, `interview_questions`, `interview_results` 키를 고정한다. Story 3.2에서는 마지막 두 배열을 비워 두며 이후 스토리가 원본/수정본·선택·검증 결과를 확장한다. 기존 인자 없는 잠금 확인 요청은 이전 계약을 보존하고, 지원서 ID가 있는 요청부터 실제 카드를 생성한다.

## Verification

**Commands:**
- `uv run --project backend --group dev pytest backend/tests -q` -- 전체 백엔드 테스트 성공.
- `npm test -- --run` (workdir `frontend`) -- 프론트엔드 테스트 성공.
- `npx tsc --noEmit` (workdir `frontend`) -- TypeScript 오류 없음.
- `npm run build` (workdir `frontend`) -- 프로덕션 빌드 성공.

## Suggested Review Order

**공식 생성 게이트와 카드 상태**

- 승인 기준, 완료 매핑, 원문, HR/HM 판단을 모두 검증하고 중복 생성을 제어합니다.
  [`handoff.py:62`](../../backend/app/services/handoff.py#L62)

- JSON 카드 생성 중 PROCESSING·READY·FAILED 상태를 안전하게 전환합니다.
  [`handoff.py:169`](../../backend/app/services/handoff.py#L169)

**추적 가능한 저장 계약과 API**

- 카드 payload와 중복 키를 SQLite에 저장해 후속 스토리의 JSON 확장을 보장합니다.
  [`db.py:81`](../../backend/app/db.py#L81)

- 기존 잠금 응답을 보존하면서 상세 카드 생성과 역할 검사를 연결합니다.
  [`handoff.py:12`](../../backend/app/api/handoff.py#L12)

**발표용 카드 화면**

- 원문, 근거 추적 ID, 구조화된 차이, 기준별 HR/HM 판단을 한 화면에 바인딩합니다.
  [`page.tsx:142`](../../frontend/src/app/handoff/page.tsx#L142)

- 지원서 목록에서 실제 핸드오프 카드 생성 화면으로 진입합니다.
  [`page.tsx:40`](../../frontend/src/app/applications/page.tsx#L40)

**검증과 타입 계약**

- 성공·게이트·중복·추적성 시나리오를 회귀 테스트로 고정합니다.
  [`test_handoff.py:1`](../../backend/tests/test_handoff.py#L1)

- 카드 생성·조회 응답의 프론트엔드 타입과 요청 경계를 정의합니다.
  [`handoff-api.ts:3`](../../frontend/src/lib/handoff-api.ts#L3)
