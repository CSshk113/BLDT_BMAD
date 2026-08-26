# Final BMad Architecture Rubric Gate

- **Artifact:** `ARCHITECTURE-SPINE.md`
- **Review date:** 2026-08-27
- **Review mode:** Validate-only; the spine was not edited.
- **Inputs checked:** the target spine, PRD `prd.md`, PRD `addendum.md`, existing reconciliation/review artifacts, and current official technology sources.
- **Verdict:** **REVISE — gate fails; not ready for implementation handoff.**

## Gate summary

| Rubric area | Result | Reason |
|---|---|---|
| Invariants and divergence points | Partial | AD-1 through AD-9 name the major trust boundaries, but calibration identity, lifecycle transitions, source snapshots, and bidirectional UI behavior remain open. |
| Rule enforceability | Fail | Several rules are asserted in prose but lack the schema constraints, endpoint guards, authorization model, or immutable audit semantics needed to enforce them. |
| PRD FR-001..FR-022 coverage | Partial | All requirement IDs are listed and grouped, but FR-002, FR-004/011, FR-014, FR-016, FR-018, and FR-022 are not fully contract-closed. |
| Deferred/open dimensions | Partial | The spine has a Deferred section, but it omits or renames PRD D-04..D-07 and does not close resource, recovery, observability, and security-operational dimensions. |
| Data/API contracts | Fail | The ERD is stronger than the prior draft, but calibration, conflict resolution, handoff composition, role access, request/response schemas, and lifecycle error behavior are incomplete or inconsistent. |
| Technology reality | Pass with lock follow-up | The named versions/models exist in current official/package sources, but exact model snapshot, runtime versions, parser configuration, worker pairing, and one internally contradictory version remain unresolved. |
| Operational envelope | Fail | Local SQLite/file storage is named, but admission limits, runtime topology, restart recovery, migrations, backup/retention, health, logging/redaction, and exposure policy are not decided or explicitly deferred. |

## Deterministic and positive checks

