---
title: '캘리브레이션 페이지 Code.Presso 로고 교체'
type: 'chore'
created: '2026-08-28'
status: 'done'
route: 'one-shot'
review_loop_iteration: 0
context: []
---

# 캘리브레이션 페이지 Code.Presso 로고 교체

## Intent

**Problem:** 캘리브레이션 페이지의 좌측 브랜드 영역이 임시 기호와 텍스트로 표시되어 실제 Code.Presso 브랜드 자산과 일치하지 않는다.

**Approach:** 제공된 `code.presso.svg`를 프론트엔드 정적 자산으로 등록하고, 캘리브레이션 페이지의 임시 브랜드 마크를 해당 SVG 이미지로 교체한다.

## Suggested Review Order

1. [`frontend/src/app/calibration/page.tsx`](../../frontend/src/app/calibration/page.tsx) — 임시 마크가 실제 SVG와 접근성 대체 텍스트로 교체되었는지 확인
2. [`frontend/public/code-presso.svg`](../../frontend/public/code-presso.svg) — 제공된 로고 자산과 크기·색상 보존 여부 확인
