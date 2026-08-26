# Final Rubric/Reconciliation Review — R4

Date: 2026-08-27  
Scope: current source documents only; prior review files were ignored.

Reviewed:

- `C:\Users\kimsu\BLDT_BMAD\_bmad-output\planning-artifacts\architecture\architecture-Zero100_Builderthon-2026-08-26\ARCHITECTURE-SPINE.md`
- `C:\Users\kimsu\BLDT_BMAD\_bmad-output\planning-artifacts\architecture\architecture-Zero100_Builderthon-2026-08-26\PRESENTATION-SYSTEM-DESIGN.md`
- `C:\Users\kimsu\BLDT_BMAD\_bmad-output\planning-artifacts\prds\prd-Zero100_Builderthon-2026-08-25\prd.md`

## Verdict

# REVISE/FAIL

The documents are broadly reconciled, but this is not a clean PASS. Three unresolved interoperability issues remain in the architecture contracts and should be resolved before implementation proceeds. No Critical-severity issue was found; the open issues below are High.

Only H-01 through H-03 are classified as phase-blockers because they are unresolved interoperability issues. D-01 through D-07 remain deferred items where the documents explicitly defer them; they are not reclassified as phase-blockers.

## Critical/high findings

### H-01 — Conflict identity is not representable in the declared data model

Severity: High  
Classification: Phase-blocker — interoperability

Evidence: `ARCHITECTURE-SPINE.md:109-115` defines the canonical `ConflictItem` identity with `review_pair_revision`. The `CONFLICT_ITEM` entity at `ARCHITECTURE-SPINE.md:672-690` has no `review_pair_revision` field, and the persistence contract at `:316-323` does not define an equivalent mapping.

Impact: independent implementations cannot deterministically persist, recompute, reopen, or snapshot the conflict revision used by approval and handoff generation. Two logically different review-pair revisions can be represented ambiguously.

Required correction: either add `review_pair_revision` throughout the ERD, persistence constraints, API payloads, and fixture contract, or explicitly declare that `revision_no` is the canonical review-pair revision and update AD-3, the ERD, and all uniqueness rules consistently.

### H-02 — “Exactly one current” constraints are stated but not enforceably specified

Severity: High  
Classification: Phase-blocker — interoperability

Evidence: `ARCHITECTURE-SPINE.md:98-99,115` requires one current review pair and one current conflict. The persistence rules at `:318-319` define uniqueness including `revision_no` or `source_processing_run_id`, but do not define a partial/current uniqueness constraint for `is_current=true` at the logical application/version/criterion scope.

Impact: multiple rows can be marked current after a revision or processing retry. “Latest current” selection can then diverge between implementations, causing approval, evidence display, handoff snapshots, and the golden demo fixture to use different records.

Required correction: specify atomic supersession plus enforceable unique-current indexes for calibration reviews, application reviews, conflicts, and evidence mappings; define the exact key for each scope and make API reads use that current marker rather than an implicit timestamp/latest query.

### H-03 — Calibration review provenance does not close the FR-002 location contract

Severity: High  
Classification: Phase-blocker — interoperability

Evidence: PRD `FR-002` at `prd.md:77-79` requires each reviewer to enter status and original location independently. The architecture’s citation location contract at `ARCHITECTURE-SPINE.md:101-107` depends on `source_processing_run_id`, while `REVIEW_LOG.source_processing_run_id` is nullable for calibration at `:645-664`; the calibration review API at `:286` and sequence at `:380-385` do not define the required preview processing run/citation handoff.

Impact: an implementation can accept a calibration status without a reproducible source location, or it can require a citation that the declared calibration API flow never creates. FR-002, FR-003, and approval-time provenance are therefore not interoperable across the UI, API, and persistence layers.

Required correction: make calibration samples depend on a completed preview processing run and require review citations against that run, or add an explicit structured location contract to calibration reviews. Update the API schema, ERD nullability, approval query, and demo seed prerequisites together.

### H-04 — Document status and next-phase readiness are inconsistent

Severity: High  
Classification: Readiness issue; not a phase-blocker under the requested classification

Evidence: the PRD is marked `status: final` at `prd.md:1-7` and declares no phase-blockers at `:274-276`, while the architecture spine remains `status: draft` at `ARCHITECTURE-SPINE.md:1-10`. The PRD next step at `prd.md:309-311` proceeds to UX, stories, and implementation while architecture finalization is described as optional follow-up.

Impact: the repository has no unambiguous statement about whether the build substrate is approved for implementation.

Required correction: after H-01 through H-03 are resolved, mark the architecture final or add an explicit architecture-finalization gate before implementation. Do not retain “no phase-blocker” language while the build substrate is draft and its contracts are unresolved.

### H-05 — Golden fixture minimum does not guarantee the storyboard’s question actions

Severity: High  
Classification: Demo-readiness issue; D-01 remains deferred and is not a phase-blocker

Evidence: the PRD storyboard requires question candidate modification, deletion, and selection at `prd.md:189-195`. The golden fixture contract at `ARCHITECTURE-SPINE.md:329-340` requires only candidate question state, while exact candidate count is deferred as D-01 at `prd.md:121,139` and `ARCHITECTURE-SPINE.md:851-856`.

Impact: a minimally valid seed can contain too few candidates to demonstrate all required click actions, making the claimed 90-second demo non-deterministic.

Required correction: retain D-01 for the exact final count, but add a fixture minimum that guarantees the scripted edit/delete/select path, with deterministic candidate IDs and source revision. Resolve the exact count before F3 implementation as already stated.

