# Final Adversarial Review r3 — Zero100_Builderthon

## Gate result

**REVISE/FAIL — finalization gate blocked.**

- Critical findings: 2
- High findings: 11
- Phase-blockers: 13
- Accepted/deferred items: D-01 through D-07, subject to the conditions in §6.

The current architecture and presentation documents are materially stronger than a superficial design: they state server-side role derivation, deterministic conflicts, exact-substring validation, source-run tracking, worker ownership, and human-only decisions. However, two independent implementations do not converge on the same behavior for the core trust path. The PRD’s statement that there are no phase-blockers (PRD §13.2) is therefore not supported by the current documents.

Scope was limited to the current contents of:

- `ARCHITECTURE-SPINE.md` (updated 2026-08-27; frontmatter status `draft`)
- `PRESENTATION-SYSTEM-DESIGN.md` (updated 2026-08-27)
- `prd.md` (updated 2026-08-27; frontmatter status `final`)

No old review file was consulted. No source file was edited.

## Independent implementation test

Two implementations were constructed from the documents only:

**Implementation A — single logical run.** One `PROCESSING_RUN` owns parsing and mapping, with `stage` advanced from `PARSING` to `MAPPING`; a retry reuses that logical run. A preview application remains preview-only and an official upload creates a separate application.

**Implementation B — stage-separated run.** Parsing and mapping each receive their own run/attempt record; the same application is promoted from preview to official after criteria approval, and current output is selected by the newest successful run for the source fingerprint.

Both are reasonable readings of the current text. They disagree on the following required cases:

| Contract test | A | B | Result |
|---|---|---|---|
| DRAFT + registered calibration sample + `PREVIEW` upload | Accept | Accept | Converges |
| DRAFT + ordinary application + `PREVIEW` upload | Reject | Reject | Converges |
| DRAFT + `OFFICIAL` upload | Reject | Reject | Converges |
| Preview run after the criteria version later becomes `APPROVED` | Reject by application mode | May accept if only version status is checked | **Diverges; blocker** |
| Parsing succeeds, mapping fails, retry from failed stage | Reuse one run and change `stage` | Create/continue a mapping run | **Diverges; blocker** |
| Retry with same PDF and criteria after a new run ID | New artifact set because run ID is part of identity | Same logical source selected by fingerprint | **Diverges; blocker** |
| Calibration review is edited after a conflict was resolved | Old resolved conflict remains unless explicitly reopened | New review event creates a second conflict or replaces it | **Diverges; blocker** |
| Generate handoff and generate questions | Initial candidates are created in handoff transaction; second endpoint may duplicate them | Handoff creates card, question endpoint creates candidates | **Diverges; blocker** |
| Final decision is revised twice | Two rows exist with no specified current projection | Latest row is treated as current by local convention | **Diverges; blocker** |

This is a specification determinism failure, not an implementation preference: both implementations satisfy substantial portions of the prose while producing different provenance and authorization outcomes.

## Findings

### C-01 — Citation-generation contract is not executable

**Severity:** Critical  
**Classification:** Phase-blocker  
**Evidence:** `ARCHITECTURE-SPINE.md:137-138, 202-203, 547-572`

The mapping pipeline says the model returns `citation_ids[]`, while the citation rows are the output that must be created only after exact-substring and hash validation. The model has no specified field for the exact quote, normalized offsets, page, or block from which a citation ID can deterministically be created. If citation IDs must already exist, the pipeline needs a prior citation-generation step that is not defined; if the model creates them, it cannot refer to IDs that do not yet exist. Implementation A pre-creates placeholder citations; Implementation B returns quote/offset candidates and creates citations afterward. Both fit the prose, but only one can be selected by convention.

**Required gate correction:** define one canonical `GroundedExtraction` schema and order of operations. It must return either exact substring/offset candidates or references to pre-existing, server-created candidate IDs; the server must create and validate citations before persisting `VERIFIED` mappings. Add a deterministic failure test for a fabricated quote and a citation ID from another run.

### C-02 — Preview/official mode is not a type-safe provenance boundary

**Severity:** Critical  
**Classification:** Phase-blocker  
**Evidence:** `ARCHITECTURE-SPINE.md:97-99, 177-185, 243-263, 278-287`

