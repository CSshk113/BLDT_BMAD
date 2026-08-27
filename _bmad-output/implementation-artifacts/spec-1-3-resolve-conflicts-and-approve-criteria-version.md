---
title: 'Story 1.3 - 충돌 해결 및 기준 버전 승인'
type: 'feature'
created: '2026-08-27'
status: 'done'
baseline_commit: '9723725ee990752fa5138fd90148805ae9951fe5'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-1-2-independent-hr-hm-calibration-and-conflict-comparison.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** HR과 HM의 검토 차이가 남아 있으면 기준을 공식 기준으로 확정할 수 없고, Draft 결과가 공식 핸드오프나 최종 결정으로 오인될 수 있다.

**Approach:** HR이 충돌 항목별 해결 사유를 남겨 원래 양쪽 판단을 보존하고, 서버가 열린 충돌과 필수 검토 완료를 재검증한 뒤 기준 버전을 `APPROVED`로 전환한다. 승인 전 공식 핸드오프와 최종 결정은 계속 차단하고, 승인 후에는 승인된 `criteria_version_id`를 다음 흐름에 전달한다.

## Boundaries & Constraints

**Always:** 충돌 해결은 `RESOLVED` 상태, 해결자, 시각, 사유를 기록한다. 원래 HR/HM 판단과 근거는 삭제·통합하지 않는다. 승인은 `OPEN` 충돌 0건과 HR/HM 필수 검토 완료를 서버에서 확인한다. 기준 승인과 공식 게이트 판단은 동일한 기준 버전 ID를 사용한다.

**Ask First:** 없음. 데모에서는 HR 권한을 승인 권한으로 시뮬레이션한다.

**Never:** 충돌 판단을 AI가 자동 통합하거나 한쪽 의견으로 대체하지 않는다. Draft 기준으로 공식 핸드오프·최종 결정을 생성하지 않는다. 점수·순위·자동 합격·탈락을 추가하지 않는다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 열린 충돌 승인 시도 | DRAFT, OPEN 충돌 존재 | 승인 차단, 충돌 항목·근거·다음 행동 표시 | 409와 남은 조건 반환 |
| 충돌 해결 | OPEN 항목, HR 해결 사유 | RESOLVED 기록, 원래 양쪽 로그와 해결 메타데이터 보존 | 권한 없는 역할은 403 |
| 필수 검토 미완료 | 충돌 0건, 한쪽 검토 누락 | 승인 차단, 누락 검토 조건 안내 | 409 |
| 기준 승인 | 충돌 0건, HR/HM 검토 완료 | APPROVED 전환, 승인자·시각·버전 ID 고정 | 이미 승인/보관된 버전은 변경 거부 |
| 공식 게이트 | DRAFT/APPROVED 기준으로 핸드오프 생성 요청 | APPROVED만 허용하고 버전 ID 전달 | 미승인 기준은 403 |

</frozen-after-approval>

## Code Map

