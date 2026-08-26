# Final Rubric / Reconciliation Review — R3

**Review date:** 2026-08-27  
**Gate result:** **REVISE — not finalization-ready**  
**Scope:** Current content only. Reviewed exactly these three source artifacts; old review files were not used and source artifacts were not edited.

## Executive decision

The PRD, architecture spine, and presentation companion are directionally aligned: the approved-criteria gate, exact-source evidence mapping, reviewer-conflict preservation, human-controlled interview questions, PDF → LlamaParse Markdown processing, and the six-step 90-second demo all appear in the current set.

The gate cannot pass because several contracts are not independently implementable or are internally contradictory. There are **no identified fatal product-direction contradictions**, but there are **14 high findings**, of which **13 are phase-blockers** for finalization or the relevant implementation/demo phase; H-10 is deferred until the demo asset freeze. Resolve the phase-blockers, then rerun this gate.

## High findings

### H-01 — Architecture artifact is still marked draft

- **Severity:** High
- **Classification:** Phase-blocker — finalization gate
- **Evidence:** `ARCHITECTURE-SPINE.md:8` says `status: draft`; the PRD says `status: final` (`prd.md:5`) and claims there is no next-phase blocker (`prd.md:274-276`).
- **Problem:** The artifact status contradicts the requested finalization state and the PRD’s declared state.
- **Required closure:** After the substantive findings below are resolved, set one canonical architecture status and update the PRD’s finalization statement so the two documents cannot report different lifecycle states.

### H-02 — Artifact-set invariant conflicts with calibration-review scope

- **Severity:** High
- **Classification:** Phase-blocker — F1/provenance
- **Evidence:** `ARCHITECTURE-SPINE.md:181-188` says every `ReviewLog` belongs to `(application_id, criteria_version_id, source_processing_run_id, normalized_markdown_hash)`. The ERD allows `REVIEW_LOG.source_processing_run_id` to be nullable for calibration (`:574-588`), while `AD-1` separately defines calibration reviews over `CALIBRATION_SAMPLE` (`:92-99`).
- **Problem:** A calibration review is a distinct pre-approval scope, but AD-10 describes the application artifact tuple as universal. An independent implementation cannot tell whether a calibration log may omit the application processing artifact or must manufacture one.
- **Required closure:** Define two explicit provenance scopes: calibration scope keyed by criteria version/sample/item/reviewer, and application scope keyed by the official artifact set. State which entities may be nullable in each scope and ensure approval/handoff queries use the correct scope.

### H-03 — Handoff-to-conflict membership is shown but not persisted

- **Severity:** High
- **Classification:** Phase-blocker — F3 / FR-014, FR-015, FR-018
- **Evidence:** The ERD draws `HANDOFF_CARD ||--o{ CONFLICT_ITEM` (`:417-421`), but `CONFLICT_ITEM` has no `handoff_card_id` and no join entity (`:596-610`).
- **Problem:** The model cannot persist which conflict snapshot belongs to a particular handoff card. Re-querying all application conflicts later can change a historical card and violate AD-10’s immutable artifact-set claim.
- **Required closure:** Add an explicit handoff-conflict membership FK/join with the same source revision/artifact-set checks, and specify whether the card stores a snapshot or a live projection.

### H-04 — Required interview-question metadata is not represented in the candidate entity

- **Severity:** High
- **Classification:** Phase-blocker — F3 / FR-019, FR-020
- **Evidence:** `AD-13` requires `verification_target` and `reason` (`:198-204`), and the PRD requires each candidate’s reason, linked criterion, and reference evidence (`prd.md:121-139`). `INTERVIEW_QUESTION_CANDIDATE` contains `criteria_item_id`, `concern_type`, and `concern_text`, but no explicit `verification_target` or `reason` (`ARCHITECTURE-SPINE.md:623-644`).
- **Problem:** The current schema does not guarantee that the UI/API can display the required “why this question” and “what exactly it verifies” fields as distinct, auditable values.
- **Required closure:** Add explicit persisted fields or define a precise mapping from existing fields, then include the request/response schema and validation rules. `QUESTION_EVIDENCE` must remain the reference-evidence relation.

