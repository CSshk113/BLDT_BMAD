---
title: 'Story 3.3 근거·질문 은행 기반 인터뷰 질문 후보 관리'
type: 'feature'
created: '2026-08-27'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'c571ad9662494d16f60091e3e04ed0936f3a1775'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-3-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-3-2-generate-json-handoff-card.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** 핸드오프 카드가 근거 부족 항목과 검토자 우려를 담아도, 인터뷰에서 무엇을 확인할지 사람이 다시 처음부터 만들어야 한다.

**Approach:** 공식 핸드오프의 기준·근거·우려를 입력으로 삼고 `HR_data`의 관련 question-bank 실제 사용 이력을 Few-shot으로 선별해 `gpt-5.6-luna` 질문 후보를 생성한다. 후보는 HandoffCard의 JSON payload에 저장하고 사람이 수정·삭제·선택한다.

## Boundaries & Constraints

**Always:** 승인된 핸드오프 카드만 질문 생성 대상이다. 생성 프롬프트에는 현재 카드의 기준·원문 근거·근거 부족·검토자 우려와 관련 직군의 실제 질문·의도·평가 포인트를 포함한다. 후보마다 원질문, 현재 질문, 질문 이유, 연결 기준·근거, 질문 유형, 상태(`CANDIDATE`, `SELECTED`, `DELETED`), 생성 시각을 보존한다. 수정 시 원질문과 행위자·시각·사유를 edit history에 남기고, 삭제는 soft delete한다. 질문은 구체적·검증 가능·비유도적·공정하고 중복이 적어야 하며 현재 카드에 없는 사실, 보호 특성·사생활, 자동 합격·탈락 판단을 포함하지 않는다. 모델은 `gpt-5.6-luna`를 사용하고 API 키·base URL은 서버 환경변수에서만 읽는다. 정확한 후보 개수는 고정하지 않는다.

**Ask First:** 없음.

**Never:** 미승인·불완전 핸드오프에서 후보를 만들지 않는다. 무관한 직군의 question-bank 예시를 Few-shot으로 무차별 주입하지 않는다. AI가 후보를 자동 선택하거나 최종 결정을 내리지 않는다. 질문 후보용 별도 관계형 테이블을 만들지 않는다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | READY 카드, 근거, 관련 question-bank, LLM 응답 | 후보를 JSON payload에 저장하고 조회 가능 | N/A |
| MISSING_GATE | 카드가 없거나 PROCESSING/FAILED | 후보를 저장하지 않음 | HTTP 409 |
| MODEL_UNAVAILABLE | API 키·모델 응답·JSON 형식 오류 | 부분 후보를 저장하지 않음 | HTTP 503/502 |
| EDIT_DELETE_SELECT | 후보 목록과 역할별 요청 | 수정 이력 보존, DELETED 숨김, SELECTED만 선택 목록에 표시 | 권한/상태 오류 |

</frozen-after-approval>

## Code Map

