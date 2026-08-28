---
title: 'Story 2.1 - 기존 PDF 표본 처리 시작'
type: 'feature'
created: '2026-08-28'
status: 'done'
review_loop_iteration: 0
baseline_commit: '420d1dd23af21663d2610173924a9dcf118e07fa'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-2-1-pdf-upload-and-llamaparse-markdown-conversion.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** PDF 표본은 서버에 원본 산출물로 등록돼 있어도 처리 실행이 없으면 화면에서 `처리 대기`로만 보인다. 현재 UI는 실패한 지원서에만 `다시 처리`를 제공하므로, `APPS-179` 같은 기존 표본을 재업로드 없이 LlamaParse 파이프라인에 넣을 수 없다.

**Approach:** 현재 원본 PDF가 있는 미처리 `SAMPLE` 지원서의 상세 화면에 `처리 시작`을 제공하고, 기존 재처리 API를 재사용한다. 처리 시작은 같은 지원서 ID에 새 실행을 만들며, 성공·실패 상태와 기존 산출물 보존 규칙은 기존 파이프라인을 그대로 따른다.

## Boundaries & Constraints

**Always:** `SAMPLE`이고 현재 `ORIGINAL_PDF` 산출물이 있으며 처리 상태가 없을 때만 `처리 시작`을 보인다. 시작 요청은 기존 `POST /api/applications/{application_id}/process`를 사용한다. 처리 중 생성된 Markdown·정규화 Markdown은 원본과 같은 지원서·새 실행 ID에 연결한다. `FAILED` 상태에는 기존 `다시 처리`를 유지한다. 화면 갱신 후 최신 상태와 산출물을 표시한다.

**Ask First:** 처리 시작을 비동기 작업 큐로 바꾸거나, 동시 요청 차단을 서버에 추가하거나, 표본 이외의 원장 후보에 원본 PDF를 연결하려면 먼저 승인받는다.

**Never:** 원본 PDF를 다시 업로드하거나 새 `UPLOAD-*` 지원서를 만들지 않는다. `LEDGER_ONLY` 지원서를 처리 대상으로 만들지 않는다. 파서 API 키·서버 파일 경로를 브라우저에 노출하지 않는다. 미완료·실패 결과를 완료된 근거처럼 표시하지 않는다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|----------------------------|----------------|
| 표본 최초 처리 | `SAMPLE`, 현재 `ORIGINAL_PDF`, 처리 실행 없음 | `처리 시작`을 누르면 같은 지원서에 새 실행을 만들고 완료 후 산출물·검토 진입점을 갱신한다 | 파서 실패 시 기존 단계·실패 사유를 표시한다 |
| 실패 재시도 | `FAILED`, 현재 원본 PDF | `다시 처리`를 유지하고 새 실행을 만든다 | 이전 성공 산출물은 유지한다 |
| 처리 불가 후보 | `LEDGER_ONLY` 또는 현재 원본 PDF 없음 | 시작 버튼을 노출하지 않는다 | 원장 데이터만 있음 상태를 유지한다 |

</frozen-after-approval>

## Code Map

- `frontend/src/app/applications/page.tsx:34` -- 기존 `reprocessApplication` 호출을 처리 시작과 재처리가 함께 재사용하는 UI 진입점
- `frontend/src/app/applications/page.tsx:40` -- 선택 지원서의 상태·현재 산출물에 따라 액션 버튼을 조건부로 표시하는 상세 화면
- `frontend/src/lib/applications-api.ts:124` -- 기존 지원서 ID를 유지한 처리 요청 API. 변경하지 않는다.
- `backend/app/api/applications.py:37` -- 기존 처리 시작 API 경계. 변경하지 않는다.
- `backend/app/services/applications.py:365` -- 현재 원본 PDF를 LlamaParse Markdown과 정규화 Markdown으로 변환하는 상태 전이 경계. 변경하지 않는다.
- `backend/app/services/applications.py:436` -- 새 실행을 만들고 동일 지원서의 현재 원본 PDF를 처리하는 재사용 서비스
- `frontend/src/app/applications/page.test.tsx:1` -- 상세 화면의 `처리 시작`·`다시 처리` 분기와 API 호출을 검증할 테스트
- `backend/tests/test_applications.py:98` -- 기존 원본 PDF 기반 실행과 실패 보존 계약을 확인하는 회귀 테스트