The policy says preview results can never feed official evidence, handoff, verification, or decision, but `APPLICATION.artifact_mode` and `PROCESSING_RUN.artifact_mode` are only ordinary fields; `HANDOFF_CARD` and `DECISION_RECORD` have no mode field or explicit official-only constraint. The documents also do not choose whether approval causes a new official run/application or whether a preview application can be promoted. Consequently, once a DRAFT version becomes APPROVED, an implementation that checks only `criteria_version.status` can reuse a successful preview run as official output. The artifact-set identity also includes `source_processing_run_id`, so a retry necessarily changes the set even when the source PDF, criteria, and normalized hash are identical.

**Required gate correction:** specify an immutable mode on every downstream source revision and make official eligibility an explicit predicate: `criteria.status=APPROVED AND run.mode=OFFICIAL AND run.status=SUCCEEDED AND current tuple matches`. Define preview-to-official as either a new official run or a forbidden promotion; do not leave it to the application table shape. Separate stable source identity/fingerprint from processing-run identity.

### H-01 — Parsing/mapping state and retry lifecycle have conflicting models

**Severity:** High  
**Classification:** Phase-blocker  
**Evidence:** `ARCHITECTURE-SPINE.md:140, 148-150, 509-545`; sequence diagram `353-369`

`PROCESSING_RUN.stage` is a single `PARSING|MAPPING` value, while the worker contract says one run transitions `QUEUED→STARTED→SUCCEEDED|FAILED` and retries start at the failed stage. The attempt entity has no stage, and the text alternates between a single logical run and separate processing executions. There is no canonical transition table for `APPLICATION.processing_status` on retry, worker restart, parser success followed by mapping failure, or stale-heartbeat recovery.

**Required gate correction:** choose either stage rows with explicit parent/source revision or one run with a stage-state subrecord. Specify legal transitions, attempt ownership, recovery after each external side effect, and which status is exposed while a retry is queued.

### H-02 — Calibration can approve without a sample, and conflict lifecycle is incomplete

**Severity:** High  
**Classification:** Phase-blocker  
**Evidence:** `ARCHITECTURE-SPINE.md:99, 280, 596-610`; PRD `FR-002–FR-004`

The approval predicate requires complete reviews for every registered sample, but never requires at least one calibration sample. A zero-sample version can therefore satisfy the universal condition and become `APPROVED`. In addition, `CONFLICT_ITEM` has no uniqueness key, review revision/current marker, or rule for reopening/recomputing a resolved conflict after a reviewer changes a review. Two concurrent review submissions can create duplicate canonical conflicts, and an old `RESOLVED` conflict can remain resolved after the underlying opinions diverge again.

**Required gate correction:** require a non-empty, approval-frozen sample set; add canonical conflict identity and current/revision semantics; define recomputation and reopen behavior transactionally. Add tests for zero samples, duplicate submissions, reviewer edit after resolution, and concurrent writes.

### H-03 — Review completeness and revision semantics are not representable

**Severity:** High  
**Classification:** Phase-blocker  
**Evidence:** `ARCHITECTURE-SPINE.md:113-114, 185-188, 249, 574-588`

The prose requires append-only revisions and says handoff generation validates review logs, but `REVIEW_LOG` has no `revision_no`, `supersedes_id`, `is_current`, or immutable review snapshot. The calibration uniqueness rule only applies to the tuple containing `calibration_sample_id`; application reviews have a nullable sample key and no explicit current selection. The handoff contract does not state that every required criterion has the required reviewer coverage before a card is generated.

**Required gate correction:** define review revision/current projection and a complete-review predicate for official handoff. State whether application review requires HR, TECH, or both for every criterion, and bind each handoff to the selected review revisions.

### H-04 — Required page fallback cannot be reconstructed from the ERD

**Severity:** High  
**Classification:** Phase-blocker  
**Evidence:** `ARCHITECTURE-SPINE.md:106, 312, 490-507, 547-559`; PRD `FR-007, FR-010, FR-012b`