- `backend/app/services/handoff.py` -- Story 3.2 카드 조회·JSON payload 저장·상태 계약; 질문 배열의 원자적 갱신 지점.
- `backend/app/models/handoff.py` -- 카드 응답과 payload 타입; 후보 객체 계약 확장 지점.
- `backend/app/api/handoff.py` -- 카드 권한·오류 처리 패턴; 질문 생성/조회 라우트 연결 지점.
- `HR_data/04_internal-docs/05_면접설계/question-bank/영업/*.md` -- B2B 영업 역량별 실제 사용 질문·의도·평가 포인트·후속 질문.
- `HR_data/04_internal-docs/05_면접설계/question_types.md` -- 질문 유형 분류 기준.
- `HR_data/04_internal-docs/05_면접설계/structured_interview_framework.md` -- 행동·상황 질문의 검증 구조.
- `HR_data/04_internal-docs/05_면접설계/competency_framework.md` -- 기준과 역량 연결에 사용할 어휘.
- `frontend/src/app/handoff/page.tsx` -- Story 3.2 카드 화면; 질문 생성·수정·삭제·선택 UI를 추가할 발표 경로.
- `frontend/src/lib/handoff-api.ts` -- 카드 API 요청 타입; 질문 API 요청 계약 확장 지점.

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/services/questions.py` -- question-bank를 역량·직군 기준으로 선별하고 gpt-5.6-luna Few-shot 요청·JSON 검증을 구현 -- 근거 연결과 안전한 실패를 보장한다.
- [x] `backend/app/models/handoff.py` -- 질문 후보·생성 응답·수정 입력 계약을 정의 -- 원질문과 현재본, 상태, 이력을 구분한다.
- [x] `backend/app/services/handoff.py` -- payload의 질문 후보 생성·조회·수정·soft delete·선택을 원자적으로 구현 -- 별도 질문 테이블 없이 카드와 함께 보존한다.
- [x] `backend/app/api/questions.py` -- 생성·목록·수정·삭제·선택 API와 역할/오류 계약을 연결 -- HR/HM 수정과 LEAD 선택을 통제한다.
- [x] `backend/app/main.py` -- 질문 라우터를 기존 FastAPI 앱에 연결 -- Story 3.2 API 호환을 유지한다.
- [x] `frontend/src/lib/handoff-api.ts` -- 질문 후보 API 타입과 요청 함수를 추가 -- 생성·수정·삭제·선택 상태를 전달한다.
- [x] `frontend/src/app/handoff/page.tsx` -- 질문 후보를 표시하고 생성·수정·삭제·선택 인터랙션을 구현 -- 90초 발표 흐름의 마지막 단계를 완성한다.
- [x] `backend/tests/test_questions.py` -- Few-shot 선별, 게이트, 모델 실패, CRUD·권한·soft delete를 검증 -- 매트릭스와 AC를 회귀 방지한다.

**Acceptance Criteria:**
- Given READY 핸드오프 카드가 있을 때, when 질문 생성을 요청하면, then 카드의 기준·근거·우려와 관련 영업 question-bank 실제 사용 이력을 Few-shot으로 포함한 `gpt-5.6-luna` 요청을 시도하고 후보를 `interview_questions`에 저장한다.
- Given 생성 응답이 있을 때, when 후보를 조회하면, then 질문·이유·연결 기준·참조 근거·질문 유형·선택 상태·생성 시각을 함께 표시한다.
- Given 후보가 품질 기준을 위반하거나 현재 카드 근거와 연결되지 않을 때, when 저장하면, then 해당 후보를 저장하지 않고 위반 사유를 반환한다.
- Given HR 또는 HM이 후보를 수정할 때, when 저장하면, then 현재 질문만 바뀌고 원질문·변경 사유·행위자·시각이 edit history에 보존된다.
- Given HR 또는 HM이 후보를 삭제할 때, when 목록을 조회하면, then 후보는 `DELETED`로 보존되지만 기본 목록과 선택 목록에서 숨겨진다.
- Given LEAD가 후보를 선택하거나 선택 해제할 때, when 핸드오프를 조회하면, then `SELECTED` 후보만 인터뷰 사용 목록으로 표시되고 자동 최종 결정은 생성되지 않는다.
- Given API 키가 없거나 모델 응답이 실패할 때, when 생성을 요청하면, then 카드 payload에 부분 후보를 저장하지 않고 재시도 가능한 오류를 반환한다.

## Design Notes

question-bank는 현재 카드의 기준 텍스트·근거 부족 항목·우려와 키워드가 겹치는 영업 역량 파일만 Few-shot으로 선별한다. LLM 응답은 구조화된 후보 배열로 받고, 후보의 기준 ID와 근거 ID가 카드 입력에 존재하는지 서버에서 확인한다. 후보 수는 고정하지 않으며 생성 실패 시 기존 후보를 덮어쓰지 않는다.

## Verification

**Commands:**
- `uv run --project backend --group dev pytest backend/tests -q` -- 질문 생성·CRUD와 기존 백엔드 테스트가 성공한다.
- `npm test -- --run` (workdir `frontend`) -- 기존 및 질문 UI 테스트가 성공한다.
- `npx tsc --noEmit` (workdir `frontend`) -- TypeScript 오류가 없다.
- `npm run build` (workdir `frontend`) -- 프로덕션 빌드가 성공한다.

## Suggested Review Order

생성·검증 핵심 로직부터 확인합니다.

1. [질문 생성·question-bank 선별·검증](../../backend/app/services/questions.py#L90)
2. [핸드오프 JSON payload 원자적 갱신과 역할 제어](../../backend/app/services/handoff.py#L265)
3. [질문 API 라우트와 오류 매핑](../../backend/app/api/questions.py#L26)
4. [후보 데이터 계약](../../backend/app/models/handoff.py#L47)
5. [핸드오프 화면의 질문 후보 흐름](../../frontend/src/app/handoff/page.tsx#L36)
6. [프론트엔드 API 타입·요청 함수](../../frontend/src/lib/handoff-api.ts#L29)
7. [백엔드 회귀 테스트](../../backend/tests/test_questions.py#L75)
8. [프론트엔드 인터랙션 테스트](../../frontend/src/app/handoff/page.test.tsx#L59)