## Tasks & Acceptance

**Execution:**

- [x] `frontend/src/app/applications/page.tsx` -- 미처리 표본의 현재 원본 PDF 존재 여부를 확인해 `처리 시작`을 표시하고 기존 처리 요청·목록 갱신 함수를 재사용한다 -- 재업로드 없이 동일 지원서 파싱을 가능하게 한다.
- [x] `frontend/src/app/applications/page.test.tsx` -- 최초 처리 가능 표본, 실패 재시도, 원장 전용/원본 없는 표본의 버튼 분기를 검증한다 -- 처리 대상 경계를 고정한다.
- [x] `backend/tests/test_applications.py` -- 기존 원본 PDF만 있는 지원서가 동일 ID의 새 실행으로 처리되는 회귀를 검증한다 -- UI가 호출하는 기존 API 계약을 보장한다.

**Acceptance Criteria:**

- Given 현재 `ORIGINAL_PDF`가 있고 처리 실행이 없는 `SAMPLE` 지원서가 선택됐을 때, when 화면을 열면, then `처리 시작` 버튼이 표시돼야 한다.
- Given HR이 `처리 시작`을 누를 때, when 기존 처리 API가 성공하면, then 새 `UPLOAD-*` 지원서 없이 기존 지원서 ID에 실행·Markdown·정규화 Markdown이 연결되고 화면이 갱신돼야 한다.
- Given 처리 시작이 파서 단계에서 실패할 때, when 결과를 조회하면, then `FAILED` 단계와 사유가 표시되고 완료된 근거로 이동할 수 없어야 한다.
- Given `FAILED` 지원서일 때, when 상세를 열면, then `처리 시작` 대신 기존 `다시 처리`가 표시돼야 한다.
- Given `LEDGER_ONLY` 또는 현재 원본 PDF가 없는 지원서일 때, when 상세를 열면, then 처리 시작·재처리 버튼이 표시되지 않아야 한다.

## Spec Change Log

## Design Notes

- 처리 실행 생성은 이미 서버에서 원본 PDF의 `storage_path`를 찾고 새 `run_id`를 만드는 경계에 있다. UI는 이 경계를 새로 구현하지 않고 상태별 호출 권한만 제공한다.
- 버튼 노출은 목록 요약의 산출물 타입이 아니라 상세의 `artifacts`에서 현재 `ORIGINAL_PDF`를 확인한다. 이전 실행 산출물과 목록 캐시가 섞여 잘못된 시작 버튼이 나타나는 것을 막는다.

## Verification

**Commands:**

- `npm test -- --run src/app/applications/page.test.tsx` (from `frontend`) -- expected: 최초 처리·실패 재시도·처리 불가 지원서의 버튼 분기와 API 호출 통과
- `backend/.venv/bin/pytest backend/tests/test_applications.py -q` -- expected: 기존 원본 PDF 처리와 실패 보존 회귀 통과
- `npm run build` (from `frontend`) -- expected: Next.js production build succeeds

**Manual checks:**

- `APPS-179`를 선택해 `처리 시작`을 누르고, 새 업로드 ID 없이 `RECEIVED → PARSING → MAPPING → COMPLETED` 또는 명시적 실패 상태가 표시되는지 확인한다.

## Suggested Review Order

**처리 시작 상태 제어**

- 현재 원본 PDF가 있는 표본만 기존 처리 경계로 연결한다.
  [`page.tsx:48`](../../frontend/src/app/applications/page.tsx#L48)

- 선택 변경 중 이전 요청 응답이 상세 화면을 되돌리지 않게 한다.
  [`page.tsx:28`](../../frontend/src/app/applications/page.tsx#L28)

- 최초 처리·재시도 버튼을 상태와 현재 산출물로 분리한다.
  [`page.tsx:67`](../../frontend/src/app/applications/page.tsx#L67)

**회귀 검증**

- 성공·실패·원장 전용·중복 클릭의 화면 분기를 검증한다.
  [`page.test.tsx:72`](../../frontend/src/app/applications/page.test.tsx#L72)

- 기존 PDF 표본이 같은 지원서 ID에서 새 실행을 만드는지 검증한다.
  [`test_applications.py:135`](../../backend/tests/test_applications.py#L135)
