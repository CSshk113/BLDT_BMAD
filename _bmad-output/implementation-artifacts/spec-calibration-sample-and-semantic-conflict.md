---
title: '교정 표본 정보 표시와 불필요한 충돌 완화'
type: 'bugfix'
created: '2026-08-28'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'd163db2565e5eaad6d6bb23ad4fffa7978bf303c'
context:
  - 'C:/Users/kimsu/BLDT_BMAD/_bmad-output/implementation-artifacts/epic-1-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** 교정 화면에서 HR과 HM이 같은 원문 위치와 같은 판단을 바탕으로 사유를 작성해도 문장 표현이 다르면 `판단 사유` 충돌로 표시된다. 또한 `APPS-2`만 표시되어 데모 관객이 어떤 지원서를 두 사람이 검토하는지 즉시 이해하기 어렵다.

**Approach:** 충돌 여부는 평가 상태와 원문 위치의 실질적 차이를 기준으로 판단하고, 판단 사유와 같은 원문 위치의 표현 차이는 독립 의견 보존 영역으로만 표시한다. 교정 표본에는 비식별 지원서 식별자·후보 라벨·포지션·출처와 대표 원문 문맥을 함께 보여준다.

## Boundaries & Constraints

**Always:** HR/HM의 원래 사유와 역할별 기록은 보존한다. `APPS-2`와 `후보081` 같은 비식별 값만 표시한다. 같은 위치의 표기 차이는 페이지 별칭, 공백, 일반 구분자와 섹션 표기를 정규화해 비교한다.

**Ask First:** 없음. 기존 90초 데모 흐름과 Draft/승인 게이트는 유지한다.

**Never:** 사유를 AI로 자동 통합하거나 한쪽 의견으로 덮어쓰지 않는다. 상태 차이를 사유 정규화로 숨기지 않는다. 새로운 지원서 평가·랭킹 기능을 추가하지 않는다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| SAME_EVIDENCE_DIFFERENT_WORDING | 두 검토자의 상태와 실질적 위치가 같고 사유·위치 표기만 다름 | 충돌 상태가 `NONE` 또는 기존 해결 상태이며 원래 사유·위치를 양쪽에 각각 표시 | N/A |
| DIFFERENT_LOCATION | 상태가 같아도 정규화된 실질 위치가 다름 | `원문 위치` 충돌을 표시 | 기존 충돌 해결 절차 사용 |
| SAMPLE_SUMMARY | `APPS-2` 교정 표본 조회 | 식별자·후보 라벨·포지션·출처·대표 문맥 표시 | 정보가 없으면 비식별 ID와 `정보 없음` 표시 |

</frozen-after-approval>

## Code Map

- `backend/app/services/criteria.py` -- `get_review_matrix`의 충돌 필드 비교와 지원서 표본 요약 조합 지점
- `backend/app/models/criteria.py` -- `ReviewMatrix` 응답과 표본 요약 계약
- `frontend/src/components/criteria/CalibrationMatrix.tsx` -- 교정 표본 제목·지원서 요약·HR/HM 비교 UI
- `frontend/src/lib/criteria-api.ts` -- 서버 응답 및 네트워크 fallback의 `ReviewMatrix` 계약
- `backend/tests/test_criteria_review.py` -- 역할 독립성과 충돌 계산 테스트
- `frontend/src/app/calibration/page.test.tsx` -- 교정 화면 렌더링 및 표본 정보 표시 테스트

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/models/criteria.py`, `backend/app/services/criteria.py` -- 표본 요약 필드와 위치 표현 정규화 비교를 추가하고 사유 문장 차이를 충돌 조건에서 제외 -- 동일 근거의 표현 차이로 승인 게이트가 막히지 않게 한다.
- [x] `frontend/src/lib/criteria-api.ts`, `frontend/src/components/criteria/CalibrationMatrix.tsx` -- 서버·fallback 표본 요약을 표시하고 기존 HR/HM 사유를 그대로 렌더링 -- 데모 관객이 입력 지원서와 독립 검토 구조를 이해하게 한다.
- [x] `backend/tests/test_criteria_review.py`, `frontend/src/app/calibration/page.test.tsx` -- 동일 위치·다른 사유, 다른 위치, 표본 요약 표시를 검증 -- 회귀를 방지한다.

**Acceptance Criteria:**
- Given HR과 HM의 기준 상태가 같고 위치가 정규화 후 같을 때, when 판단 사유 또는 위치 표기만 다르면, then 해당 표현 차이를 충돌 차이로 추가하지 않고 양쪽 원문을 각각 보존한다.
- Given 두 검토자의 원문 위치가 페이지 별칭·공백·구분자·섹션 표기 정규화 후에도 다를 때, when 비교하면, then `원문 위치` 차이와 기존 충돌 해결 흐름을 유지한다.
- Given 교정 표본이 `APPS-2`일 때, when 교정 화면을 열면, then `APPS-2`, `후보081`, 포지션, 출처와 대표 원문 문맥이 함께 보인다.
- Given 표본 요약 일부가 없을 때, when 화면을 렌더링하면, then 비식별 식별자는 유지하고 누락 필드는 안전한 대체 문구로 표시한다.

## Design Notes

판단 사유는 서로 다른 관찰을 보존하는 기록이므로 텍스트 동일성만으로 충돌을 만들지 않는다. 위치도 같은 근거를 가리키는 표기 차이로 승인 차단을 만들지 않도록 페이지 별칭·공백·구분자·섹션 표기를 정규화한다. 정규화 후 실질 위치가 다른 경우에는 위치 충돌을 유지한다.

## Verification

**Commands:**
- `uv run --project backend --group dev pytest backend/tests/test_criteria_review.py` -- expected: 충돌 계산 및 표본 요약 백엔드 테스트 통과
- `npm run test -- --run src/app/calibration/page.test.tsx` -- expected: 교정 화면 테스트 통과
- `npx tsc --noEmit` -- expected: TypeScript 오류 없음
- `npm run build` -- expected: 프로덕션 빌드 성공

**Manual checks:**
- 교정 화면에서 `APPS-2 · 후보081`과 표본 문맥이 보이고, 사유·위치 표기만 다른 동일 근거 입력이 승인 차단을 만들지 않는지 확인한다.

## Suggested Review Order

**충돌 판정과 위치 정규화**

- 상태 차이만 차단하고 사유·동일 위치 표현 차이는 보존합니다.
  [`criteria.py:364`](../../backend/app/services/criteria.py#L364)

- 페이지 별칭과 범위를 안전하게 비교해 실제 위치 차이를 남깁니다.
  [`criteria.py:70`](../../backend/app/services/criteria.py#L70)

- 클라이언트 fallback도 서버와 같은 위치 비교 규칙을 적용합니다.
  [`criteria-api.ts:261`](../../frontend/src/lib/criteria-api.ts#L261)

**교정 표본 표시**

- 지원서·후보·포지션·출처·대표 문맥을 응답 계약으로 전달합니다.
  [`criteria.py:81`](../../backend/app/services/criteria.py#L81)

- API 표본을 우선 표시하고 누락 필드는 안전한 대체 문구를 사용합니다.
  [`CalibrationMatrix.tsx:79`](../../frontend/src/components/criteria/CalibrationMatrix.tsx#L79)

**회귀 검증**

- 동일 위치의 다른 표현과 원본 기록 보존을 검증합니다.
  [`test_criteria_review.py:31`](../../backend/tests/test_criteria_review.py#L31)

- API가 반환한 고유 표본 문맥이 실제 화면에 표시되는지 검증합니다.
  [`page.test.tsx:68`](../../frontend/src/app/calibration/page.test.tsx#L68)