### H-05 — Interview-question generation has conflicting endpoint contracts

- **Severity:** High
- **Classification:** Phase-blocker — F3 / FR-019
- **Evidence:** The candidate contract names `POST /api/handoff/{handoff_id}/questions/generate` (`:224-230`), but the detailed API paragraph names `POST /api/{handoff_id}/questions/generate` (`:261-263`). Separately, `POST /api/handoff/generate` is said to create the card and initial candidates atomically (`:255`, `:263`).
- **Problem:** The canonical route and the lifecycle are ambiguous: an implementer cannot know whether initial candidates are created by handoff generation, a second call, or both.
- **Required closure:** Choose one canonical route spelling and define one lifecycle: either handoff creation always creates initial candidates, or candidate generation is a separate required operation. Specify replay, duplicate, and failure behavior for both paths.

### H-06 — Question-selection authorization contradicts itself

- **Severity:** High
- **Classification:** Phase-blocker — F3 / FR-021 / authorization
- **Evidence:** The candidate table says “검토자가 선택” (`:230`), and the following paragraph limits mutation to any role with current handoff access (`:232`). `AD-5` says only `LEAD` selects (`:127-131`), and the API role rule also says `LEAD` selects (`:289`).
- **Problem:** The same endpoint has at least three possible authorization interpretations. This can produce either an unauthorized state change or a demo flow that cannot be completed by the stated actor.
- **Required closure:** Make the role matrix canonical at the endpoint table, state explicitly whether HR/TECH may edit/delete and whether only LEAD may select, and align the Mermaid flow and presentation labels.

### H-07 — Editing a selected question has no stale-verification rule

- **Severity:** High
- **Classification:** Phase-blocker — F3 / FR-017, FR-021
- **Evidence:** Selected-question edits are allowed while revisions are append-only (`:128`, `:232`); verification binds to an exact `question_revision_id` (`:156-158`, `:284`). No rule states whether editing a selected question invalidates its prior verification or whether decision validation must require the latest selected revision.
- **Problem:** A decision can be associated with a newer question text while satisfying verification for an older revision, or the UI can show a selected question whose verification is stale.
- **Required closure:** Define the state transition after edit: require re-selection/re-verification for the new revision, or freeze selected question text. Make decision validation require the current selected revision’s terminal verification.

### H-08 — Demo fixture does not guarantee a clickable evidence path

- **Severity:** High
- **Classification:** Phase-blocker — demo freeze / FR-006..FR-010
- **Evidence:** The seed contract permits every mapping outcome to be `VERIFIED`, `NO_EVIDENCE`, or `UNVERIFIABLE` (`:302`) but does not require at least one `VERIFIED` mapping with an attached citation and displayable page/block/snippet location.
- **Problem:** A valid seed can produce no citation for the 25-second “click citation → inspect source” step, so the required 90-second demo is not guaranteed by the fixture contract.
- **Required closure:** Require at least one `VERIFIED` mapping with one citation, exact substring/hash validation, and a renderable location. If fallback is demonstrated, require a second known fallback fixture; otherwise state that fallback is tested but not part of the golden path.

### H-09 — Demo fixture does not guarantee the application-level disagreement story

- **Severity:** High
- **Classification:** Phase-blocker — demo freeze / FR-015
- **Evidence:** The seed requires “one or more `OPEN ConflictItem`” (`:302`) but does not require `review_scope=APPLICATION`, two distinct HR/TECH application review logs, discrepant statuses/evidence, or inclusion of that conflict in the selected handoff.
- **Problem:** The open conflict could be a calibration conflict or an unrelated application conflict, leaving the 15-second “two reviewers’ disagreement and evidence” step empty.
- **Required closure:** Mark the golden fixture conflict as application-scoped, require both reviewer logs and their citations, and require the selected handoff to include that exact conflict membership.

### H-10 — Representative-application selection remains nondeterministic for the demo