- `backend/app/db.py` -- 충돌 해결 상태와 해결자·시각·사유를 저장할 스키마 경계
- `backend/app/models/criteria.py` -- `RESOLVED` 충돌, 해결 입력, 승인 응답 계약
- `backend/app/services/criteria.py` -- 충돌 해결·필수 검토 검증·원자적 기준 승인 규칙
- `backend/app/api/criteria.py` -- `POST /api/criteria/{id}/conflicts`, `POST /api/criteria/{id}/approve` API 경계
- `backend/app/main.py` -- 공식 핸드오프 게이트와 승인된 버전 연결
- `frontend/src/app/calibration/page.tsx` -- 충돌 해결 입력과 기준 승인 상태 연결
- `frontend/src/components/criteria/CalibrationMatrix.tsx` -- 충돌 행의 해결 사유 입력 surface
- `backend/tests/test_criteria_approval.py` -- 승인 차단·해결·검토 누락·성공 경계 테스트
- `frontend/src/app/calibration/page.test.tsx` -- 충돌 해결과 승인 버튼 상태 검증

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/db.py`, `backend/app/models/criteria.py` -- 충돌 해결 메타데이터와 승인 응답 모델을 추가 -- 원래 검토 로그 보존을 보장한다.
- [x] `backend/app/services/criteria.py`, `backend/app/api/criteria.py`, `backend/app/main.py` -- 해결·승인·공식 게이트를 서버 검증과 함께 구현 -- Draft 우회를 차단한다.
- [x] `frontend/src/components/criteria/CalibrationMatrix.tsx`, `frontend/src/app/calibration/page.tsx`, `frontend/src/lib/criteria-api.ts` -- 충돌 해결 사유 입력과 승인 전후 상태를 연결 -- 다음 행동을 명확히 안내한다.
- [x] `backend/tests/test_criteria_approval.py`, `frontend/src/app/calibration/page.test.tsx` -- I/O 표의 정상·경계 시나리오를 검증 -- 미해결 충돌과 미검토 승인을 막는다.

**Acceptance Criteria:**
- Given `OPEN` 충돌이 있을 때, when HR이 승인을 시도하면, then 승인을 차단하고 열린 충돌 수·항목·양쪽 근거·다음 행동을 반환한다.
- Given 충돌 항목이 있을 때, when 권한 있는 사용자가 해결 사유를 저장하면, then `RESOLVED`와 해결자·시각·사유를 기록하고 원래 양쪽 판단·근거를 보존한다.
- Given 열린 충돌이 없고 HR/HM 필수 검토가 완료됐을 때, when HR이 승인을 확정하면, then 버전을 `APPROVED`로 바꾸고 승인자·승인 시각·`criteria_version_id`를 고정한다.
- Given 기준이 `APPROVED`일 때, when 공식 핸드오프 생성을 시작하면, then 승인 잠금을 해제하고 같은 버전 ID를 요청과 결과에 연결한다.
- Given 기준이 Draft이거나 필수 인터뷰 조건이 부족할 때, when 최종 결정을 저장하면, then 저장하지 않고 해당 조건을 안내한다.

## Spec Change Log

## Verification

**Commands:**
- `uv run --project backend --group dev pytest backend/tests/test_criteria_approval.py backend/tests/test_criteria_review.py backend/tests/test_criteria_version.py` -- expected: all backend tests pass
- `npm test` (from `frontend`) -- expected: all frontend tests pass
- `npm run build` (from `frontend`) -- expected: Next.js production build succeeds

## Suggested Review Order

**승인·공식 게이트**

- 승인 조건과 Draft 우회를 서버에서 차단하는 핵심 흐름입니다.
  [`criteria.py:441`](../../backend/app/services/criteria.py#L441)

- API 권한 헤더와 승인·충돌 해결 경계를 확인합니다.
  [`criteria.py:77`](../../backend/app/api/criteria.py#L77)

- 승인된 버전만 공식 핸드오프를 열도록 연결합니다.
  [`main.py:24`](../../backend/app/main.py#L24)

**충돌 해결·데이터 보존**

- 해결 메타데이터를 별도 레코드로 보존하고 양쪽 판단을 유지합니다.
  [`db.py:61`](../../backend/app/db.py#L61)

- 재검토 시 해결 상태를 다시 열어 오래된 합의를 재사용하지 않습니다.
  [`criteria.py:326`](../../backend/app/services/criteria.py#L326)

**UI 상태 연결**

- 승인 상태와 실제 공식 핸드오프 동작을 화면에 연결합니다.
  [`page.tsx:210`](../../frontend/src/app/calibration/page.tsx#L210)

- 충돌 해결 사유 입력과 원래 의견 보존을 제공합니다.
  [`CalibrationMatrix.tsx:194`](../../frontend/src/components/criteria/CalibrationMatrix.tsx#L194)

- Draft·승인·보관 상태의 게이트 표현을 분리합니다.
  [`GateBanner.tsx:10`](../../frontend/src/components/criteria/GateBanner.tsx#L10)

**검증**

- 승인 차단·권한·해결·핸드오프 잠금 해제 경계를 검증합니다.
  [`test_criteria_approval.py:51`](../../backend/tests/test_criteria_approval.py#L51)

- Draft 화면의 승인 버튼과 충돌 해결 surface를 확인합니다.
  [`page.test.tsx:8`](../../frontend/src/app/calibration/page.test.tsx#L8)
