---
title: 'Story 2.3 - 스플릿 뷰와 텍스트 검색 하이라이트'
type: 'feature'
created: '2026-08-27'
status: 'done'
review_loop_iteration: 0
baseline_commit: '71a507769b47f2b8483874f0c9c808e96cf3f2ed'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-2-2-map-criteria-to-source-citations.md'

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Story 2.2의 기준별 인용구는 표시되지만 지원서 원문과 같은 화면에서 대조하거나 실제 문맥으로 이동할 수 없다.

**Approach:** 완료된 매핑 결과와 동일 실행의 정규화 Markdown을 불러와 왼쪽 원문·오른쪽 근거 카드의 독립 스크롤 스플릿 뷰를 제공한다. 근거 카드를 선택하면 원문 문자열을 검색하고 하이라이트하며, 좌표가 없거나 문자열이 불일치하면 fallback 문맥과 명시적인 실패 상태를 보여준다.

## Boundaries & Constraints

**Always:** 지원서 ID·기준 버전·처리 실행 컨텍스트를 화면 상단에 함께 표시한다. 원문 검색은 정규화 Markdown의 실제 부분 문자열만 대상으로 하며 `active_citation_id`와 선택 상태를 유지한다. 키보드 Enter/Space 선택을 지원하고 결과를 `aria-live="polite"`로 알린다. 근거 상태는 `충족`, `부분 충족`, `미충족`, `확인 불가`를 그대로 표시한다.

**Ask First:** 없음.

**Never:** PDF 좌표를 계산한 것처럼 가장하지 않는다. 일치하지 않는 다른 텍스트를 하이라이트하거나 성공으로 표시하지 않는다. 점수·순위·확률·자동 합격/탈락 및 핸드오프 기능을 추가하지 않는다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 정상 대조 | 완료 실행, 매핑 결과, Markdown | 좌측 원문과 우측 카드가 같은 실행·기준으로 표시되고 카드 선택 시 해당 문자열이 하이라이트됨 | N/A |
| 좌표 없음 | citation과 fallback 문맥, 좌표 없음 | `문맥 보기`와 fallback을 표시하고 문자열 검색으로 대조 | 좌표 오류로 표시하지 않음 |
| 문자열 불일치 | 저장된 citation이 viewer 원문에 없음 | 하이라이트하지 않고 `원문 일치 실패`와 사용 가능한 snippet/context를 표시 | 실패 상태를 aria-live로 알림 |
| 준비 안 됨 | 매핑 또는 완료 Markdown 없음 | 검토 화면을 만들지 않고 준비 상태 안내 | API 오류를 사용자 메시지로 변환 |

</frozen-after-approval>

## Code Map

