# Final Architecture Rubric Review — R2

- Review date: 2026-08-27
- Scope: `ARCHITECTURE-SPINE.md`, `PRESENTATION-SYSTEM-DESIGN.md`, and PRD `prd.md`
- Mode: validate-only; source documents were not edited
- Verdict: **REVISE/FAIL**

## Gate verdict

The recent patches materially improved traceability, processing-run identity, role intent, question lifecycle, demo timing, and D-01–D-07 parity. The gate still fails because several non-deferred requirements are not closed as interoperable contracts. The main blockers are preview-vs-official processing, the incomplete calibration API/schema, explicit no-evidence outcomes, current-result promotion integrity, and enforceable interview-question safety.

## Critical/high findings

### H-01 — Preview mode is asserted but conflicts with the processing/API contract

- **References:** PRD `prd.md:63,83,99-105`; spine `AD-1:92-99`, `AD-6:132-139`, Core API `215-231`, demo contract `237-246`.
- **Finding:** The PRD permits exploratory results on an unapproved criteria version, with a preview watermark, while the spine’s upload contract accepts only an approved version (`219`) and its question/handoff contracts are also official-only. `preview_mode` is prose only; it is not persisted or carried in an output/API contract. Final-decision gating is not stated on the decision endpoint.
- **Required guard:** Define persisted `PREVIEW`/`OFFICIAL` artifact mode, preview watermark/status, and a separate preview processing path whose outputs can never be promoted to official mappings, handoffs, or decisions. State the approved-version, `COMPLETED`, current-run preconditions on every official write.
- **Disposition:** **Genuine phase-blocker — YES.** This is an FR-004/FR-011/FR-012 contract conflict, not D-01–D-07.

### H-02 — The calibration lifecycle cannot be implemented from the stated contracts

- **References:** PRD `prd.md:77-85`; spine sequence `269-292`; ERD `380-386,454-467`; Core API `223-225`.
- **Finding:** The spine now names `CALIBRATION_SAMPLE`, but it does not define criteria/version/item create-edit-list contracts, a conflict-resolution write operation, or the required conditional relationship between `review_scope=CALIBRATION` and `calibration_sample_id`. The calibration sequence also runs before document processing, while `REVIEW_LOG.source_processing_run_id` and `CONFLICT_ITEM.source_processing_run_id` are shown without a nullable calibration rule.
- **Required guard:** Add the complete F1 API lifecycle and request/response/state rules; require reviewer × sample × criterion uniqueness and ownership; define conflict resolution; and make processing-run/source fields nullable or separately typed for calibration records.
- **Disposition:** **Genuine phase-blocker — YES** for F1 parallel implementation and FR-001–FR-004 acceptance.

### H-03 — “No evidence” is not a first-class mapping result

- **References:** PRD `prd.md:143-146,160-165`; spine `AD-2:101-107`, `AD-6:132-139`; ERD `444-452`; evidence API `219-222`.
- **Finding:** The PRD requires every confirmed presentation input to expose either a criterion mapping or explicit `근거 없음`/unverifiable status. `EVIDENCE_MAPPING` only has identity and `is_current`; it has no outcome, reason, or failure-to-find state. `UNVERIFIABLE` exists only as a reviewer status, so a missing mapping can still be silently absent or look like successful evidence.
- **Required guard:** Add a canonical mapping outcome such as `VERIFIED`, `NO_EVIDENCE`, and `UNVERIFIABLE`, with required reason/error fields and citation cardinality rules. Ensure the read model renders every criterion row and never treats an absent citation as verified evidence.
- **Disposition:** **Genuine phase-blocker — YES** for F2 and FR-006–FR-008/FR-012b implementation readiness.

### H-04 — Current-result promotion is not enforceable at the data boundary

- **References:** spine `AD-7:141-149`, `AD-10:170-177`; ERD `408-428,444-452`; Core API `220-233`.
- **Finding:** The rules require only the latest successful processing run and one current mapping per `(application, criteria version, criterion)`, but the ERD provides only a boolean `is_current` and no uniqueness/partial-current constraint, promotion token, or serialized transition rule. Two retries can therefore both become current while satisfying the prose. The handoff/read contract can then select a different current mapping than the run used to create the card.
- **Required guard:** Define legal run transitions, uniqueness for logical runs and current mappings, atomic compare-and-promote semantics, and a read rule that binds every official projection to the exact `source_processing_run_id` and normalized hash captured at creation.
- **Disposition:** **Genuine phase-blocker — YES** for evidence integrity and FR-012b/FR-018.

### H-05 — Interview-question safety and quality are not enforceable

- **References:** PRD `prd.md:121-139`; spine `AD-5:123-130`, question contract `201-213`, ERD `500-525`; companion `95-97`.
- **Finding:** The spine enforces provenance, edit history, soft deletion, and selection, but not the PRD’s required multiple-candidate behavior, verifiability, specificity, non-leading/fair wording, duplicate minimization, or the prohibition on asserted facts and automated hiring conclusions. The nullable `criteria_item_id`/`conflict_item_id` fields and free-text `question_text`/`concern_text` do not provide a generator/output validator.
- **Required guard:** Define a structured candidate-generation schema and server validation before persistence: verification target, reason, required provenance, neutral-question form, protected-trait/privacy rejection, duplicate-similarity check, and explicit prohibition of hiring conclusions/new facts. Keep D-01 limited to the final count.
- **Disposition:** **Genuine phase-blocker — YES** for F3 acceptance; this is not deferred by D-01.