- **Severity:** High
- **Classification:** Deferred D-02; phase-gate before demo asset freeze
- **Evidence:** The contract says `/review` selects one representative application (`:293-302`), while D-02 leaves the file count and representative-selection criterion undecided (`:302`, `:748-749`; PRD `:153`, `:280-281`).
- **Problem:** A changing fixture set can cause the click path to open a different application or an application without the required citation/conflict state.
- **Required closure:** Before demo asset freeze, add an explicit fixture marker or deterministic selection rule and bind the six-step storyboard to that application. This is intentionally deferred now, but it is a hard demo-entry condition.

### H-11 — LlamaParse uses a moving parser version in a reproducibility-sensitive pipeline

- **Severity:** High
- **Classification:** Phase-blocker — F2 / FR-012b, FR-018
- **Evidence:** `AD-6` instructs `parsing.create(... version="latest")` while recording the provider-resolved version (`:133-140`); the stack describes the SDK version, not a pinned parser version (`:306-322`).
- **Problem:** Recording the resolved version explains a run after the fact but does not make a later re-run deterministic. The same PDF can produce different Markdown offsets and citations as “latest” changes.
- **Required closure:** Pin the parser version for the MVP, or define an explicit resolved-version lock/fail-closed rule and the reprocessing contract when the provider version changes.

### H-12 — API field names drift between `mode`, `artifact_mode`, and `preview_mode`

- **Severity:** High
- **Classification:** Phase-blocker — F2 / FR-011, FR-012b
- **Evidence:** Upload accepts `mode` and application/run entities store `artifact_mode` (`:243`, `:483-484`, `:514-515`); status lookup says it returns `mode` (`:245`); preview rules use `preview_mode` (`:261`); the presentation summary also uses `PREVIEW|OFFICIAL` (`PRESENTATION-SYSTEM-DESIGN.md:140`).
- **Problem:** The guardrail’s canonical state field is ambiguous across persistence, API, and UI. A client can display or submit a value that does not match the server’s authorization query.
- **Required closure:** Select one canonical wire name and one canonical persisted name, define the mapping if they differ, and include it in the standard response envelope and preview rejection tests.

### H-13 — Core ERD references undeclared identity/ownership entities

- **Severity:** High
- **Classification:** Phase-blocker — architecture implementation readiness / FR-001, FR-002, FR-013, FR-016
- **Evidence:** `POSITION` is used in relationships and foreign keys (`:396-399`, `:437-438`, `:476-478`) but has no entity definition. `reviewer_id`, `created_by`, `updated_by`, `recorded_by`, and `approved_by` are FK-like fields, but no canonical principal/actor target is defined; `DEMO_PRINCIPAL` is present but not declared as their target (`:400`, `:454-467`, `:574-587`, `:623-644`, `:661-677`).
- **Problem:** Independent implementations cannot establish the position scope or enforce actor ownership consistently.
- **Required closure:** Define `POSITION` and the principal/actor relationship, including the single-workspace assumption, role constraints, and which identity fields are derived from the demo session.

### H-14 — Question-safety validation is normative but not executable enough

- **Severity:** High
- **Classification:** Phase-blocker — F3 / FR-022
- **Evidence:** The PRD requires non-leading, fair, specific, privacy-safe questions (`prd.md:129-139`), and `AD-13` says the server validates those properties (`ARCHITECTURE-SPINE.md:202-204`), but no schema constraints, rejection criteria, canonical error code, or validation test cases are defined.
- **Problem:** “Validate” is not sufficient for independent implementation of a safety boundary; the model can emit a question that passes structural checks but violates the stated safety contract.
- **Required closure:** Define deterministic checks and/or a required human-review state, the rejection/error behavior, prohibited patterns, and acceptance tests. Preserve the rule that a question cannot assert a new fact or make an automated hiring decision.

## FR-001..FR-022 reconciliation

