# Epic 1 Context: 합의된 기준으로 안전하게 검토 시작

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

HR과 HM이 Code.presso의 B2B 영업 매니저 평가 기준을 각자 검토하고 의견 차이를 보존한 뒤, 승인된 기준 버전만 공식 검토·핸드오프·최종 결정에 사용하도록 한다. HR은 승인 전에도 Draft 기준의 매핑 결과를 미리 탐색할 수 있지만, 미승인 결과가 공식 판단으로 오인되거나 공식 핸드오프가 생성되어서는 안 된다.

## Stories

- Story 1.1: 포지션 기준 버전 확인 및 Draft 미리보기
- Story 1.2: HR·HM 독립 교정 검토와 충돌 비교
- Story 1.3: 충돌 해결 및 기준 버전 승인

## Requirements & Constraints

- 데모 포지션은 `B2B 영업 매니저 5년 이상 ver.4`이며 기준은 버전 단위로 관리한다.
- 기준 버전에는 고유 ID, 포지션, 필수·우대 기준, 상태와 생성·수정·승인 정보가 있어야 한다.
- 기준 상태는 `DRAFT`, `APPROVED`, `ARCHIVED`를 사용한다. Draft에서는 탐색용 결과를 허용하되 `미리보기`를 명시한다.
- HR과 HM은 기준별 상태, 사유와 원문 근거를 독립적으로 기록한다. 두 판단을 자동으로 통합하지 않는다.
- 충돌이 미해결된 기준은 승인할 수 없다. 승인 전에는 공식 핸드오프 카드와 최종 결정 기능을 차단한다.
- 승인 시 고유한 기준 버전 ID와 승인 시각을 고정하고, 이후 공식 결과가 이 ID를 참조하도록 한다.
- 기준 텍스트가 수정되어 기존 매핑이 해당 기준과 불일치하면 기존 매핑을 `INVALIDATED` 처리하고 재실행을 유도한다. 기존 결과를 새 기준에 덮어쓰지 않는다.
- 점수, 순위, 합격 확률, 자동 합격·탈락 결론은 제공하지 않는다.

## Technical Decisions

- 계층형 모듈러 모놀리스 구조에서 기준·교정·승인 API와 서비스를 분리한다.
- 핵심 API는 기준 조회·수정 `GET/PATCH /api/criteria/{criteria_version_id}`, 교정 저장 `POST /api/criteria/{criteria_version_id}/reviews`, 충돌 조회·해결 `GET/POST /api/criteria/{criteria_version_id}/conflicts`, 승인 `POST /api/criteria/{criteria_version_id}/approve`다.
- 서버가 역할, 기준 버전과 승인 상태를 확인한다. HR은 교정·승인 권한을 갖고, HM은 독립 검토를 수행한다. 다른 검토자의 로그는 수정하지 못한다.
- 모든 근거와 검토 로그는 `criteria_version_id`에 연결한다. 승인은 충돌 상태를 서버에서 재검증한 뒤 처리한다.

## UX & Interaction Patterns

- 전역 `context-bar`에 포지션, 기준 버전, 승인 상태와 현재 역할을 표시한다.
- `workflow-nav`는 교정·검토·핸드오프 단계의 현재·완료·잠김 상태를 텍스트로 보여준다.
- `calibration-matrix`는 HR·HM의 독립 입력, 양쪽 근거, 충돌 행과 해결 사유를 비교한다.
- `gate-banner`는 승인 전 공식 기능이 차단된 이유와 남은 조건을 설명한다. 비활성 버튼만으로 차단 상태를 전달하지 않는다.
- 승인·버전 생성·기준 수정처럼 결과가 바뀌는 행동은 확인 대화상자와 지속적인 저장 결과 메시지를 사용한다.

## Cross-Story Dependencies

- Story 1.1이 기준 버전과 Draft 탐색 경로를 제공하고, Story 1.2가 HR·HM 검토와 충돌 데이터를 추가한다. Story 1.3은 해결된 충돌을 검증해 승인 상태로 전환한다.
- Epic 2의 공식 매핑과 Epic 3의 공식 핸드오프·최종 결정은 승인된 기준 버전에 의존한다. Draft 결과는 해당 에픽의 공식 결과로 사용할 수 없다.
