# PRD ↔ Architecture Spine Reconciliation

Date: 2026-08-27  
Sources: `prd-Zero100_Builderthon-2026-08-25/prd.md` (final), `ARCHITECTURE-SPINE.md` (draft status; updated 2026-08-27)

## Outcome

**Partially aligned.** The spine establishes the main domain boundaries, evidence traceability, deterministic reviewer conflict handling, human-owned decisions, and question-candidate lifecycle. It is not yet a complete implementation contract for every PRD requirement. The gaps below should be resolved before treating the spine as implementation-ready.

## FR-by-FR trace

| PRD | Result | Reconciliation finding |
|---|---|---|
| FR-001 | Partial | Criteria/version entities and bindings exist, but `POSITION` is not defined in the ERD and no criteria/version create, edit, list, or item-management API is specified. |
| FR-002 | Partial | Independent `ReviewLog` records and four statuses are represented, but calibration samples, the two-reviewer completeness/pairing rule, and explicit original-location capture are not modeled as a calibration contract. |
| FR-003 | Partial | Deterministic status/evidence/reason diffs and `ConflictItem` exist, but the conflict record has no reviewer-side values, side-specific citations, or explicit conflict-reason payload; no conflict resolution API/workflow is specified. |
| FR-004 | Partial | Approval is blocked by open conflicts and official handoff creation is gated, but preview result/card state and its watermark/status are not modeled; final-decision gating is not explicit. |
| FR-005 | Partial | Stable criteria-version FKs are present on mappings, reviews, handoffs, and decisions, but version issuance/approval metadata and the invariant that every generated review/handoff projection uses one immutable version snapshot are not explicit. |
| FR-006 | Covered | `EvidenceCitation`, exact-substring validation, and criteria/application mapping directly support original-text citations. |
| FR-007 | Partial | Page, Markdown block, and optional BBox plus fallback are present, but heading/PDF-native location and a persisted/typed fallback representation are not defined in the ERD/API. |
| FR-008 | Covered | The spine requires exact original Markdown substrings and stores snippet text; it does not make an AI summary the evidence source. |
| FR-009 | Covered | Split-view UI, PDF viewer, criteria panel, and synchronization contract are identified. |
| FR-010 | Covered | `active_citation_id`, focus payload, BBox/page behavior, and snippet/context fallback are specified. |
| FR-011 | Partial | The handoff gate is explicit, but `POST /decision` has no stated approved-version guard and preview mode/status is not represented in the output contract. |
| FR-012 | Partial | PDF → LlamaParse → normalized Markdown → grounded extraction is specified and linked by `application_id`; the required approved-version gate versus permitted exploratory preview path is ambiguous. |
| FR-012a | Partial | Scale is deferred and fixture quantity is noted, but the permitted preprocessed/fixed-data demo mode and explicit non-goal of live 200-document processing are not stated. |
| FR-012b | Partial | Raw/normalized documents, processing runs, failure statuses, and fallback intent exist, but location-resolution failure has no distinct status/error path and `DOCUMENT_PAGE` is undefined. |
| FR-013 | Covered | Reviewer status, rationale, reviewer identity/role, and citation relationships are represented. |
| FR-014 | Partial | Related entities can supply the card contents, but no explicit handoff read/projection contract guarantees one-screen inclusion of original, applied criteria, first judgment, unverified questions, and candidate questions. |
| FR-015 | Covered | Separate reviewer logs and reviewer-specific citation joins preserve each opinion and its evidence. |
| FR-016 | Partial | A leader role and handoff UI are named, but no `GET /handoff/{id}` card endpoint or explicit leader read authorization is specified. |
| FR-017 | Covered | `InterviewVerification` separates initial hypothesis, finding, answer notes, and verification status; `DecisionRecord` captures the final human result. |
| FR-018 | Partial | `DecisionRecord` binds application, handoff, and criteria version, but has no direct evidence/citation relation or immutable evidence snapshot proving which exact sources supported the decision. |
| FR-019 | Partial | Candidate generation and provenance fields exist, but “insufficient evidence” is not a first-class source/status, the generation input projection is unspecified, and the D-01 count decision is not carried into the deferred section. |
| FR-020 | Partial | Criteria, concern, and citation joins support provenance, but nullable schema fields require an explicit DB/API constraint enforcing at least one criterion/concern and required citations for document-fact questions. |
| FR-021 | Covered | PATCH, soft DELETE, SELECTED-only final exposure, and original/current text separation are specified. |
| FR-022 | Partial | Human decision ownership and the prohibition on asserted facts/automatic decisions are stated, but no generated-question schema validation or review guard checks that each output is a neutral verification question. |

## Cross-cutting findings

