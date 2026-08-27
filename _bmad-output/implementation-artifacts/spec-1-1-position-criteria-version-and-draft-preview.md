---
title: 'Story 1.1 - 포지션 기준 버전 확인 및 Draft 미리보기'
type: 'feature'
created: '2026-08-27'
status: 'done'
baseline_commit: 'ef149ca4c01eb1f58a6a74657287ea8ee688a93d'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-Zero100_Builderthon-2026-08-26/ARCHITECTURE-SPINE.md'
  - '{project-root}/_bmad-output/planning-artifacts/ux-designs/ux-Zero100_Builderthon-2026-08-27/DESIGN.md'
  - '{project-root}/HR_data/04_internal-docs/04_공고게시가이드/JD원문/2026-08-12_B2B영업매니저_5년이상_JD.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** 채용 담당자가 적용 중인 포지션 기준과 버전을 확인하기 어렵고, 리더 승인 전에도 기준을 탐색할 수 있는 안전한 경로가 없다.

**Approach:** B2B 영업 매니저 기준 버전을 조회·수정·복제할 수 있는 기준 관리 화면과 API를 제공한다. Draft 기준의 기존 매핑 결과는 `미리보기`로만 노출하고, 공식 핸드오프와 최종 결정은 서버와 UI에서 차단한다.

## Boundaries & Constraints

**Always:** 데모 포지션은 `B2B 영업 매니저 5년 이상 ver.4`다. 기준 버전에는 고유 ID, 필수·우대 기준, `DRAFT`/`APPROVED`/`ARCHIVED` 상태, 생성·수정 정보를 보존한다. Draft 요건 텍스트가 변경되면 해당 버전의 기존 매핑을 `INVALIDATED`로 처리하고 재실행이 필요하다는 안내를 제공한다. 모든 공식 행동은 서버가 기준 상태를 다시 검증한다.

**Ask First:** 없음.

**Never:** 미승인 기준으로 공식 핸드오프나 최종 결정을 저장하지 않는다. 자동 합격·탈락, 점수, 순위, 합격 확률을 만들지 않는다. 기존 매핑 결과를 변경된 기준에 조용히 재사용하거나 덮어쓰지 않는다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | HR이 기준 목록에서 현재 Draft를 열고 저장 | 버전·기준·상태·수정 정보 표시, 변경 시 새 결과가 Draft에 연결됨 | 저장 성공 메시지 |
| NEW_VERSION | 기존 기준에서 새 버전 생성 | 새 고유 ID와 `DRAFT` 상태 생성, 기존 버전 불변 | 중복·저장 오류 표시 |
| DRAFT_PREVIEW | Draft 버전에 연결된 매핑 결과 조회 | 결과마다 `미리보기`와 기준 상태를 표시 | 결과가 없으면 빈 상태 표시 |
| CRITERIA_CHANGED | 실행된 매핑이 있는 Draft의 요건 텍스트 수정 | 기존 매핑 `INVALIDATED`, 재실행 안내, 공식 기능 잠금 유지 | 저장 실패 시 입력 보존 |
| APPROVED_GATE | Draft 상태에서 공식 기능 요청 | 서버가 거부하고 남은 승인 조건 표시 | 403과 지속 안내 |

</frozen-after-approval>

## Code Map

