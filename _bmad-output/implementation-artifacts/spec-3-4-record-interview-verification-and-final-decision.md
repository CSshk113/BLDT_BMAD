---
title: 'Story 3.4 면접 검증 결과와 최종 결정 기록'
type: 'feature'
created: '2026-08-28'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'a3ba6b6'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-3-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-3-3-manage-evidence-and-question-bank-interview-candidates.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** 핸드오프 카드가 서류 단계의 우려와 질문 후보를 보존해도, 면접에서 무엇이 확인되었고 최종 판단이 왜 내려졌는지 같은 근거 흐름으로 남지 않는다.

**Approach:** LEAD가 선택한 질문별로 서류 초기 가설과 실제 면접 결과를 분리해 기록하고, 모든 필요한 검증 결과를 확인한 뒤 사람이 네 가지 공식 결정값 중 하나와 사유를 저장한다. 결과와 결정은 HandoffCard JSON payload에 감사 이력과 함께 보존한다.

## Boundaries & Constraints

**Always:** 공식 `READY` 핸드오프와 승인된 `criteria_version_id`만 사용한다. 선택된 모든 질문은 질문·현재본·연결 기준·원문 근거·서류 초기 가설·면접 결과·기록자·시각을 보존한다. 초기 가설과 면접 결과는 서로 다른 필드와 화면 영역에 둔다. 최종 결정은 `LEAD`가 명시적으로 입력하며 `채용`, `미채용`, `종료`, `인재풀 등록`만 허용한다. 결정에는 사유·행위자·시각·기준 버전 ID를 저장하고, 검증·결정 수정은 이전 값·변경 값·행위자·시각·사유를 JSON 이력에 추가한다. 모든 기록은 원문 질문·기준·근거 ID와 연결하고 감사 타임라인에서 시간순으로 읽을 수 있어야 한다.

**Ask First:** 없음.

**Never:** 미승인·불완전 카드에 검증이나 결정을 저장하지 않는다. 면접 결과가 HR·HM 판단이나 서류 가설을 자동으로 덮어쓰지 않는다. AI가 최종 결정값이나 결정 사유를 생성하지 않는다. 새 관계형 검증·결정 테이블, 점수·랭킹·자동 합격·탈락을 추가하지 않는다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | READY 카드, SELECTED 질문, LEAD의 검증 결과와 결정 | JSON payload 저장 및 비교·감사 표시 | N/A |
| MISSING_PREREQUISITE | 카드 없음/READY 아님/선택 질문 없음/검증 누락 | 저장하지 않고 누락 조건 안내 | 404/409 |
| INVALID_DECISION | 허용되지 않은 결정값 또는 빈 결정 사유 | 저장하지 않음 | 422 |
| EDIT_AUDIT | 기존 검증 또는 결정 수정 | 현재 값 갱신, 이전 기록은 JSON 이력에 보존 | 403/409/422 |

</frozen-after-approval>

## Code Map

