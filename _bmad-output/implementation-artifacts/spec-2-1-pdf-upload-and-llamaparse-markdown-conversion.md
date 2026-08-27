---
title: 'Story 2.1 - PDF 업로드와 LlamaParse Markdown 변환'
type: 'feature'
created: '2026-08-27'
status: 'done'
review_loop_iteration: 0
baseline_commit: '773c172f0c119ecb578d528034e21922469e25a5'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/epics.md'
  - '{project-root}/HR_data/00_README.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** 현재 MVP에는 PDF 지원서를 원본과 변환 산출물로 연결하고 처리 상태를 추적하는 입력 파이프라인이 없다. 따라서 이후 기준별 근거 매핑이 어떤 문서와 실행에서 나온 것인지 확인할 수 없다.

**Approach:** 서버가 PDF만 접수해 지원서·처리 실행·원본 파일을 먼저 연결하고, 서버 환경변수의 LlamaParse 연동을 통해 Markdown과 정규화 Markdown을 저장한다. 처리 목록에서는 178건 원장과 20건 비식별 PDF 표본을 구분하고, 표본 매핑표의 후보 토큰으로 원장 메타데이터를 연결한다.

## Boundaries & Constraints

**Always:** PDF 형식은 레코드 생성 전에 검증한다. 처리 상태는 `RECEIVED → PARSING → MAPPING → COMPLETED` 또는 `FAILED`로 기록하고 현재 단계·시각·실패 사유를 보존한다. 원본 PDF, LlamaParse Markdown, 정규화 Markdown과 처리 실행 ID를 같은 지원서에 연결한다. 재처리 실패 시 기존 마지막 성공 산출물을 덮어쓰지 않는다. 파서 키와 파일 경로는 서버 환경변수 또는 `.env`에서만 사용한다.

**Ask First:** 없음. 외부 LlamaParse 호출은 테스트에서 주입 가능한 파서 경계로 대체할 수 있으며, 실제 호출 설정이 없으면 명확한 실패 상태를 표시한다.

**Never:** DOCX 등 비-PDF 파일을 처리하지 않는다. 178건 전체 원문의 실시간 파싱을 MVP 성공 조건으로 만들지 않는다. 브라우저에 LlamaParse 키를 노출하지 않는다. `PARSING`, `MAPPING`, `FAILED` 산출물을 완료된 근거처럼 표시하지 않는다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| PDF 업로드 | 비식별 PDF, 후보 식별자, 포지션, 기준 버전 | 지원서·실행 레코드와 원본 저장, `RECEIVED` 표시 | 필수 메타데이터 오류는 422 |
| 비-PDF 제출 | DOCX 또는 임의 파일 | 처리 요청을 만들지 않음 | 415와 PDF 전용 안내 |
| 변환 성공 | 저장된 PDF, LlamaParse 응답 | `PARSING` 후 Markdown·정규화 Markdown 저장, 완료 시각과 `COMPLETED` 기록 | N/A |
| 변환 실패 | 파서 오류 또는 키 미설정 | `FAILED`, 실패 단계·사유 표시, 이전 성공 산출물 보존 | 502 또는 처리 실패 응답 |
| 원장 전용 후보 | 원장에는 있으나 PDF 표본 없음 | `원장 데이터만 있음`, 파싱 대상에서 제외 | PDF 업로드 전까지 근거 검토 차단 |

</frozen-after-approval>

## Code Map