- `backend/app/models/criteria.py` -- 기준 버전·기준 항목·매핑 무효화 상태의 저장 모델
- `backend/app/services/criteria.py` -- 버전 조회·생성·수정과 기준 변경 시 매핑 무효화 규칙
- `backend/app/api/criteria.py` -- 기준 조회·수정·새 버전 생성·Draft 미리보기 API
- `backend/app/main.py` -- FastAPI 앱과 criteria 라우터 등록
- `frontend/src/app/calibration/page.tsx` -- 기준 버전 관리 및 Draft 미리보기 화면
- `frontend/src/components/criteria/CriteriaVersionPanel.tsx` -- 버전·상태·기준 목록·저장 UI
- `frontend/src/components/criteria/GateBanner.tsx` -- 공식 기능 차단 이유와 다음 조건 안내

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/models/criteria.py` -- 기준 버전과 항목 모델, 상태·무효화 필드 정의 -- 기준과 결과의 버전 추적을 보장한다.
- [x] `backend/app/services/criteria.py` -- 기준 조회·생성·수정과 Draft 변경 시 기존 매핑 무효화 구현 -- 오염된 결과 재사용을 방지한다.
- [x] `backend/app/api/criteria.py` 및 `backend/app/main.py` -- 기준 관리·미리보기 API와 승인 게이트 등록 -- 서버 권한 검증을 단일 경계로 둔다.
- [x] `frontend/src/app/calibration/page.tsx` 및 `frontend/src/components/criteria/CriteriaVersionPanel.tsx` -- context-bar, 버전 상태, 필수·우대 기준, Draft 미리보기 구현 -- HR이 현재 기준을 빠르게 확인한다.
- [x] `frontend/src/components/criteria/GateBanner.tsx` -- Draft의 공식 행동 차단 및 다음 조건 메시지 구현 -- 비활성 버튼만으로 상태를 전달하지 않는다.
- [x] `backend/tests/test_criteria_version.py` 및 `frontend/src/app/calibration/page.test.tsx` -- 버전 생성·변경 무효화·Draft 게이트·미리보기 표시 테스트 -- I/O 행렬의 경계 사례를 검증한다.

**Acceptance Criteria:**
- Given 데모 포지션이 열려 있을 때, when HR이 기준 관리 화면을 조회하면, then 필수·우대 기준과 현재 버전 ID·상태·생성·수정 정보를 확인할 수 있어야 한다.
- Given HR이 기준을 저장하거나 새 버전을 만들 때, when HM 승인 전이면, then 고유 ID의 `DRAFT` 버전으로 저장되고 공식 핸드오프·최종 결정은 차단되어야 한다.
- Given Draft에 매핑 결과가 있을 때, when HR이 결과를 조회하면, then `미리보기` 표시와 기준별 결과 상태를 확인할 수 있어야 한다.
- Given 실행된 매핑이 있는 Draft의 요건 텍스트를 수정할 때, when 저장이 완료되면, then 기존 매핑은 `INVALIDATED`가 되고 수정 기준으로 재실행하라는 안내가 표시되어야 한다.
- Given Draft 상태에서 공식 기능을 요청할 때, when 서버가 요청을 검증하면, then 요청을 거부하고 미승인 상태와 필요한 조건을 반환해야 한다.

## Verification

**Commands:**
- `uv run --project backend --group dev pytest backend/tests/test_criteria_version.py` -- expected: all criteria version and gate tests pass
- `npm test` (frontend directory) -- expected: calibration UI tests pass

**Manual checks (if no CLI):**
- HR로 `/calibration`을 열어 버전 상태, Draft 미리보기, 기준 수정 후 무효화 안내와 공식 기능 잠금 메시지를 확인한다.

## Suggested Review Order

**기준 버전·무효화 규칙**

- 기준 버전 상태와 Draft 변경 시 무효화 흐름의 핵심 진입점입니다.
  [`criteria.py:123`](../../backend/app/services/criteria.py#L123)

- 기준 버전·항목·매핑 상태의 저장 계약을 확인합니다.
  [`criteria.py:10`](../../backend/app/models/criteria.py#L10)

**API 게이트**

- 기준 조회·생성·수정·미리보기 API의 외부 경계를 확인합니다.
  [`criteria.py:10`](../../backend/app/api/criteria.py#L10)

- 미승인 기준의 공식 핸드오프 차단을 서버에서 검증합니다.
  [`main.py:24`](../../backend/app/main.py#L24)

**발표용 화면 연결**

- HR 기준 관리 화면에서 서버 기준과 Draft 안내가 연결됩니다.
  [`page.tsx:15`](../../frontend/src/app/calibration/page.tsx#L15)

- API 호출과 로컬 데모 fallback의 동작을 확인합니다.
  [`criteria-api.ts:43`](../../frontend/src/lib/criteria-api.ts#L43)

- 기준 수정·새 Draft 생성과 잠금 안내 UI를 확인합니다.
  [`CriteriaVersionPanel.tsx:21`](../../frontend/src/components/criteria/CriteriaVersionPanel.tsx#L21)

**검증**

- 버전 복제와 버전 간 무효화 경계를 검증합니다.
  [`test_criteria_version.py:42`](../../backend/tests/test_criteria_version.py#L42)

- Draft 기준 수정 후 사용자에게 재실행을 안내하는 화면을 검증합니다.
  [`page.test.tsx:16`](../../frontend/src/app/calibration/page.test.tsx#L16)