`DOCUMENT_PAGE` stores only page number and page hash, while `MARKDOWN_BLOCK` has no page association or page-range mapping. A citation stores an optional page number and BBox but no coordinate space, page snapshot reference, or block-to-page relation. Thus the required “page or Markdown block” fallback and the click-to-page behavior cannot be implemented deterministically from the declared persisted data. BBox support may be deferred, but page/block fallback is an MVP requirement and is not the deferred part.

**Required gate correction:** persist the page/block mapping (including the page snapshot and coordinate-space/version metadata where BBox exists) or explicitly define the resolver’s deterministic derived index and its hash/version binding.

### H-05 — Offset unit is ambiguous across Python and browser implementations

**Severity:** High  
**Classification:** Phase-blocker  
**Evidence:** `ARCHITECTURE-SPINE.md:105-106, 503-506, 555-557`

The phrase “UTF-8 code point offset” conflates Unicode code points with UTF-8 byte offsets. Python string indices, UTF-8 byte indices, and JavaScript UTF-16 code-unit indices differ for Korean text, emoji, and combining characters. The exact-substring/hash gate can pass on the backend while the browser highlights a different range.

**Required gate correction:** select one offset unit (prefer normalized Unicode scalar/code-point indices for text, with an explicit conversion routine) and specify the canonical encoding, normalization version, and test vectors containing Korean, emoji, CRLF, tabs, and combining characters.

### H-06 — API paths, error status, and selection authority contradict each other

**Severity:** High  
**Classification:** Phase-blocker  
**Evidence:** `ARCHITECTURE-SPINE.md:97, 226-232, 255-258, 263, 267-276`; PRD `FR-021`

The question-generation path is `/api/handoff/{handoff_id}/questions/generate` in the candidate contract but `/api/{handoff_id}/questions/generate` in the core request description. Candidate selection is described as “the reviewer” and “roles with handoff access” in one place, but `AD-5` and the PRD’s LEAD flow make `LEAD` the selector. Preview handoff rejection is `403` in `AD-1` but `409 PREVIEW_ONLY` in the error matrix. Independent clients will implement different URLs, role checks, and retry/error handling.

**Required gate correction:** publish one endpoint/role/error matrix and remove the contradictory forms. Include exact request/response schemas and an authorization test for HR, TECH, and LEAD on every question operation.

### H-07 — Idempotency scope is stated but not persisted as a complete contract

**Severity:** High  
**Classification:** Phase-blocker  
**Evidence:** `ARCHITECTURE-SPINE.md:148, 274, 282, 287, 509-534`

The required idempotency key scope includes workspace, actor, endpoint, payload fingerprint, and criteria version, but `PROCESSING_RUN` stores only `idempotency_key`; the schema has no workspace, actor, endpoint, or payload-fingerprint columns and no generic idempotency resource for criteria, handoff, question, or decision operations. A unique key can therefore incorrectly replay a different request or fail to prevent duplicates, depending on implementation.

**Required gate correction:** define an idempotency record with the complete scope, request fingerprint, status, original response/resource IDs, and mismatch behavior. State which endpoints are idempotent and test same key/same payload, same key/different payload, different actor, and concurrent first requests.

### H-08 — Question safety fields are generated but not durably modeled

**Severity:** High  
**Classification:** Phase-blocker  
**Evidence:** `ARCHITECTURE-SPINE.md:127-131, 203-204, 623-644`

The structured question output contains `verification_target` and `reason`, but `INTERVIEW_QUESTION_CANDIDATE` has no `verification_target` or `reason` field. `concern_text` may be intended as the destination, but that mapping is not stated and cannot preserve the distinction between the concern, the verification target, and the generation reason. The server is required to validate non-leading, concrete, privacy-safe questions, yet the persisted record lacks the complete data needed to audit those checks.

**Required gate correction:** add explicit persisted fields or define a lossless mapping, including validation policy/version and reviewer-visible reason/target. Add negative tests for protected-trait questions, leading questions, unsupported factual assertions, and questions with no citation.

### H-09 — Handoff conflicts are shown as a projection but not snapshotted

**Severity:** High  
**Classification:** Phase-blocker  
**Evidence:** `ARCHITECTURE-SPINE.md:185-188, 418-421, 596-621`