- `backend/app/db.py` -- 지원서, 파일 산출물, 처리 실행과 상태를 저장할 SQLite 스키마 경계
- `backend/app/models/applications.py` -- 업로드·처리 상태·원장 메타데이터의 Pydantic 계약
- `backend/app/services/llamaparse.py` -- 서버 전용 LlamaParse 어댑터와 주입 가능한 파서 인터페이스
- `backend/app/services/applications.py` -- PDF 검증, 원본 저장, 파이프라인 상태 전이, 실패·재처리 보존 규칙
- `backend/app/api/applications.py` -- multipart 업로드와 처리 목록·상세 조회 API
- `backend/app/main.py` -- 애플리케이션 라우터 등록과 업로드 API 경계
- `frontend/src/app/applications/page.tsx` -- PDF 업로드, 처리 목록, 표본·원장 상태 표시 화면
- `frontend/src/components/applications/UploadForm.tsx` -- PDF 형식 검증과 메타데이터 입력 UI
- `frontend/src/components/applications/ProcessingList.tsx` -- 처리 단계·실패 사유·마지막 성공 산출물 표시
- `HR_data/01_ledger/지원접수원장_178건.csv`, `HR_data/03_resumes/표본매핑표.csv` -- 데모 목록과 후보 토큰 조인 기준
- `backend/tests/test_applications.py`, `frontend/src/app/applications/page.test.tsx` -- 업로드·상태·원장/표본 경계 검증

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/db.py`, `backend/app/models/applications.py` -- 지원서·산출물·처리 실행 계약과 상태 저장 구조를 추가 -- 원본과 Markdown의 추적성을 보장한다.
- [x] `backend/app/services/llamaparse.py`, `backend/app/services/applications.py` -- 서버 전용 파서 경계와 PDF 처리 파이프라인을 구현 -- 성공 산출물 보존과 실패 상태를 보장한다.
- [x] `backend/app/api/applications.py`, `backend/app/main.py` -- multipart 업로드와 처리 목록·상세 API를 연결 -- 비-PDF와 미완료 결과의 노출을 차단한다.
- [x] `frontend/src/app/applications/page.tsx`, `frontend/src/components/applications/UploadForm.tsx`, `frontend/src/components/applications/ProcessingList.tsx` -- 실제 업로드·처리 상태·원장 전용 표본 상태를 표시한다.
- [x] `backend/tests/test_applications.py`, `frontend/src/components/applications/applications.test.tsx` -- 정상·실패·비-PDF·원장 전용 시나리오를 검증한다.

**Acceptance Criteria:**
- Given PDF와 후보 식별자·포지션·기준 버전이 주어졌을 때, when HR이 제출하면, then 원본 PDF와 지원서·처리 실행·`criteria_version_id`가 연결된다.
- Given 비-PDF 파일을 선택했을 때, when 업로드를 제출하면, then 제출 전에 오류를 표시하고 처리 레코드나 부분 결과를 만들지 않는다.
- Given 유효한 PDF가 접수됐을 때, when 서버 파이프라인이 실행되면, then `RECEIVED → PARSING → MAPPING → COMPLETED`와 각 단계의 상태 정보를 목록에서 확인할 수 있다.
- Given LlamaParse 변환이 완료됐을 때, when 실행이 성공하면, then 원본 PDF와 동일 지원서에 Markdown·정규화 Markdown이 연결된다.
- Given 변환 또는 처리 단계가 실패했을 때, when 결과를 조회하면, then `FAILED`와 실패 단계·사유가 표시되고 이전 성공 산출물은 보존된다.
- Given 원장에만 존재하는 후보일 때, when 처리 목록을 열면, then `원장 데이터만 있음`으로 표시되고 PDF 파싱 대상으로 제공되지 않는다.
- Given 표본 매핑표와 원장 행이 모두 존재할 때, when 표본을 조회하면, then 후보 토큰으로 원장 이름·채널·포지션·지원일·판정 메타데이터가 연결된다.

## Spec Change Log

## Design Notes

- 파서 호출부와 저장·상태 전이부를 분리해 실제 LlamaParse 호출과 테스트용 가짜 파서를 같은 계약으로 다룬다. 브라우저는 업로드 API만 호출하며 키와 서버 파일 경로를 받지 않는다.
- 재처리는 새 처리 실행으로 기록하고 성공 산출물만 현재 결과로 승격한다. 실패한 실행은 실패 사유와 함께 남겨 데모 목록에서 완료 결과와 구분한다.

## Verification

**Commands:**
- `uv run --project backend --group dev pytest backend/tests/test_applications.py backend/tests/test_criteria_approval.py` -- expected: 업로드·파싱 상태와 기존 승인 회귀 테스트 통과
- `npm test` (from `frontend`) -- expected: 업로드·처리 목록과 기존 프론트 테스트 통과
- `npm run build` (from `frontend`) -- expected: Next.js production build succeeds

## Suggested Review Order

**처리 경계와 상태 보존**

- 업로드 입력과 재처리 진입점에서 PDF·메타데이터를 검증하고 실행을 연결한다.
  [`applications.py:35`](../../backend/app/api/applications.py#L35)

- 서버 전용 서비스가 원본·실행·Markdown 산출물과 실패 보존 규칙을 조정한다.
  [`applications.py:319`](../../backend/app/services/applications.py#L319)

- LlamaParse 호출을 환경변수 기반 어댑터로 격리해 브라우저 키 노출을 막는다.
  [`llamaparse.py:57`](../../backend/app/services/llamaparse.py#L57)

**저장 무결성**

- 처리 실행과 산출물의 애플리케이션·기준 버전 교차 연결을 데이터베이스에서 차단한다.
  [`db.py:127`](../../backend/app/db.py#L127)

**데모 화면과 검증**

- 실제 업로드 폼이 처리 목록과 상세 상태 화면으로 연결된다.
  [`page.tsx:14`](../../frontend/src/app/applications/page.tsx#L14)

- 클라이언트는 PDF 선택과 서버 업로드만 담당하고 파서 비밀값은 받지 않는다.
  [`UploadForm.tsx:14`](../../frontend/src/components/applications/UploadForm.tsx#L14)

- 원장 178건·표본 20건 조인과 성공·실패·재처리 보존을 백엔드 테스트로 확인한다.
  [`test_applications.py:52`](../../backend/tests/test_applications.py#L52)

- LlamaParse 응답 추출과 실제 페이지 데이터 바인딩을 프론트·어댑터 테스트로 확인한다.
  [`test_llamaparse.py:18`](../../backend/tests/test_llamaparse.py#L18)
  [`page.test.tsx:32`](../../frontend/src/app/applications/page.test.tsx#L32)