| FR | Current result | Current evidence / gate note |
|---|---|---|
| FR-001 | Traceable; revise H-13 | Criteria version and position relationships are defined, but `POSITION` is not fully modeled. |
| FR-002 | Traceable; revise H-02/H-13 | Independent HR/TECH review logs and calibration rules exist; calibration provenance and reviewer identity need explicit scope. |
| FR-003 | Pass in behavior | Deterministic status/evidence diff and canonical `ConflictItem` are specified in `AD-3:109-115`. |
| FR-004 | Pass in behavior | Preview-only processing and approval blocking are specified in `AD-1:96-99` and API error handling `:271-273`. |
| FR-005 | Pass in behavior | Immutable criteria ID binding and approved-version gating are specified in `AD-1` and `AD-10`. |
| FR-006 | Traceable; revise H-08 | Exact evidence mapping and citation entities exist; the golden fixture does not guarantee a citation to click. |
| FR-007 | Pass in contract | Markdown block/page/offset/hash plus snippet/context fallback are specified in `AD-2:105-107`. |
| FR-008 | Pass in contract | Exact substring validation and no partial/summary output are specified in `AD-2` and `AD-6`. |
| FR-009 | Pass in contract | Split-view UI is present in both architecture diagrams and the presentation companion. |
| FR-010 | Traceable; revise H-08/H-12 | Active citation sync and fallback exist; the fixture and canonical mode field need closure. |
| FR-011 | Traceable; revise H-12 | Approved-version and preview-only downstream guards exist, but preview state naming drifts. |
| FR-012 | Traceable; revise H-11 | PDF → LlamaParse → Markdown is explicit; parser version pinning is not. |
| FR-012a | Deferred-compatible | The 200-application requirement is correctly treated as future scale; the MVP worker is bounded. |
| FR-012b | Traceable; revise H-08/H-11/H-12 | Artifact tracking, failure states, and fallback are specified; reproducible parser/version and demo evidence guarantees remain open. |
| FR-013 | Pass in contract | Reviewer status and reason are persisted in `REVIEW_LOG`. |
| FR-014 | Traceable; revise H-03/H-04 | Handoff read projection lists required content, but conflict membership and question reason/target persistence are incomplete. |
| FR-015 | Traceable; revise H-03/H-09 | Independent reviewer logs and conflict projection exist; historical handoff membership and golden-fixture conflict scope are not guaranteed. |
| FR-016 | Pass in role contract | LEAD read access to official handoff/question resources is stated. |
| FR-017 | Traceable; revise H-07 | Interview verification and hypothesis/finding separation exist; selected-question revision freshness is undefined. |
| FR-018 | Traceable; revise H-02/H-03/H-07/H-11 | Version, artifact set, revisions, and citations are designed, but several persistence/reproducibility boundaries remain ambiguous. |
| FR-019 | Revise H-04/H-05/H-14 | Candidate generation is present and count is deferred, but lifecycle, metadata persistence, and safety validation are not final. |
| FR-020 | Revise H-04/H-14 | Criterion/concern and citation relationships exist, but explicit reason/verification-target storage and executable safety checks are missing. |
| FR-021 | Revise H-05/H-06/H-07 | Edit/delete/select operations exist, but route, role authority, and post-edit verification semantics conflict or are incomplete. |
| FR-022 | Revise H-14 | Human-controlled, no-auto-decision intent is clear; the enforceable validation contract is incomplete. |

## Deferred D-01..D-07 reconciliation

