---
title: 'Story 1.2 - HR·HM 독립 교정 검토와 충돌 비교'
type: 'feature'
created: '2026-08-27'
status: 'done'
baseline_commit: '0af098c84ca085699b077616d75685c4419a82c9'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-1-1-position-criteria-version-and-draft-preview.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-Zero100_Builderthon-2026-08-26/ARCHITECTURE-SPINE.md'
  - '{project-root}/_bmad-output/planning-artifacts/ux-designs/ux-Zero100_Builderthon-2026-08-27/EXPERIENCE.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** HR과 HM의 기준 해석이 서로 다른데도 차이를 확인할 수 없으면, 승인 전 기준 교정이 형식적으로 끝나고 이후 검토 결과를 신뢰하기 어렵다.

**Approach:** 동일한 Draft 기준과 표본에 대해 HR·HM이 각자의 상태·사유·원문 위치를 독립 저장하고, 서버가 두 `ReviewLog`를 비교해 충돌과 양쪽 근거를 보여준다.

## Boundaries & Constraints

**Always:** 기준 항목 상태는 `충족`, `부분 충족`, `미충족`, `확인 불가`로 표시한다. 모든 검토는 `criteria_version_id`, 지원서 표본, 검토자 역할에 연결한다. 다른 검토자의 기록은 읽기 전용이다. 미제출 검토는 충돌이 아니라 `아직 검토하지 않음`으로 표시한다.

**Ask First:** 없음. 데모 역할 전환은 인증이 아닌 UI 시뮬레이션으로 유지한다.

**Never:** HR·HM 판단을 자동 통합하거나 평균내지 않는다. 지원서 전체 판정 어휘와 기준 항목 상태를 섞지 않는다. 점수·순위·자동 합격·탈락을 추가하지 않는다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 첫 검토 저장 | Draft 표본, 역할, 기준별 상태·사유·위치 | 역할과 버전이 포함된 독립 `ReviewLog` 저장 | 필수 상태·사유 누락을 필드 오류로 표시 |
| 양쪽 제출·차이 있음 | HR/HM의 상태·위치·사유 불일치 | `OPEN` 충돌과 양쪽 값을 나란히 표시 | 자동 선택·통합 금지 |
| 한쪽만 제출 | HR 또는 HM 기록 1건 | 제출값과 `아직 검토하지 않음` 표시 | 미제출을 충돌로 생성하지 않음 |
| 다른 역할 기록 편집 시도 | 읽기 전용 상대 `ReviewLog` | 편집 제어를 제공하지 않음 | API도 403으로 거부 |

</frozen-after-approval>

## Code Map