- AD-1 through AD-9 are monotonic and not duplicated.
- Every AD block contains `Binds`, `Prevents`, and `Rule`.
- The front matter lists FR-001 through FR-022, including FR-012a, FR-012b, and FR-019 through FR-022.
- The ERD now contains `CONFLICT_ITEM`, `INTERVIEW_VERIFICATION`, `DECISION_RECORD`, and question provenance relations; these are useful foundations.
- The current technology references are real/current: [Next.js 16.3](https://nextjs.org/blog), [FastAPI 0.141.1](https://fastapi.tiangolo.com/pt/release-notes/), [Pydantic 2.13.4](https://github.com/pydantic/pydantic/releases), [react-pdf 10.5.0](https://www.npmjs.com/package/react-pdf), [llama-parse 0.6.94](https://pypi.org/project/llama-parse/0.6.94/), and [gpt-5.6-luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna).
- No brownfield source implementation exists in the repository to ratify; the review therefore treats the spine as a greenfield build contract.
- The prescribed `uv run .../lint_spine.py` pass could not execute because `uv` is unavailable in the environment. An equivalent local check found no duplicate/non-monotonic AD IDs or missing AD fields. The linter would likely flag the deliberate `{application_id}`, `{handoff_id}`, `{question_id}`, and `{id}` route parameters as possible low-severity template tokens; these are not gate blockers.

## Critical findings

### None

No single defect makes the design irrecoverable, but the high findings below collectively block the gate because they affect official-output trust, cross-unit interoperability, and reproducibility.

## High findings

### H-01 — Approved criteria immutability and conflict scope are not enforceable

- **Location:** `ARCHITECTURE-SPINE.md:92-98, 301-350, 422-434`
- **Trigger:** AD-1 says approved criteria are not modified and unresolved conflicts block approval, but the schema has no immutable-version/item constraint, approval actor/time, or calibration-sample/phase scope for conflicts.
- **Guard:** Define server-side criteria state transitions; reject update/delete of an approved version or its items; create a new version for corrections; add `approver_id`, `approved_at`, and a calibration-sample/phase identity; make approval atomically verify zero unresolved calibration conflicts.
- **Consequence:** The same criteria version can change over time, or an applicant-review conflict can incorrectly approve/block a criteria version, breaking FR-001/004/005/018 reproducibility.

### H-02 — Calibration sample and independent reviewer contract is incomplete

- **Location:** `ARCHITECTURE-SPINE.md:108-113, 241-263, 404-420`
- **Trigger:** FR-002 requires two independent reviewers on calibration samples, but `REVIEW_LOG` has no calibration sample entity/reference, no reviewer account/role authority, and no uniqueness/append-only constraint for reviewer × sample × criterion.
- **Guard:** Add `CALIBRATION_SAMPLE` (or an explicit sample type and identity), bind each calibration review to it, define reviewer ownership and uniqueness constraints, and expose calibration create/review/compare/resolve/approve contracts.
- **Consequence:** Two implementations can store incompatible review populations and still claim to have calibrated the same criteria version.

### H-03 — Official/preview and completed-processing gates are only partially closed

- **Location:** `ARCHITECTURE-SPINE.md:92-98, 131-147, 193-207, 436-491`
- **Trigger:** `preview_mode` is required by prose but absent from the data model; only handoff creation is explicitly blocked; there is no explicit `COMPLETED` precondition for handoff/decision generation and no official/preview mode in the artifact contracts.
- **Guard:** Define persisted artifact mode/status and enforce, at every official write, `criteria_version.status=APPROVED`, `application.processing_status=COMPLETED`, current successful run, and zero disallowed open conflicts; return typed 403/409/422 errors for each failed precondition.
- **Consequence:** A caller can create an official-looking handoff or decision from preview, in-progress, or stale evidence while satisfying the written ADs.

### H-04 — Citation provenance and fallback data are not canonical enough to enforce FR-006..FR-010

- **Location:** `ARCHITECTURE-SPINE.md:100-106, 115-120, 382-402`
- **Trigger:** Exact substring, Markdown block, page, location, BBox, and `context_box` are mentioned, but there is no Markdown-block/source-revision entity, canonical normalization/comparison rule, BBox units/origin/rotation/page dimensions, or persisted fallback payload.
- **Guard:** Specify a versioned citation schema with exact source text, normalized comparison text, source document/run revision, unique block identity, location confidence, coordinate system, and required fallback fields for zero/ambiguous matches.
- **Consequence:** A structurally valid citation can point to the wrong repeated text or render no usable context when page/BBox resolution fails.

### H-05 — Processing retries and current-mapping promotion lack concurrency constraints

- **Location:** `ARCHITECTURE-SPINE.md:140-147, 363-402`
- **Trigger:** The prose names idempotency and latest-success promotion, but the ERD has no uniqueness/partial-current constraint, no transition graph, no stale-run ownership rule, and no `processing_run_id` on `HANDOFF_CARD`.
- **Guard:** Define unique keys for logical runs and provider calls, legal state transitions, serialized status updates, atomic promotion of one current mapping per application/version/criterion, and source-run/revision binding on every official artifact.
- **Consequence:** Concurrent retries can duplicate mappings, race status, or make a handoff read a mapping from a different run than the one it claims.

### H-06 — “No evidence” and unverified mapping outcomes cannot be represented

- **Location:** `ARCHITECTURE-SPINE.md:100-106, 131-147, 394-402`; PRD `prd.md:143-146, 160-165`
- **Trigger:** The PRD requires every criterion to have a mapping or explicit “근거 없음”/unverifiable outcome, but `EVIDENCE_MAPPING` has no outcome/status/reason fields and citations imply successful evidence.
- **Guard:** Add a mapping outcome such as `VERIFIED`, `UNVERIFIABLE`, or `NO_EVIDENCE`, with required reason and optional citation rules; prevent unsupported rows from being rendered as verified evidence.
- **Consequence:** Missing evidence is either silently dropped or represented as a false-positive mapping, violating traceability and failure visibility.

### H-07 — The claimed bidirectional split-view invariant specifies one direction only

- **Location:** `ARCHITECTURE-SPINE.md:115-120, 241-299`
- **Trigger:** The contract defines citation-panel click → PDF focus, but no PDF selection/scroll → criteria-panel update, stale-event handling, or multi-citation disambiguation.
- **Guard:** Define both event directions, event IDs/versioning, active-citation ownership, behavior for repeated/overlapping citations, and fallback when a PDF selection has no canonical citation.
- **Consequence:** Two teams can each comply while delivering different synchronization semantics, and the “bidirectional” invariant is not testable.

### H-08 — Handoff composition and generation endpoints are inconsistent

- **Location:** `ARCHITECTURE-SPINE.md:179-207, 281-292, 436-462`
- **Trigger:** The sequence uses `POST /api/handoff/generate`, the core API table omits it, and the `HANDOFF_CARD` schema does not define a composed first-pass judgment/insufficient-evidence/read snapshot despite FR-014.
- **Guard:** Choose the canonical create/generate endpoint and define request/response schemas, stable ordering, snapshot/version semantics, and a composed read model containing original document, criteria, current evidence, both reviewer views, conflicts, unresolved concerns, candidates, and provenance.
- **Consequence:** Frontend and backend units can implement different handoff shapes and still appear compliant with the current document.

### H-09 — Interview verification and decision history are not actually append-only/replayable

- **Location:** `ARCHITECTURE-SPINE.md:149-155, 470-497`
- **Trigger:** The ERD contains verification and decision rows, but append-only behavior, update/delete rejection, actor identity/role, prior/new state, and source snapshot binding are not enforced by schema or API rules.
- **Guard:** Define immutable event semantics and server guards for verification/decision writes; include actor, action, timestamp, handoff/source revision, criteria version, evidence citation IDs, prior/new values, and correction/reversal behavior.
- **Consequence:** FR-017/FR-018 can show current values but cannot reliably reconstruct how the final decision was reached.

### H-10 — Role authorization and leader access are not implementable from the spine

- **Location:** `ARCHITECTURE-SPINE.md:157-163, 404-414, 246-248, 293-298`
- **Trigger:** The rule says reviewers can edit only their own records and leaders can perform post-interview actions, but there is no user/role model, authentication boundary, authorization matrix, or endpoint-level leader read/write contract; the Deferred section says role toggles substitute for real access without defining server enforcement.
- **Guard:** Define the MVP identity/role mechanism and a matrix for HR, Tech Reviewer, and Hiring Lead across criteria, calibration, reviews, conflicts, handoff, questions, verification, and decisions; enforce it in FastAPI, not only in the UI.
- **Consequence:** A client can approve criteria, mutate another reviewer’s record, alter selected questions, or bypass the leader workflow, and FR-016 is not demonstrable.

### H-11 — Interview-question safety and quality requirements are not enforceable

- **Location:** `ARCHITECTURE-SPINE.md:122-129, 445-468`; PRD `prd.md:121-139`
- **Trigger:** The spine preserves provenance and selection but does not enforce multiple candidates, verifiability, specificity, non-leading/fair wording, duplicate minimization, or the ban on automated hiring conclusions/new factual claims.
- **Guard:** Define structured generator output plus a server validator for required grounding, question type, verification target, reason/citations, prohibited outcome/factual assertions, protected-trait/privacy checks, and duplicate similarity; reject invalid candidates before persistence.
- **Consequence:** Traceable candidates can still be generic, repetitive, leading, discriminatory, or implicitly auto-adjudicating, violating FR-019/020/022.

### H-12 — Question-generation timing, lifecycle, and regeneration semantics conflict

- **Location:** `ARCHITECTURE-SPINE.md:179-191, 185-189, 281-292, 445-462`
- **Trigger:** The section says candidates are created with the handoff, while the API and sequence use a separate generation operation; state transitions do not define selected/deleted edit rules, regeneration behavior, or a database uniqueness guarantee for `generation_key`.
- **Guard:** Select one lifecycle; define legal transitions and authorization, whether selected rows can be deleted/re-generated, and a unique generation key scoped to handoff/source revision/prompt version with deterministic read semantics.
- **Consequence:** Parallel builders can create duplicate or resurrected questions, and a deleted/old candidate can remain actionable.

### H-13 — Calibration, conflict resolution, and criteria APIs are missing from the API contract set

- **Location:** `ARCHITECTURE-SPINE.md:193-207, 241-263, 422-434`
- **Trigger:** The sequence names calibration and approval endpoints, and `CONFLICT_ITEM` has a `RESOLVED` state, but the Core API table has no criteria create/version, calibration sample/review, conflict resolution, or approval request/response contract.
- **Guard:** Add endpoint schemas, authorization, idempotency, state preconditions, conflict-resolution payloads, and stable error/status behavior for the complete FR-001..FR-005 flow.
- **Consequence:** F1 cannot be split across implementation units without inventing incompatible endpoints and conflict semantics.

### H-14 — The spine contains an internal frontend-version contradiction

- **Location:** `ARCHITECTURE-SPINE.md:226-230, 500-523`
- **Trigger:** The Stack fixes Next.js at `16.3.x`, while the source-tree comment says `Next.js 15 Frontend`; the Stack also uses loose `x`/“lockfile-pinned” wording without declaring Node/Python/worker compatibility baselines.
- **Guard:** Remove the contradictory version, pin the tested frontend/backend/runtime/worker set, and state supported Node.js and Python versions plus clean-install/build verification.
- **Consequence:** Two teams can select different framework APIs or runtime assumptions, causing build and integration drift.

### H-15 — Model/parser reproducibility and provider-failure contracts remain open

- **Location:** `ARCHITECTURE-SPINE.md:131-138, 140-147, 222-235`
- **Trigger:** The model alias and parser package version are named, but the exact model snapshot, Responses/Chat Completions mode, strict output schema, refusal/truncation/schema-failure behavior, parser tier/version/output options, and silent-fallback policy are not part of the contract.
- **Guard:** Pin or record exact model/parser snapshots and request configuration in `ProcessingRun`; define provider response validation, refusal/truncation handling, timeout classes, and an explicit no-silent-substitution rule.
- **Consequence:** Identical inputs can produce non-reproducible outputs or be silently processed by a different model/parser contract.

### H-16 — File admission and resource limits are missing

- **Location:** `ARCHITECTURE-SPINE.md:131-138, 197-200, 222-235, 539-547`; PRD `prd.md:101-105, 143-146`
- **Trigger:** PDF is the only accepted type, but maximum file size/page count, batch identity/count, encrypted/corrupt PDF behavior, storage quota, memory/time budgets, and oversized-input error codes are absent.
- **Guard:** Define deterministic admission validation, per-file and batch limits, malformed/encrypted handling, quota policy, bounded parser/LLM work, and user-visible terminal states; separately mark the 200-application scale target as future scope.
- **Consequence:** A malformed or oversized input can exhaust local resources or remain stuck without a predictable result.

### H-17 — Local persistence, migration, restart recovery, and retention are not closed

- **Location:** `ARCHITECTURE-SPINE.md:222-235, 351-380, 539-547`
- **Trigger:** SQLite and file storage are selected, but database/file layout, migration/bootstrap versioning, WAL/sidecar handling, restart recovery for non-terminal runs, backup/export, retention, deletion, and orphan cleanup are absent.
- **Guard:** Define the demo persistence root, migration command/version, restart reconciliation, backup/restore expectation, retention/deletion policy, and atomic file/database cleanup rules.
- **Consequence:** A restart or schema change can orphan PDFs/evidence, lose audit history, or leave the demo unrecoverable.

### H-18 — Network exposure, diagnostics, and secret-safe operations are incomplete

- **Location:** `ARCHITECTURE-SPINE.md:44-86, 157-163, 222-235, 539-547`
- **Trigger:** CORS allowlisting and server-side secrets are asserted, but deployment topology, frontend API-base strategy, TLS/exposure policy, authentication transport, health/readiness, structured logs/metrics, redaction, and repository secret-ignore/scan controls are not defined.
- **Guard:** Decide same-origin proxy versus direct browser-to-API, allowed origins/credentials, TLS and demo exposure, startup secret validation, health endpoints, correlation-aware logs/metrics, and redaction for PDFs, prompts, responses, and keys; specify `.env`/artifact ignore and secret scanning.
- **Consequence:** The clickable demo may not be reproducible or safely exposable, and operational logs can leak applicant or provider data.

### H-19 — PRD deferred/open decisions D-04..D-07 are not carried forward explicitly

- **Location:** `ARCHITECTURE-SPINE.md:539-547`; PRD `prd.md:278-286`
- **Trigger:** The spine defers question count, demo data, queueing, baseline, deployment values, and worker version, but omits explicit D-04 problem-card evidence, D-05 repository/deployment links, D-06 timing metric, and D-07 supported coordinate-highlight scope.
- **Guard:** Carry D-01 through D-07 by ID with owner, decision point, revisit condition, and whether each blocks implementation, demo validation, or submission only.
- **Consequence:** Downstream teams can mistake unresolved measurement, submission, and PDF-support choices for settled architecture.

## Medium/low follow-ups

### M-01 — The declared RFC 7807-compatible error shape is not RFC 7807-compatible

- **Location:** `ARCHITECTURE-SPINE.md:167-175`
- **Trigger:** The error example has `code` and `message` but omits the standard problem-detail fields (`type`, `title`, `status`, and `detail`).
- **Guard:** Adopt RFC 9457 problem details with project extensions, or explicitly rename/document the project-specific envelope and map 403/409/422/provider errors consistently.

### M-02 — Status enums omit several lifecycle states needed by the API

- **Location:** `ARCHITECTURE-SPINE.md:171-175, 336-380, 436-491`
- **Trigger:** Criteria, handoff, decision, and verification lifecycles have no explicit pending/revoked/superseded/cancelled states even though retries, approval, soft deletion, and append-only history require them.
- **Guard:** Define legal transition graphs and terminal/non-terminal states for each aggregate.

### M-03 — Capability mapping is grouped too coarsely for acceptance traceability

- **Location:** `ARCHITECTURE-SPINE.md:529-535`
- **Trigger:** F1/F2/F3 ranges show that IDs are present, but do not map each FR to a concrete schema, endpoint, guard, and verification evidence.
- **Guard:** Add a compact per-FR traceability matrix or link to one without duplicating the architecture narrative.

### M-04 — The location resolver is a named application service but not a versioned contract

- **Location:** `ARCHITECTURE-SPINE.md:228-234, 382-402`
- **Trigger:** The resolver is marked “MVP” and fallback is promised, but its input/output schema, confidence/error result, and versioning are not fixed.
- **Guard:** Define resolver contract/version and persist it in `ProcessingRun`/citation metadata.

### M-05 — Intentional endpoint path parameters trigger the mechanical placeholder heuristic

- **Location:** `ARCHITECTURE-SPINE.md:183-205`
- **Trigger:** The linter’s generic `{token}` check treats REST path parameters as possible unfilled template tokens.
- **Guard:** Either exempt documented route parameters in the lint rule or annotate the API section so the warning is unambiguously intentional.

## Gate disposition

The spine should remain **REVISE**. The minimum blocking set is H-01 through H-06, H-08 through H-13, H-16 through H-19, plus the version contradiction in H-14. After those contracts are tightened, rerun the deterministic lint and the independent rubric/data-integrity/technology passes before marking the spine final.