| Deferred | Result | Classification and required timing |
|---|---|---|
| D-01 — exact interview-question candidate count | Aligned | Deferred by both documents; exact count must be fixed before F3 implementation, while the data model remains count-independent. H-04/H-14 are separate non-deferred contract requirements. |
| D-02 — demo dataset quantity and composition | Aligned but operationally incomplete | Deferred until demo asset creation. H-08, H-09, and H-10 must be closed before the golden fixture/demo freeze; synthetic/de-identified PDF remains mandatory. |
| D-03 — baseline reproducibility contract (PB-02) | Mostly aligned | Deferred and non-blocking for the core MVP. The spine repeats 5×3 and metadata preservation but omits the PRD’s seven comparison criteria; carry that detail into the future PB-02 deliverable contract. |
| D-04 — final problem-card evidence | Aligned | Deferred until submission; current candidate sources are appropriately labeled as unverified and not direct Korean resume-review evidence. |
| D-05 — repository/deployment links | Aligned | Deferred until submission; not a core architecture blocker. |
| D-06 — “within two minutes” metric | Aligned | Deferred until demo validation; measurement inputs and adjudication method must be fixed then. |
| D-07 — supported PDF coordinate-highlight range | Aligned | Deferred for BBox coverage only. Snippet/page/context fallback, worker compatibility, and Korean-PDF smoke validation are correctly non-deferred MVP contracts. |

## Demo fixture and 90-second flow

The timing arithmetic is correct and aligned across documents:

`10 + 10 + 25 + 15 + 10 + 20 = 90 seconds`.

The six steps match the PRD (`prd.md:189-195`), the spine contract (`ARCHITECTURE-SPINE.md:291-302`), and the presentation storyboard (`PRESENTATION-SYSTEM-DESIGN.md:121-140`). The entry state, processing-status list, citation interaction, conflict review, handoff card, and question adjustment are all named consistently.

The fixture contract is not yet strong enough to guarantee the flow. It must explicitly guarantee the selected application’s evidence citation, the application-scoped two-reviewer conflict, the conflict’s handoff membership, and deterministic representative selection. These are H-08, H-09, and H-10.

## Companion alignment

**Mostly aligned, with two clarification-level drifts:**

- The presentation’s calibration example names only `충족/미충족` (`PRESENTATION-SYSTEM-DESIGN.md:90-93`), while the PRD and spine define four review states including `부분 충족/확인 불가`. This is acceptable as a shortened example only if the presentation explicitly labels it as illustrative.
- The presentation diagram aggregates review/handoff behavior into one service, while the spine capability map and AD-8 assign final-decision ownership to a distinct decision service (`ARCHITECTURE-SPINE.md:152-158`, `:734-740`). Keep the companion summary-level, but label decision ownership consistently.

The shared pipeline, model name, split view, fallback behavior, conflict-preserving handoff, and 90-second storyboard are otherwise aligned.

## Architecture rubric

| Rubric area | Result | Reason |
|---|---|---|
| PRD traceability | Revise | All FRs are named/bound, but FR-019..FR-022 need executable persistence, lifecycle, role, and safety contracts. |
| Decision/invariant quality | Revise | The major guardrails are explicit, but AD-10 overreaches across calibration scope and selected-question freshness is open. |
| Data model/provenance | Revise | Strong hashes/revisions/artifact-set intent; missing handoff-conflict membership and undeclared identity/position targets. |
| API completeness/consistency | Revise | Broad endpoint coverage exists, but question-generation routes/lifecycle and preview-state field names conflict. |
| Failure/idempotency/transaction boundaries | Mostly pass | CAS, retry, rollback, current-run promotion, and standard error envelopes are well specified; question-generation lifecycle needs one canonical contract. |
| Security/role boundaries | Revise | Server-side session/role checks are strong, but question-selection authority is contradictory and identity ownership is under-modeled. |
| Reproducibility | Revise | Run metadata is strong; `version="latest"` undermines deterministic parser replay. |
| Demo readiness | Revise | 90-second storyboard is aligned, but the seed contract does not guarantee the evidence/conflict path. |
| Deferred governance | Pass with follow-up | D-01..D-07 are identified and mostly reconciled; D-03 should retain the PRD’s seven comparison criteria in its future contract. |

## Required disposition

1. Resolve H-02 through H-07 and H-11 through H-14 before declaring the architecture final or entering the corresponding implementation phases.
2. Resolve H-08 through H-10 before freezing the demo fixture or claiming the 90-second path is reproducible.
3. Update the finalization status/document statements (H-01).
4. Re-run a fresh reconciliation over the same three current artifacts; do not rely on this report as a substitute for the next gate.

**Final gate:** **REVISE**.
