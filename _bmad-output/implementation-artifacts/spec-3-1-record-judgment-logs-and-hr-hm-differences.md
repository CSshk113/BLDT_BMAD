---
title: 'Story 3.1 판단 로그와 HR·HM 의견 차이 기록'
type: 'feature'
created: '2026-08-27'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'bd812eca70b4d09062436437c349986101f2e0d0'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-3-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-2-3-split-view-and-text-search-highlighting.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** 현재 `ReviewLog`는 기준 교정용 Draft 검토와 같은 흐름에 묶여 있어, 승인된 기준과 완료된 지원서 근거를 기준으로 HR·HM의 실제 판단과 지원서 단계 판정을 독립적으로 보존할 수 없다.

**Approach:** 승인된 기준 버전과 완료된 매핑 결과를 검증하는 판단 로그 API와 화면을 추가한다. HR·HM 로그를 별도로 저장·비교하고, Document 레벨의 HR 스크리닝·HM 서류 심사 판정을 분리하며, 수정 이력은 기존 로그의 `edit_history` JSON 배열에 누적한다.

## Boundaries & Constraints

**Always:** 승인된 `criteria_version_id`와 처리 완료 지원서만 공식 판단 로그를 저장한다. Item 상태는 `충족`, `부분 충족`, `미충족`, `확인 불가`를 사용하고, 판단 사유는 인용구/위치와 함께 저장한다. HR과 HM의 판단은 대표 결론으로 합치지 않는다. 다른 역할의 로그는 읽기 전용이다. Document 판정과 Item 상태를 서로 다른 값으로 유지한다.

**Ask First:** 없음. 기존 제품 결정과 제공 데이터의 공식 어휘를 따른다.

**Never:** Draft 기준을 공식 판단으로 저장하지 않는다. 매핑이 완료되지 않은 지원서, 근거 없는 사유, 점수·순위·합격 확률, 자동 합격·탈락, AI에 의한 의견 통합을 구현하지 않는다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | APPROVED 기준, COMPLETED 매핑, HR/HM 검토 입력 | 역할별 로그와 Document 판정을 저장하고 비교 결과 반환 | N/A |
| DRAFT_OR_INCOMPLETE | DRAFT 기준 또는 미완료 매핑 | 저장하지 않고 공식 검토 불가 안내 | HTTP 409 |
| MISSING_EVIDENCE | `UNVERIFIABLE`이 아닌 상태에 인용구/위치 누락 | 로그를 저장하지 않음 | HTTP 422 |
| OTHER_ROLE_EDIT | 현재 역할과 다른 역할의 로그 수정 | 원본 로그 유지 | HTTP 403 |
| EDIT | 기존 로그 변경 | 현재 값 갱신 및 이전/변경 값·행위자·시각·사유를 `edit_history`에 추가 | N/A |

</frozen-after-approval>

## Code Map