### H-06 — The 90-second demo is described but not fully executable from the API/fixture contract

- **References:** PRD `prd.md:187-195,230-236`; spine demo contract `237-246`, Core API `219-231`, source tree `571-595`; companion `113-129`.
- **Finding:** The storyboard requires a processing-status list, representative-application selection, latest successful evidence, two saved reviewer views, visible disagreement, and a generated handoff/question state. The spine defines only single-application status retrieval and does not specify a list/selection endpoint, pre-seeded fixture contract, or the exact `COMPLETED`/review-data preconditions for the `/review` entry point. D-02 defers dataset size, not these executable demo preconditions.
- **Required guard:** Define the demo fixture seed and status-list/read APIs, including an approved criteria version, completed application, latest successful run, both reviewer logs/citations, conflict, handoff, and candidate lifecycle state. Keep dataset quantity/preprocessing deferred under D-02.
- **Disposition:** **Genuine phase-blocker — YES for demo-readiness validation;** not a blocker to the deferred dataset choice itself.

### H-07 — Presentation companion topology is not explicitly a projection of the spine

- **References:** spine `Design Paradigm:44-86`, capability map `600-606`; companion `19-75`.
- **Finding:** The spine routes the API through `Evidence Matcher Service` before the pipeline (`76-83`), while the companion draws `ROUTER --> PIPELINE` directly and omits that service. The companion also compresses component names without labeling the edges as presentation-only simplifications.
- **Required guard:** Either show the evidence service in the companion or explicitly mark the direct edge and aliases as a presentation projection whose canonical topology is the spine.
- **Disposition:** **Genuine phase-blocker — NO.** This is a presentation-reconciliation item; defer only if the spine remains the sole implementation source of truth, and close before the final presentation artifact is used for build coordination.

### H-08 — Operational/environmental envelope remains under-specified

- **References:** spine `AD-9:159-168`, Stack `250-265`, processing rule `141-149`, Deferred `610-622`; PRD `prd.md:146-149,230-236`.
- **Finding:** Local SQLite, single writer, retries, and server-side configuration are named, but startup/migration/bootstrap, file/database roots, admission limits, health/readiness, browser-to-API topology, artifact retention/cleanup, and deployment exposure are not closed or separately deferred with owners and revisit gates. The reviewer rubric treats a silent operational dimension as a gate finding.
- **Required guard:** Declare the demo topology and limits (single process/worker, local storage, CORS/proxy, PDF size/page bounds), startup migration/recovery, health check, redacted diagnostics, and retention/cleanup. Mark production deployment/retention/scale explicitly as deferred where appropriate.
- **Disposition:** **Genuine phase-blocker — CONDITIONAL.** It blocks implementation handoff if a publicly clickable/deployed demo is in scope; otherwise it is a deferred demo-operations gate, not a product FR blocker.

### H-09 — Artifact lifecycle metadata is not finalized

- **References:** spine front matter `1-10`; PRD front matter `1-7`; spine `13.2:274-276`, `15:309-311`.
- **Finding:** The PRD is `status: final`, but the architecture spine remains `status: draft` while its own text says no active phase-blocker remains and recommends downstream implementation. This prevents the architecture artifact from being treated as a finalization output even if the substantive findings are later resolved.
- **Required guard:** After the substantive contract fixes and a passing gate, set the spine lifecycle status to `final` and record the finalization event. This review does not make that edit.
- **Disposition:** **Genuine phase-blocker — NO.** Process/finalization metadata, not a deferred product decision.

## FR-001–FR-022 reconciliation summary

- **Contractually close enough:** FR-006, FR-008, FR-009, FR-010, FR-013, FR-015, FR-017, and FR-021 have direct supporting rules, entities, and endpoint intent.
- **Partial or blocked by findings:** FR-001–FR-005 (H-02), FR-007 (H-03/H-04), FR-011–FR-012b (H-01/H-03/H-04), FR-014 and FR-016 (H-06 plus handoff read-model detail), FR-018 (H-01/H-04), and FR-019–FR-022 (H-05).
- **FR-012a:** correctly treated as future scale rather than a real-time 200-document MVP requirement; no phase-blocker from the volume itself.

## Deferred-item disposition

PRD D-01 through D-07 are carried by ID in spine `610-620` and align with PRD `278-286`. Their content is appropriately deferred: question count, demo dataset composition, PB-02/DEL-003, problem-card evidence, repository/deployment links, timing measurement, and coordinate-highlight support. None is, by itself, a current PRD-finalization blocker. D-02 does not excuse the missing executable demo fixture/API contract in H-06, and D-07 does not excuse the mandatory snippet/page/context fallback.

## Gate checks

- All FR IDs, including FR-012a/FR-012b, are listed in spine front matter (`11-35`).
- AD-1 through AD-11 each contain `Binds`, `Prevents`, and `Rule` fields.
- The stack names real/current core releases and model capabilities as of this review ([Next.js](https://nextjs.org/blog), [FastAPI](https://fastapi.tiangolo.com/pt/release-notes/), [Pydantic](https://github.com/pydantic/pydantic/releases), [React-PDF](https://www.npmjs.com/package/react-pdf), [OpenAI model page](https://developers.openai.com/api/docs/models/gpt-5.6-luna)); however, clean-install/lockfile verification cannot be performed because implementation manifests and lockfiles are not present in the reviewed workspace. The spine’s exact runtime/version commitments should be validated during the technology-lock step before build.
- No source implementation was present to ratify brownfield conventions; this is therefore a documentation/build-substrate gate.