1. **Priority/dependency traceability is missing.** The PRD prioritizes F3 → F1 → F2 for user value but requires execution dependency F1 → F2 → F3. The spine shows the execution sequence but does not preserve the P1/P2/P3 distinction or identify the critical-path rationale.

2. **Approved versus preview processing needs an explicit state model.** The PRD simultaneously permits exploratory results on an unapproved version and prohibits running the evaluation pipeline on an unapproved version. The spine should define separate `PREVIEW` and `OFFICIAL` modes, with preview outputs unable to become official mappings, handoffs, or decisions.

3. **Final-decision gating is incomplete.** AD-1 explicitly blocks official handoff creation, while AD-8/AD-9 only say that a person with permission writes a decision. Add an approved criteria-version check to the decision transaction and endpoint contract.

4. **The PRD guardrails are not all explicit invariants.** Human-owned decisions and deterministic disagreement handling are covered, but no spine rule/API guard explicitly forbids composite scores, ranking, automatic filtering, or automatic accept/reject behavior in UI and backend projections.

5. **Calibration approval lifecycle is underspecified.** Add approval actor/time, version content hash or immutable snapshot, conflict resolution operation, and a rule preventing edits to an approved version.

6. **Evidence location schema is underspecified.** The prose mentions `location` and fallback, but `EVIDENCE_CITATION` only has page/BBox/Markdown block fields. Define heading/paragraph/PDF location semantics and typed fallback fields, including how a location-extraction failure remains viewable without being treated as a successful precise location.

7. **Handoff composition is underspecified.** Add a read-model/API contract for the single-screen card, including explicit first-judgment, unresolved-evidence/unverified-question, reviewer-opinion, conflict, and selected-question projections.

8. **Role authorization is not endpoint-complete.** Specify read access for HR, Tech Reviewer, and Lead, plus who may approve criteria, resolve conflicts, generate/edit/select questions, record verification, and record the final decision. The current “role toggle” deferred substitute must not be mistaken for authorization enforcement.

9. **Audit/replay data is incomplete for the decision path.** `ProcessingRun` records runtime model ID and request metadata, but no direct decision evidence join, prompt/version/parameters for question generation, raw structured model response, or model snapshot identifier is defined. This weakens PRD auditability and reproducibility.

10. **Model decision is only partially synchronized.** Both documents name `gpt-5.6-luna`, but the spine does not require startup/fixture validation of account availability, exact API model snapshot pinning, or a fail-closed/no-silent-substitution behavior. Add these to configuration and processing-run contracts.

11. **Baseline deferral is not fully scoped.** PB-02 is deferred, but the spine does not preserve the PRD’s future contract: five representative cases × three runs, seven comparison criteria, exact prompt/parameters/input, raw response, timestamp, and request ID.

12. **Idempotency is asserted but not operationalized.** The API section requires idempotent upload/retry/question generation and latest-success activation, yet no idempotency-key persistence, uniqueness scope, or response-replay contract is modeled.

13. **Demo data safety is absent from the spine.** The PRD requires synthetic/de-identified PDFs and no real names/PII. The fixture directory is named, but an explicit fixture policy and validation gate are missing.

14. **The 90-second behavior is not represented.** The spine has the broad sequence but omits the timed six-step path: approved-version confirmation (10s), status-list selection (10s), evidence/fallback inspection (25s), reviewer disagreement (15s), handoff open (10s), and candidate edit/delete/select (20s).

15. **The demo entry points are missing.** No application status-list endpoint, representative-application selection behavior, pre-seeded approved criteria/data contract, or “already processed/fixed demo data” route is specified. The pipeline sequence alone does not guarantee the PRD’s clickable demo can complete in 90 seconds.

16. **Deferred-item parity is incomplete.** The spine’s Deferred section covers queue, PB-02, operations/deployment, worker version, ATS, and SSO, but does not explicitly carry PRD D-04 (problem-card evidence), D-05 (repo/deployment links), or D-06 (2-minute metric), and only partially carries D-01 (question count), D-02 (dataset composition), and D-07 (coordinate support decision). Mark these as PRD-owned deferred items with decision timing.

17. **Metadata status conflicts with the requested artifact state.** The file says `status: draft`, while the PRD is final and calls the architecture synchronized. If “finalized candidate” is intentional, update the lifecycle metadata in a later authorized change; this review does not modify the spine.

## Required reconciliation decisions

- Define `PREVIEW` versus `OFFICIAL` processing and enforce approved-version gating for official mappings, handoffs, and decisions.
- Add explicit API/ERD contracts for calibration samples/conflict resolution, handoff read composition, leader access, evidence fallback/location failures, and decision evidence links.
- Make all PRD guardrails and question-quality constraints enforceable at the backend boundary, not only prose rules.
- Carry D-01 through D-07 and the PRD’s model/baseline/demo acceptance conditions into the architecture’s deferred and demo contracts.

