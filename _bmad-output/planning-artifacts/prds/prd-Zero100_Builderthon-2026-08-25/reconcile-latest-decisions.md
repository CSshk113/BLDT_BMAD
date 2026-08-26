# Input Reconciliation — 최신 변경 결정

- 입력: 2026-08-27 사용자 변경 요청
- 대상: `prd.md`, `addendum.md`, 동기화된 아키텍처 문서

## 반영한 내용

- MVP와 베이스라인 모델을 `gpt-5.6-luna`로 통일했다.
- PB-02를 활성 Phase-blocker에서 제거하고 D-03 deferred로 이동했다. 실행 절차는 addendum에 보존했다.
- 발표용 데이터 세트의 미정 상태를 유지했다.
- PB-03 해결을 위해 아키텍처의 PDF 입력 파이프라인을 PDF→LlamaParse→Markdown으로 변경했다.
- 아키텍처의 20건 고정과 기존 5분 라이브 데모 흐름을 제거하고, PRD의 90초 클릭 데모 흐름으로 맞췄다.
- FR-019~FR-022 인터뷰 질문 후보 요구사항을 architecture map에 추가했다.

## 의도적으로 남긴 내용

- PB-02의 실제 15회 실행과 비교 화면 제작은 수행하지 않았다.
- 발표용 데이터 세트의 파일 수와 구성은 확정하지 않았다.
- 아키텍처 spine 자체는 동기화했지만 별도 architecture finalization은 수행하지 않았다.