- `backend/app/db.py` -- `review_logs` 스키마와 초기화/마이그레이션 경계; `edit_history` 및 Document 판정 저장 필드 추가 지점.
- `backend/app/models/criteria.py` -- `ReviewLog`, `ReviewInput`, `ReviewSubmission`, `ReviewMatrix` 계약; Item 상태와 역할별 판정 모델 확장 지점.
- `backend/app/services/criteria.py` -- `save_reviews`, `get_review_matrix`, `_row_to_review`; 현재 Draft 교정 로직과 분리해 승인 기준 기반 공식 로그를 검증할 위치.
- `backend/app/api/criteria.py` -- 기존 `/reviews`·`/conflicts` 라우트; 공식 판단 로그 조회/저장 API를 추가할 경계.
- `backend/app/services/mapping.py` -- 완료된 `mapping_results`와 현재 처리 실행의 검증·근거 연결 규칙 재사용 지점.
- `frontend/src/lib/criteria-api.ts` -- ReviewLog/ReviewMatrix 타입과 API 요청 패턴; 공식 판단 로그 계약 확장 지점.
- `frontend/src/components/criteria/CalibrationMatrix.tsx` -- HR/HM 분리·읽기 전용·충돌 표시 UI 패턴 재사용. 공식 판단 화면은 Draft 교정 화면과 상태를 혼동하지 않게 분리.
- `backend/tests/test_criteria_review.py` -- 기존 교정 로그 테스트; 공식 로그 승인 게이트·역할 분리·근거·이력 테스트를 추가할 위치.

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/db.py` -- `review_logs`에 공식/교정 scope·`edit_history`·근거 추적 필드를 추가하고 `document_judgments`를 마이그레이션 -- 기존 데이터와 Draft 교정 기능을 보존한다.
- [x] `backend/app/models/criteria.py` -- 공식 판단 입력·응답 모델과 회사의 HR/HM 단계 판정 어휘를 정의 -- Item 상태와 Document 판정을 분리한다.
- [x] `backend/app/services/criteria.py` -- 완료 매핑 및 APPROVED 기준 게이트, 독립 저장·비교, 역할 검사, 수정 이력 누적을 구현 -- 공식 판단의 근거 추적성과 오판 방지 규칙을 서버에서 보장한다.
- [x] `backend/app/api/criteria.py` -- 공식 판단 로그 조회·저장 라우트를 연결하고 오류를 HTTP 계약으로 변환 -- 프론트엔드가 명확히 실패 상태를 표시할 수 있게 한다.
- [x] `frontend/src/lib/criteria-api.ts` -- 공식 판단 로그 타입과 요청 함수를 추가 -- 화면이 HR/HM 및 Document 판정을 구분해 소비하게 한다.
- [x] `frontend/src/components` -- 기존 검토 UI 패턴을 활용해 HR/HM 판단·차이·Document 판정을 구분 표시하고 다른 역할을 읽기 전용으로 처리 -- 데모에서 양쪽 근거가 보존됨을 확인한다.
- [x] `backend/tests/test_judgment_logs.py` -- I/O 행렬과 AC의 게이트·차이·권한·근거·감사 이력을 검증 -- 회귀를 방지한다.

**Acceptance Criteria:**
- Given 승인된 기준·완료 매핑이 있을 때, when HR 또는 HM이 자신의 Item 상태·사유·인용 근거를 저장하면, then 역할·지원서·항목·기준 버전·시각을 포함한 독립 로그가 저장된다.
- Given HR과 HM 로그가 같은 지원서에 있을 때, when 비교를 조회하면, then 상태·사유·위치·근거 차이와 양쪽 로그가 분리 표시된다.
- Given 다른 역할의 로그를 수정하려 할 때, when 요청하면, then 거부되고 기존 값은 보존된다.
- Given Document 판정을 입력할 때, when HR/HM 단계 어휘를 선택하면, then 두 단계 값이 분리 저장되고 Item 상태와 섞이지 않는다.
- Given 기존 로그를 수정할 때, when 저장하면, then 현재 값은 갱신되고 이전/변경 값·행위자·시각·사유가 `edit_history` 배열에 추가된다.
- Given 근거가 없고 `확인 불가`도 아닐 때, when 저장하면, then 공식 로그가 생성되지 않는다.
- Given 결과를 표시할 때, when 검토자가 확인하면, then 자동 결론·점수·순위·확률 없이 사람의 두 판단을 그대로 제공한다.

## Design Notes

기존 `/api/criteria/{version_id}/reviews`는 Draft 기준 교정 게이트의 계약이므로 의미를 바꾸지 않는다. Story 3.1의 공식 판단 로그는 별도 경로 또는 명확히 분리된 서비스 계약으로 구현하고, 기존 seed 데이터가 공식 로그로 오인되지 않게 승인·완료 조건을 서버에서 검사한다. 인용구는 Story 2 매핑 결과의 citation/source artifact/location 연결을 재사용한다.

## Verification

**Commands:**
- `uv run --no-cache pytest backend/tests -q` -- 전체 백엔드 테스트 성공.
- `npm test -- --run` (workdir `frontend`) -- 프론트엔드 테스트 성공.
- `npx tsc --noEmit` (workdir `frontend`) -- TypeScript 오류 없음.
- `npm run build` (workdir `frontend`) -- 프로덕션 빌드 성공.

## Suggested Review Order

**공식 판단 저장 경계**

- 승인 기준과 전체 기준 매핑을 먼저 검증해 공식 로그의 진입 조건을 보장합니다.
  [`criteria.py:427`](../../backend/app/services/criteria.py#L427)

- HR·HM 로그를 독립 저장하고 근거·실행 추적 ID와 감사 이력을 함께 보존합니다.
  [`criteria.py:510`](../../backend/app/services/criteria.py#L510)

- API에서 판단 저장·조회와 역할별 오류 계약을 외부에 노출합니다.
  [`criteria.py:76`](../../backend/app/api/criteria.py#L76)

**데이터 모델과 호환성**

- 교정 로그와 공식 로그를 scope로 분리하고 기존 SQLite 데이터를 마이그레이션합니다.
  [`db.py:57`](../../backend/app/db.py#L57)

- Item 상태, Document 판정, 역할별 응답 구조를 별도 모델로 유지합니다.
  [`criteria.py:190`](../../backend/app/models/criteria.py#L190)

**검토 화면과 흐름 연결**

- 역할별 입력과 양쪽 의견 차이·감사 이력을 한 화면에서 보여줍니다.
  [`JudgmentWorkspace.tsx:77`](../../frontend/src/components/judgments/JudgmentWorkspace.tsx#L77)

- 지원서 처리 상세에서 판단 로그 화면으로 이어지는 실제 클릭 경로를 제공합니다.
  [`page.tsx:40`](../../frontend/src/app/applications/page.tsx#L40)

**검증·계약**

- 승인 게이트·근거·권한·감사 이력의 API 행위와 회귀를 검증합니다.
  [`test_judgment_logs.py:48`](../../backend/tests/test_judgment_logs.py#L48)

- 프론트엔드 요청 타입과 공식 판단 API 계약을 확인합니다.
  [`criteria-api.ts:86`](../../frontend/src/lib/criteria-api.ts#L86)