## FR-001..FR-022 reconciliation

| Requirements | Result | Evidence / qualification |
|---|---|---|
| FR-001 | Covered | Criteria version entity and AD-1/AD-9; no open semantic gap beyond H-02 current-row enforcement. |
| FR-002 | Covered with blocker | Independent HR/TECH review is specified; calibration location provenance remains open in H-03. |
| FR-003 | Covered with blockers | Deterministic conflict calculation exists in AD-3; persistence identity/currentness are open in H-01/H-02. |
| FR-004 | Covered | Preview-only behavior and approval gating are explicit in AD-1 and the API matrix. |
| FR-005 | Covered | Immutable criteria version binding is explicit in AD-1/AD-10. |
| FR-006 | Covered | Exact evidence citation and mapping contracts are defined in AD-2/AD-6/AD-13. |
| FR-007 | Covered | Markdown block/page/location plus snippet/context fallback are defined. |
| FR-008 | Covered | Exact substring validation prevents generated summaries from serving as evidence. |
| FR-009 | Covered | Split-view UI and active citation synchronization are defined in AD-4 and both architecture documents. |
| FR-010 | Covered | Immediate citation focus with BBox or fallback rendering is specified. |
| FR-011 | Covered | Official downstream creation is gated on approved criteria and official completed runs. |
| FR-012 | Covered | PDF → LlamaParse → Markdown pipeline and source linkage are explicit. |
| FR-012a | Covered/deferred correctly | 200-document throughput is explicitly future scope; demo data may be fixed/preprocessed. |
| FR-012b | Covered | Processing status, failure isolation, source fingerprint, and fallback are specified. |
| FR-013 | Covered | Review status/reason persistence is defined in AD-3/AD-10. |
| FR-014 | Covered | Handoff card response and fixture contract include the required evidence and questions. |
| FR-015 | Covered with blockers | Reviewer disagreement is preserved; deterministic current conflict representation remains open in H-01/H-02. |
| FR-016 | Covered | LEAD read/access behavior is defined in AD-9/AD-12 and the API contract. |
| FR-017 | Covered | Interview verification, hypothesis snapshot, and finding comparison are defined in AD-8. |
| FR-018 | Covered | Criteria/source/revision and append-only decision provenance are specified. |
| FR-019 | Covered/deferred correctly | Generation basis and multiple candidates are specified; exact count is D-01. |
| FR-020 | Covered | Criterion/concern/reason/citation linkage is required by AD-5/AD-13. |
| FR-021 | Covered with demo qualification | Edit/delete/select permissions and state transitions are defined; golden fixture coverage is H-05. |
| FR-022 | Covered | Safety validation, human selection, and no automatic decision/new-fact assertion are explicit. |

## D-01..D-07 disposition

All seven deferred items are consistently identified in the PRD and architecture spine. They should remain deferred, with their stated decision timing:

- D-01: exact interview-question candidate count; decide before F3 implementation.
- D-02: demo dataset quantity and composition; decide before demo asset production.
- D-03: baseline reproducibility/PB-02; decide when DEL-003 is produced.
- D-04: final problem-card evidence; decide before the submission card is finalized.
- D-05: repository/deployment links; decide before submission.
- D-06: two-minute auxiliary metric; decide before demo verification.
- D-07: supported PDF BBox range; keep snippet/page/context fallback mandatory and decide supported range after fixture/worker validation.

None of D-01..D-07 is reclassified as a phase-blocker. H-05 is a readiness correction associated with D-01, not a demand to resolve the deferred exact count immediately.

## Demo golden fixture

The fixture contract is directionally complete: approved criteria, official completed processing, complete per-criterion outcomes, at least one verified exact/hash citation, current HR/TECH reviews, an open conflict, a conflict snapshot, and candidate questions are all required at `ARCHITECTURE-SPINE.md:329-340`. The fixture is aligned with the PRD’s six-step 90-second flow and deterministic `golden_demo=true` selection.

The remaining gap is H-05: the minimum seed must guarantee the actual edit/delete/select interaction path, not merely the existence of candidate questions.

## Companion alignment

The presentation companion aligns with the spine and PRD on the core stack, PDF → LlamaParse → Markdown pipeline, exact evidence/fallback behavior, role-gated handoff, conflict preservation, and the 90-second sequence. Its backend diagram includes the Decision Service and worker, and its closing implementation note matches the spine’s API, artifact-mode, storage-boundary, and PDF viewer contracts.

One non-gating consistency cleanup remains: the spine’s opening architecture diagram omits the Decision Service even though the companion diagram, structural seed, API contract, and ERD include it. This does not create a separate High finding, but the diagram should be updated when H-01 through H-03 are reconciled.

## Status and next-phase readiness

Current readiness: not ready for implementation sign-off because H-01 through H-03 are unresolved interoperability contracts. UX/story work can use the current behavioral intent, but implementation-facing schemas and fixture work should wait for those three corrections.

Required gate exit:

1. Reconcile conflict identity and current-row uniqueness across invariants, ERD, persistence, APIs, and seed validation.
2. Close calibration review provenance from sample input through preview processing, citation/location, conflict calculation, and approval.
3. Set architecture status to final, or explicitly record the finalization gate before implementation.
4. Lock the D-01 fixture minimum before F3 implementation and verify the D-07 PDF fallback/worker smoke path before demo sign-off.

No source document was edited by this review.
