후보 ---
title: '지원서 처리 목록 스크롤 영역 개선'
type: 'feature'
created: '2026-08-28'
status: 'done'
route: 'one-shot'
baseline_commit: '420d1dd23af21663d2610173924a9dcf118e07fa'
context: []
---

# 지원서 처리 목록 스크롤 영역 개선

## Intent

**Problem:** 지원서 처리 목록이 항목 수에 따라 계속 길어져 다른 처리 상세 영역을 아래로 밀고, 긴 목록을 한 화면에서 효율적으로 탐색하기 어렵습니다.

**Approach:** 목록 본문을 화면 세로 길이의 80%로 제한하고 내부 세로 스크롤을 활성화합니다. 목록 헤더는 유지하며, 기존 선택 동작과 선택 상태 전달을 보존합니다.

## Suggested Review Order

- 목록 본문을 화면 높이 80%로 고정하고 내부 세로 스크롤을 활성화합니다.
  [`ProcessingList.tsx:17`](../../frontend/src/components/applications/ProcessingList.tsx#L17)

- 선택 상태와 기존 항목 클릭 동작의 회귀를 검증합니다.
  [`applications.test.tsx:42`](../../frontend/src/components/applications/applications.test.tsx#L42)

- 80vh 및 overflow 스타일 계약을 테스트로 고정합니다.
  [`applications.test.tsx:49`](../../frontend/src/components/applications/applications.test.tsx#L49)
