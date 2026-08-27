# Epic 2 Context: 지원서 원문에서 판단 근거 확인

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Convert anonymized application PDFs into traceable Markdown evidence for the B2B 영업 매니저 5년 이상 ver.4 criteria, so reviewers can verify each requirement against the candidate's original document and record a defensible reason. The planning-artifacts directory currently contains only `epics.md`; PRD, architecture, UX/design, and product brief artifacts were not available, so this context is compiled from the epics file only.

## Stories

- Story 2.1: PDF 업로드와 LlamaParse Markdown 변환
- Story 2.2: 기준별 원문 인용구 매핑
- Story 2.3: 스플릿 뷰와 텍스트 검색 하이라이트

## Requirements & Constraints

- Support PDF input only. Reject other formats before creating processing records or partial results.
- Process documents in this order: PDF → LlamaParse → Markdown Normalizer → `gpt-5.6-luna` → Location Resolver. Track processing state as `RECEIVED`, `PARSING`, `MAPPING`, `COMPLETED`, or `FAILED`, including the current/failed step, timestamps, and failure reason. In-progress or failed output must never appear as completed evidence.
- Preserve and connect the original PDF, LlamaParse Markdown, normalized Markdown, and each processing run to the same application. Preserve the last successful artifact on failure, and do not overwrite an existing completed result when reprocessing.
- Keep the 178-application intake ledger distinct from the 20 anonymized resume samples. Ledger-only candidates must be shown as “원장 데이터만 있음” and excluded from PDF parsing and evidence review. Where a sample exists, join its candidate token to the ledger name field and retain channel, position, application date, and decision metadata.
- Map every mandatory and preferred B2B 영업 매니저 criterion to evidence where possible. Evidence must be an exact substring verifiable in normalized Markdown; do not present an AI-written summary as source evidence. If no source support exists, show an explicit “원문에서 확인 가능한 근거가 없습니다” or “확인 불가” state and do not invent text.
- Make evidence traceable through application ID, criterion ID, criteria version ID, and processing run ID. Attach paragraph, heading, and page information when available. If stable PDF coordinates or exact location data are unavailable, provide snippet, page, and surrounding context as the fallback and identify the evidence as such.
- Draft criteria may be explored, but all Draft-derived results must be visibly labeled as preview/exploration and must not be mistaken for approved official results. Do not expose scores, rankings, pass probabilities, or automatic pass/fail conclusions.
- Keep parser credentials and server file paths on the server, using environment variables or `.env`; never expose them to the browser. Use only anonymized or synthetic material in the demo.

## Technical Decisions

- Implement within the five-day MVP's layered modular monolith: Next.js/React/Tailwind CSS frontend, FastAPI/Pydantic backend, SQLite persistence, and server-side PDF storage.
- Treat the processing run as the unit that records model, pipeline step, execution time, success/failure, and error details. Keep source artifacts immutable enough to support audit and comparison across reruns.
- Use original-text matching as the primary evidence-location strategy. The frontend may use `react-highlight-words` or `window.find()` to search normalized Markdown text; PDF coordinate highlighting is not the default path.
- Maintain a shared `active_citation_id` between the evidence card and document viewer. A failed text match must be shown as a match-failure state with the available snippet/context, never as a successful highlight of unrelated text.
- Serve data and PDFs through FastAPI only. Enforce application, criteria-version, and processing-state checks server-side before returning or using results.

## UX & Interaction Patterns

- Present a left document viewer and right criteria/evidence panel in an approximately 55:45 desktop split. Panels scroll independently while application and criteria-version context remain aligned.
- The right-side `evidence-card` must expose criterion, citation, location/fallback, evidence availability, and mapping status. Selecting it updates `active_citation_id`, searches and focuses the matching text on the left, and announces the location or fallback through persistent text and an `aria-live="polite"` region.
- Use `application-row` and `processing-stepper` to show processing state, failed step/reason, and last successful artifact. Use visible banners/text for preview status, partial-result blocking, and failure recovery; do not communicate state only through disabled controls.
- Support keyboard activation (Enter/Space) for evidence selection, preserve in-progress inputs during panel changes, and meet WCAG 2.2 AA expectations including visible non-color status indicators, 44×44px targets, and responsive stacked/tabbed layouts at narrow widths.

## Cross-Story Dependencies

- Story 2.1 produces the linked PDF, Markdown artifacts, processing state, and sample/ledger metadata required by Story 2.2.
- Story 2.2 produces criterion-level citations and location/fallback data consumed by Story 2.3.
- Epic 2 uses the criteria version supplied by Epic 1; Draft versions support preview only, while approved-version constraints govern downstream official review and handoff flows in Epic 3.