- `backend/app/models/handoff.py` -- 검증 결과·최종 결정의 Pydantic 입력/출력 계약; 공식 결정값과 JSON 이력 필드 추가 지점.
- `backend/app/services/handoff.py` -- READY 카드 조회, 선택 질문 확인, JSON payload read-modify-write와 rowcount 검증을 재사용할 핵심 서비스 지점.
- `backend/app/api/handoff.py` -- 기존 카드 생성/조회 라우트의 역할·오류 매핑 패턴; 검증 저장과 결정 저장 라우트 연결 지점.
- `frontend/src/lib/handoff-api.ts` -- 카드 payload 타입과 검증·결정 API 요청 함수 추가 지점.
- `frontend/src/app/handoff/page.tsx` -- 질문 후보 카드 다음에 verification-comparison과 최종 결정 UI를 배치할 발표 경로.
- `backend/tests/test_handoff.py` -- 공식 카드 선행 조건과 payload 초기화 회귀 테스트; 검증·결정 게이트 테스트 확장 지점.
- `backend/tests/test_questions.py` -- SELECTED 질문 및 역할 제한 픽스처 재사용 지점.
- `frontend/src/app/handoff/page.test.tsx` -- 핸드오프 화면의 검증 입력, 공식 결정값, 실패 시 입력 보존 테스트 지점.
- `HR_data/04_internal-docs/03_스크리닝판정기준/전형_단계별_상태값.md` -- 주최측 전형 단계와 최종 공식 어휘의 읽기 전용 정본.

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/models/handoff.py` -- `InterviewVerification`, `DecisionRecord`, 입력 계약과 공식 결정값을 정의 -- JSON payload의 비교·감사 필드를 명시한다.
- [x] `backend/app/services/handoff.py` -- 선택 질문별 검증 저장/수정과 최종 결정 저장/수정을 구현 -- READY·APPROVED·LEAD·필수 검증 게이트와 원자적 JSON 이력을 보장한다.
- [x] `backend/app/api/handoff.py` -- 검증·결정 저장 라우트와 404/403/409/422 오류 계약을 연결 -- 카드 기준 버전은 서버 값만 사용한다.
- [x] `frontend/src/lib/handoff-api.ts` -- 검증 결과·최종 결정 타입과 요청 함수를 추가 -- 저장 성공/실패 응답을 화면 상태에 반영한다.
- [x] `frontend/src/app/handoff/page.tsx` -- 선택 질문별 초기 가설/면접 결과 비교와 네 가지 결정값 입력 UI를 추가 -- LEAD만 편집하고 발표 흐름에서 사람의 결정을 명시한다.
- [x] `backend/tests/test_handoff.py` -- 검증 게이트, 결과 보존, 결정 어휘, 수정 이력과 권한을 검증 -- JSON flattening과 자동 결정 금지를 회귀 방지한다.
- [x] `frontend/src/app/handoff/page.test.tsx` -- 비교 화면·결정 드롭다운·저장 요청·실패 입력 보존을 검증 -- 클릭 데모의 마지막 단계를 보호한다.

**Acceptance Criteria:**
- Given 공식 READY 핸드오프와 LEAD가 선택한 질문이 있을 때, when 질문별 검증 결과를 저장하면, then 질문 원문/현재본·기준·근거·서류 초기 가설·면접 결과·기록자·시각이 `interview_results`에 함께 저장된다.
- Given 서류 우려 또는 근거 부족 항목이 있을 때, when 검증 결과를 조회하면, then 초기 가설과 면접 결과가 다른 영역에 표시되고 HR·HM 판단은 변경되지 않는다.
- Given 선택 질문과 검증 결과가 있을 때, when LEAD가 최종 결정 화면을 열면, then 선택 질문·검증 결과·서류 가설·HR·HM 판단 근거를 한 화면에서 확인할 수 있다.
- Given 승인된 기준 버전, 공식 READY 핸드오프와 선택된 모든 질문의 검증 결과가 있을 때, when LEAD가 결정값과 사유를 저장하면, then `DecisionRecord`에 사람이 입력한 네 가지 공식 어휘 중 하나·사유·행위자·시각·`criteria_version_id`가 저장된다.
- Given 기준 미승인, 공식 카드 부재, 선택 질문 없음, 검증 결과 누락 또는 결정 사유 누락일 때, when 최종 결정을 저장하면, then 저장을 차단하고 누락 조건을 안내하며 자동 결정을 저장하지 않는다.
- Given 검증 결과와 최종 결정을 저장할 때, when MVP JSON 구조를 적용하면, then 별도 관계형 테이블 없이 HandoffCard payload에 질문·기준·근거·가설·결과·결정 연결을 보존한다.
- Given 검증 결과 또는 최종 결정이 수정될 때, when 저장이 완료되면, then 현재 값은 갱신하되 이전 값·변경 값·행위자·시각·사유를 JSON 변경 이력에 추가한다.
- Given 최종 결정이 저장되었을 때, when 감사 기록을 조회하면, then 승인 기준·핸드오프·선택 질문·초기 가설·면접 결과·최종 사람 결정을 시간순으로 확인하고 AI를 결정자로 표시하지 않는다.

## Design Notes

검증 저장 시 초기 가설은 선택 질문의 질문 이유와 연결된 카드의 근거 부족/우려를 서버에서 snapshot한다. 면접 결과는 LEAD가 입력한 사실·관찰·확인 내용을 그대로 보존한다. 모든 선택 질문에 결과가 있어야 결정 저장을 허용하며, 질문 후보가 하나도 선택되지 않은 카드도 결정 게이트에서 차단한다. 결정값은 요청 본문이 아니라 서버에서 읽은 카드의 기준 버전과 연결한다.

## Verification

**Commands:**
- `uv run --project backend --group dev pytest backend/tests -q` -- 기존 테스트와 검증·결정 게이트가 성공한다.
- `npm test -- --run` (workdir `frontend`) -- 핸드오프 비교·결정 UI 테스트가 성공한다.
- `npx tsc --noEmit` (workdir `frontend`) -- TypeScript 오류가 없다.
- `npm run build` (workdir `frontend`) -- 프로덕션 빌드가 성공한다.

## Suggested Review Order

검증 저장과 최종 결정 게이트부터 확인합니다.

1. [면접 검증·결정 게이트와 JSON 갱신](../../backend/app/services/handoff.py#L500)
2. [검증·결정 데이터 계약과 공식 어휘](../../backend/app/models/handoff.py#L86)
3. [검증·결정 API와 오류 매핑](../../backend/app/api/handoff.py#L56)
4. [초기 가설·면접 결과 비교와 결정 입력 UI](../../frontend/src/app/handoff/page.tsx#L371)
5. [프론트엔드 API 타입과 요청 함수](../../frontend/src/lib/handoff-api.ts#L57)
6. [백엔드 게이트·감사 회귀 테스트](../../backend/tests/test_handoff.py#L102)
7. [프론트엔드 클릭 흐름 테스트](../../frontend/src/app/handoff/page.test.tsx#L80)