The ERD claims `HANDOFF_CARD` preserves `CONFLICT_ITEM`, but `CONFLICT_ITEM` has no `handoff_card_id` and the card has no conflict snapshot or selected-conflict revision list. If a conflict is later resolved or recomputed, a historical handoff can display a different conflict state, violating the stated immutable artifact set and auditability. Deriving conflicts by the card’s tuple is not enough when the conflict record itself is mutable.

**Required gate correction:** add a handoff-to-conflict snapshot/join with conflict revision and display projection, or make conflict revisions immutable and bind the card to the exact revision set.

### H-10 — Final decision history has no current/voided semantics or decision idempotency

**Severity:** High  
**Classification:** Phase-blocker  
**Evidence:** `ARCHITECTURE-SPINE.md:157-158, 257-258, 284, 679-699`

`DECISION_RECORD` is append-only with increasing `revision_no`, but has no `is_current`, supersession, void/reversal, or GET projection rule. Repeating the decision request can create multiple active `ADVANCE`/`REJECT` records, and two clients can submit different revisions without a defined winner. The decision endpoint also has no explicit idempotency contract. “Latest by revision” is mentioned for verification, not for decisions.

**Required gate correction:** define decision revision concurrency, current projection, correction/void semantics, and idempotent replay. Test duplicate submit, concurrent contradictory submit, and post-decision question edit/verification attempts.

### H-11 — Architecture is still marked `draft` while the PRD declares finalization complete

**Severity:** High  
**Classification:** Phase-blocker  
**Evidence:** `ARCHITECTURE-SPINE.md:8`; PRD frontmatter and §13.2/§15

The architecture frontmatter says `status: draft`, while the PRD says the architecture was synchronized, has no phase-blocker, and PRD finalization is complete. This makes the release state non-deterministic for the next phase and directly contradicts the requested fresh finalization gate.

**Required gate correction:** after resolving the substantive blockers, update the architecture status and completion statement together; do not mark it final while any contract above remains unresolved.

## Deferred classification

The following are explicitly deferred in the current PRD and architecture and are not, by themselves, finalization blockers:

- **D-01:** exact number of interview-question candidates — acceptable only after the generation schema and selection authority are fixed.
- **D-02:** exact demo dataset count/composition — acceptable while the seed invariants remain fixed and tested.
- **D-03:** baseline reproduction execution — deferred for the product phase, but becomes a submission blocker before DEL-003 is claimed complete.
- **D-04:** final problem-card evidence — deferred until sources are verified; no unverified number may be presented as fact.
- **D-05:** repository/deployment links — deferred until submission; it is a submission blocker at that phase.
- **D-06:** two-minute metric measurement — deferred until demo validation.
- **D-07:** BBox support range — acceptable as deferred because snippet/page/context fallback remains mandatory. The missing page/block persistence in H-04 is not covered by D-07.

Additional hardening that is not a gate blocker for the stated single-workspace demo but should be tracked: CSRF/origin protection for cookie-authenticated mutations, production retention/cleanup, multi-tenant isolation, SSO, and scale-out queueing. The demo must still run over HTTPS if `Secure` cookies are mandatory.

## Passing controls observed

These controls are clearly specified and should be preserved during revision:

- Server-derived actor and role; request-body identity/role values are not trusted (`AD-12`).
- Deterministic server-side conflict calculation rather than AI reconciliation (`AD-3`).
- Exact-substring and hash validation before a mapping becomes complete (`AD-2`, `AD-7`).
- Preview downstream gating, no automatic accept/reject decision, and human LEAD decision entry (`AD-1`, `AD-8`).
- Soft deletion and question revision preservation (`AD-5`).
- PDF magic-byte/MIME validation, private file storage, provider allowlists, correlation IDs, and worker CAS ownership (`AD-7`, `AD-9`, `AD-12`).

## Final disposition

**Do not advance to implementation as a finalized architecture.** Resolve C-01 and C-02 first, then close H-01 through H-11 with executable contract tests and update the architecture status. A fresh gate can pass only when both independent implementations converge on the same identity, mode, transition, authorization, citation, question, interview, and decision behavior.