- `backend/app/db.py` -- 기준 항목과 연결된 `review_logs` 저장 구조를 추가할 SQLite 경계
- `backend/app/models/criteria.py` -- 기준 상태와 별도로 검토 상태·역할·근거·충돌 응답 계약을 정의할 Pydantic 모델
- `backend/app/services/criteria.py` -- 역할별 검토 저장 및 상태·위치·사유 차이를 계산하는 도메인 규칙
- `backend/app/api/criteria.py` -- `POST /api/criteria/{id}/reviews`, `GET /api/criteria/{id}/conflicts` API 경계
- `frontend/src/app/calibration/page.tsx` -- Story 1.1 화면에 역할 전환과 독립 검토 표면을 연결할 페이지
- `frontend/src/components/criteria/` -- `Table`, `RadioGroup`, `Textarea`, `Badge`, `Alert`, `Dialog` 기반 교정 매트릭스·비교 UI
- `frontend/src/lib/criteria-api.ts` -- 검토 저장·충돌 조회 요청과 데모 fallback을 추가할 API 클라이언트
- `backend/tests/test_criteria_review.py` -- 저장, 차이 계산, 미제출, 상대 기록 수정 거부의 경계 테스트
- `frontend/src/app/calibration/page.test.tsx` -- 역할별 입력, 충돌 표시, 상대 기록 읽기 전용 UI 테스트

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/db.py`, `backend/app/models/criteria.py` -- 역할·검토 상태·근거·버전 연결을 저장하고 응답 모델을 정의 -- 2-Tier 상태 혼입을 방지한다.
- [x] `backend/app/services/criteria.py`, `backend/app/api/criteria.py` -- 독립 검토 저장, 충돌 계산·조회, 상대 기록 변경 거부를 구현 -- 서버에서 검토 보존 규칙을 강제한다.
- [x] `frontend/src/lib/criteria-api.ts`, `frontend/src/components/criteria/CalibrationMatrix.tsx`, `frontend/src/app/calibration/page.tsx` -- HR/HM 입력과 나란히 비교하는 교정 화면을 구현 -- 승인 전 충돌을 빠르게 확인한다.
- [x] `backend/tests/test_criteria_review.py`, `frontend/src/app/calibration/page.test.tsx` -- I/O 표의 정상·경계 시나리오를 검증 -- 미제출·읽기 전용·자동 통합 금지를 보장한다.

**Acceptance Criteria:**
- Given `DRAFT` 기준과 동일 표본이 있을 때, when HR과 HM이 각자 상태·사유·위치를 저장하면, then 서로 다른 `ReviewLog`에 역할과 기준 버전 ID가 보존된다.
- Given 양쪽 검토가 제출됐을 때, when 상태·위치·사유 중 하나라도 다르면, then `OPEN` 충돌과 양쪽 판단·근거·차이가 표시되고 자동 통합하지 않는다.
- Given 한쪽만 검토했을 때, when 비교 화면을 열면, then 제출값과 `아직 검토하지 않음`을 구분하고 충돌로 표시하지 않는다.
- Given 상대 `ReviewLog`가 존재할 때, when 현재 검토자가 비교 화면을 열면, then 상대 기록은 읽을 수 있지만 수정·삭제할 수 없다.
- Given 양쪽 판단을 표시할 때, when 회사 판정 어휘가 노출되면, then HR 스크리닝과 HM 서류 심사의 단계별 상태·사유를 분리한다.

## Spec Change Log

## Verification

**Commands:**
- `uv run --project backend --group dev pytest backend/tests/test_criteria_review.py backend/tests/test_criteria_version.py` -- expected: all backend tests pass
- `npm test` (from `frontend`) -- expected: all frontend tests pass
- `npm run build` (from `frontend`) -- expected: Next.js production build succeeds

**Manual checks:**
- HR과 HM을 각각 선택해 같은 기준을 저장하고, 충돌 행에서 양쪽 값·근거가 보이며 상대 기록 편집 제어가 없는지 확인한다.

## Suggested Review Order

**독립 검토 저장과 충돌 계산**

- 역할별 로그를 보존하고 세 필드 차이를 서버에서 계산합니다.
  [`criteria.py:245`](../../backend/app/services/criteria.py#L245)

- API가 검토 저장과 충돌 조회를 명시된 응답 계약으로 노출합니다.
  [`criteria.py:52`](../../backend/app/api/criteria.py#L52)

- 기준별 역할·상태·근거 모델이 2-Tier 상태를 분리합니다.
  [`criteria.py:92`](../../backend/app/models/criteria.py#L92)

**교정 화면과 오류 경계**

- HR/HM 양쪽 기록과 충돌 필드를 한 표에서 비교합니다.
  [`CalibrationMatrix.tsx:101`](../../frontend/src/components/criteria/CalibrationMatrix.tsx#L101)

- 역할 전환과 저장 결과를 현재 Draft 화면에 연결합니다.
  [`page.tsx:136`](../../frontend/src/app/calibration/page.tsx#L136)

- API가 없을 때만 데모 fallback을 사용하고 서버 오류는 표시합니다.
  [`criteria-api.ts:170`](../../frontend/src/lib/criteria-api.ts#L170)

**검증**

- 독립 로그·충돌·미검토·권한·입력 검증 시나리오를 검증합니다.
  [`test_criteria_review.py:10`](../../backend/tests/test_criteria_review.py#L10)

- 비교 화면의 충돌 수와 양쪽 근거 노출을 검증합니다.
  [`page.test.tsx:48`](../../frontend/src/app/calibration/page.test.tsx#L48)