- `backend/app/models/applications.py` -- 정규화 Markdown을 브라우저에 전달할 응답 계약 추가 지점
- `backend/app/services/applications.py:254` -- 완료된 실행의 현재 `NORMALIZED_MARKDOWN`을 선택·읽는 서비스 재사용 지점
- `backend/app/api/applications.py:20` -- 지원서 문서 조회 API 라우트 추가 지점
- `frontend/src/lib/applications-api.ts:90` -- 문서 조회 타입과 호출 함수 추가 지점
- `frontend/src/lib/mapping-api.ts:48` -- Story 2.2 매핑 조회 계약과 실행 ID 재사용 지점
- `frontend/src/components/criteria/MappingResults.tsx:11` -- 근거 카드의 상태·citation·fallback 표시 및 상호작용 확장 지점
- `frontend/src/app/evidence/page.tsx` -- 신규 실제 클릭 데모 진입점으로 스플릿 뷰 연결
- `frontend/src/components/criteria/evidence-split-view.test.tsx`, `backend/tests/test_applications.py` -- 선택·하이라이트·불일치 및 문서 API 회귀 검증 지점

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/models/applications.py`, `backend/app/services/applications.py` -- 동일한 완료 실행의 현재 Markdown을 읽어 문서 내용과 추적 ID를 반환하는 서비스 계약을 추가한다 -- 서버 경로는 노출하지 않고 매핑과 원문 실행을 정렬한다.
- [x] `backend/app/api/applications.py`, `backend/tests/test_applications.py` -- 지원서 문서 조회 API와 완료/미완료·누락 산출물 오류를 구현하고 검증한다 -- 검토 가능한 원문만 제공한다.
- [x] `frontend/src/lib/applications-api.ts` -- 문서 조회 타입과 API 호출을 추가한다 -- 기존 매핑 응답의 `processing_run_id`와 같은 실행을 요청한다.
- [x] `frontend/src/components/criteria/MappingResults.tsx`, `frontend/src/components/criteria/EvidenceSplitView.tsx` -- 카드 선택, `active_citation_id`, native `window.find()` 시도와 문자열 하이라이트 fallback, 독립 스크롤, 키보드 조작, match-failure 안내를 구현한다 -- 잘못된 하이라이트를 막는다.
- [x] `frontend/src/app/evidence/page.tsx`, `frontend/src/app/applications/page.tsx` -- 지원서 ID·기준 버전으로 매핑과 문서를 불러오는 검토 화면을 만들고 완료 지원서에서 진입 링크를 연결한다 -- 실제 데모 클릭 흐름을 완성한다.
- [x] `frontend/src/components/criteria/evidence-split-view.test.tsx` -- 정상 선택·키보드·불일치 fallback과 접근성 알림을 검증한다 -- Story 2.3 회귀를 막는다.

**Acceptance Criteria:**
- Given 완료된 지원서와 기준별 매핑 결과가 있을 때, when HM이 검토 화면을 열면, then 왼쪽에 Markdown 원문, 오른쪽에 기준·인용구·상태·위치 카드와 동일한 지원서/기준/실행 컨텍스트가 표시되어야 한다.
- Given 오른쪽 카드에 정규화 Markdown citation이 있을 때, when HM이 클릭하거나 Enter/Space를 누르면, then `active_citation_id`가 바뀌고 같은 문자열만 왼쪽에서 검색·포커스·하이라이트되어야 한다.
- Given PDF 좌표가 없을 때, when 카드를 선택하면, then `문맥 보기` fallback과 snippet/page/context를 표시하고 좌표 계산 성공처럼 표현하지 않아야 한다.
- Given 저장된 citation이 viewer 원문과 일치하지 않을 때, when 카드를 선택하면, then 다른 텍스트를 하이라이트하지 않고 `원문 일치 실패`와 사용 가능한 fallback을 표시·알려야 한다.
- Given 두 패널을 스크롤하거나 카드를 키보드로 조작할 때, when 상태가 변경되면, then 패널은 독립적으로 스크롤되고 선택 상태와 진행 중 입력을 유지하며 상태 알림은 비시각 사용자에게도 전달되어야 한다.
- Given 매핑 상태를 표시할 때, when HM이 결과를 확인하면, then `충족`, `부분 충족`, `미충족`, `확인 불가`만 사용하고 종합 점수·랭킹·자동 판정을 제공하지 않아야 한다.

## Design Notes

- 브라우저의 `window.find()`는 가능한 경우 원문 위치를 네이티브 검색하고, 시각적 일관성을 위해 정확한 부분 문자열 확인 후 `<mark>`를 렌더링한다. 문자열이 없으면 검색 성공으로 간주하지 않는다.
- PDF 원문 직접 렌더링은 이번 스토리의 기본 경로가 아니다. Story 2.1이 저장한 정규화 Markdown을 viewer의 단일 진실 공급원으로 사용한다.

## Verification

**Commands:**
- `uv run --project backend --group dev pytest` -- expected: 문서 조회와 기존 백엔드 회귀 테스트 통과
- `npm test` (from `frontend`) -- expected: 스플릿 뷰 선택·불일치·접근성 테스트 통과
- `npx tsc --noEmit` (from `frontend`) -- expected: TypeScript 오류 없음
- `npm run build` (from `frontend`) -- expected: Next.js production build succeeds

## Suggested Review Order

**실행 정합성과 원문 API**

- 완료 실행의 현재 Markdown만 반환하고 서버 경로는 숨긴다.
  [`applications.py:268`](../../backend/app/services/applications.py#L268)

- 문서 조회 경계에서 완료 상태와 산출물 누락을 명시적으로 차단한다.
  [`applications.py:286`](../../backend/app/services/applications.py#L286)

- API가 문서 계약과 준비 오류를 HTTP 상태로 전달한다.
  [`applications.py:27`](../../backend/app/api/applications.py#L27)

**원문 대조 UX**

- 카드 선택과 문자열 일치 여부를 스플릿 뷰 상태로 연결한다.
  [`EvidenceSplitView.tsx:23`](../../frontend/src/components/criteria/EvidenceSplitView.tsx#L23)

- 정확한 citation만 mark 처리하고 실패 시 이전 네이티브 선택도 제거한다.
  [`EvidenceSplitView.tsx:36`](../../frontend/src/components/criteria/EvidenceSplitView.tsx#L36)

- 기준별 근거 카드에 클릭·키보드·활성 상태를 제공한다.
  [`MappingResults.tsx:11`](../../frontend/src/components/criteria/MappingResults.tsx#L11)

**진입 경로와 회귀 검증**

- 완료 지원서에서 실행 ID를 보존해 검토 화면으로 이동한다.
  [`page.tsx:40`](../../frontend/src/app/applications/page.tsx#L40)

- 매핑과 원문을 함께 불러오고 실행·artifact 불일치 시 검토를 중단한다.
  [`page.tsx:27`](../../frontend/src/app/evidence/page.tsx#L27)

- 정상 하이라이트·불일치·빈 근거 상태를 검증한다.
  [`evidence-split-view.test.tsx:40`](../../frontend/src/components/criteria/evidence-split-view.test.tsx#L40)

- 문서 API의 완료·미완료 처리와 전체 백엔드 회귀를 검증한다.
  [`test_applications.py:145`](../../backend/tests/test_applications.py#L145)
