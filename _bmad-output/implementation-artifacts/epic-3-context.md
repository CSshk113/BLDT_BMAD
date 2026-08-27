# Epic 3 Context: 공동 판단 로그와 현업 핸드오프

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

지원서 원문 근거와 승인된 기준을 바탕으로 HR·HM의 독립 판단을 보존하고, 현업 리더가 의견 차이와 미검증 지점을 한 장의 핸드오프로 확인하게 한다. 인터뷰 질문 후보와 검증 결과까지 같은 흐름에 연결하되, 최종 판단은 항상 사람이 직접 내린다.

## Stories

- Story 3.1: 판단 로그와 HR·HM 의견 차이 기록
- Story 3.2: JSON 기반 핸드오프 카드 생성
- Story 3.3: 근거·질문 은행 기반 인터뷰 질문 후보 관리
- Story 3.4: 면접 검증 결과와 최종 결정 기록

## Requirements & Constraints

- 공식 검토·핸드오프·최종 결정은 승인된 `criteria_version_id`, 처리 완료 지원서, 저장된 원문 근거를 사용한다. 미승인 기준은 탐색용이며 공식 기능을 만들 수 없다.
- HR과 HM의 판단 로그는 역할별로 독립 보존한다. 기준 항목 상태(`FULFILLED`, `PARTIALLY_FULFILLED`, `UNFULFILLED`, `UNVERIFIABLE`)와 Document/전형 단계 판정값을 섞지 않는다.
- 의견 차이는 상태·사유·위치·근거별로 드러내며, 시스템이 한쪽을 대표 결론으로 선택하거나 자동 통합하지 않는다. 다른 검토자의 로그는 읽기 전용이다.
- 판단 로그 수정은 현재 값을 갱신하되 `edit_history` JSON 배열에 이전 값·변경 값·행위자·시각·사유를 남긴다.
- 핸드오프의 질문·면접 검증 데이터는 별도 관계형 테이블이 아니라 `HandoffCard.payload_json`에 저장하되 지원서·기준·근거 추적 ID를 보존한다.
- 질문 후보는 `gpt-5.6-luna`와 Code.presso `question-bank`의 관련 실제 사용 이력을 활용한다. 근거에 없는 사실, 보호 특성·사생활 질문, 자동 합격·탈락 유도는 금지한다. 정확한 후보 수는 고정하지 않는다.
- 최종 결정값은 `채용`, `미채용`, `종료`, `인재풀 등록`만 허용한다.

## Technical Decisions

계층형 모듈러 모놀리스(Next.js/React/Tailwind, FastAPI/Pydantic, SQLite)를 유지한다. 기존 `ReviewLog`와 매핑 결과의 지원서·기준·처리 실행·artifact 연결을 재사용하고, 핸드오프는 JSON payload를 단순 저장한다. 역할 검증과 승인 게이트는 서버에서 처리하며 API 키·파일 경로는 브라우저에 노출하지 않는다.

## UX & Interaction Patterns

근거 검토 화면에서 HR·HM의 영역을 분리해 보여주고, 이견은 양쪽 원문 근거와 함께 표시한다. LEAD는 핸드오프에서 기준·근거·판단·우려·질문 후보를 확인하고 질문을 선택한다. 질문 후보는 원래 질문·수정본·이유·연결 근거·선택 상태를 보여주며, 최종 결정 화면에서는 초기 가설과 면접 검증 결과를 나란히 비교한다.

## Cross-Story Dependencies

Epic 1의 승인된 기준 버전과 Epic 2의 처리 완료 지원서·원문 매핑이 선행 조건이다. Story 3.1의 판단 로그와 의견 차이는 Story 3.2 핸드오프의 입력이며, Story 3.2가 만든 `payload_json`을 Story 3.3 질문 후보와 Story 3.4 면접 검증·최종 결정이 확장한다.
