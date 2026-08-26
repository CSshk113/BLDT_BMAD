# Architecture Spine Rubric Review

- **Artifact:** `ARCHITECTURE-SPINE.md`
- **Review scope:** architecture spine only. The PRD and addendum were consulted only to verify capability coverage and stated technology decisions.
- **Review method:** adversarial and edge-case passes, constrained to the good-spine checklist supplied for this review.
- **Verdict:** **REVISE — does not yet pass the good-spine gate.**

## Rubric result

| Checklist area | Result | Assessment |
|---|---|---|
| Invariants cover divergence points | Partial | The major product divergences are named, but approval, processing-state, reviewer-identity, question-safety, and interview-result boundaries are not fully closed. |
| Every AD has enforceable Binds/Prevents/Rule | Partial | AD-1 through AD-7 all contain the three headings, but several Rules cannot be enforced by the stated data model or API contract. |
| Deferred items are explicit | Pass with follow-up | The four spine deferrals are explicit; some PRD deferrals and their implementation gates are not carried into the spine. |
| Named technology is verified or honestly marked | Partial | LlamaParse is marked account-configured and the PRD calls for model availability verification, but the spine gives no verification evidence or explicit provisional status for the fixed model/version choices. |
| PRD capabilities are covered | Partial | FR-001–FR-022 are listed and grouped, but FR-014, FR-017, FR-018, and FR-022 lack complete architectural contracts; several quality requirements are only implied. |
| Operational/environmental envelope is decided or deferred | Fail | Local storage and server-side configuration are named, but deployment, access, resource, persistence, recovery, observability, and runtime limits are neither decided nor explicitly deferred. |

## Findings

### Invariants and divergence points

1. **Approved criteria are not actually immutable.**

   - **Location:** `ARCHITECTURE-SPINE.md:92-98`
   - **Trigger:** `criteria_version_id` is immutable as an identifier, but no rule forbids editing or deleting an approved `CriteriaVersion` or its `CriteriaItem` rows.
   - **Guard:** Define an explicit state-transition and immutability rule: approved versions and their items are append-only; update/delete returns a domain error; corrections create a new version.
   - **Consequence:** The same version ID can produce different evaluations over time, breaking auditability and FR-005/FR-018 reproducibility.

2. **Approval is not tied to resolution of all conflicts.**

   - **Location:** `ARCHITECTURE-SPINE.md:92-98, 106-112`
   - **Trigger:** The gate checks `status == APPROVED`, but no rule requires zero unresolved `ConflictItem`s before approval.
   - **Guard:** Make approval a server transaction that verifies `unresolved_conflict_count == 0`, records the approver, and rejects otherwise.
   - **Consequence:** An API caller can approve a version while the calibration gate still contains unresolved divergence.

3. **The official-final-decision gate is narrower than the PRD guardrail.**

   - **Location:** `ARCHITECTURE-SPINE.md:94-98, 313-328`
   - **Trigger:** Only official `HandoffCard` creation is explicitly rejected; no final-decision resource or endpoint is defined, and `ReviewLog` writes are not gated.
   - **Guard:** Define the final decision resource and apply the approved-version precondition to every official review, handoff, and final-decision write.
   - **Consequence:** An unapproved version can still acquire a record that the product describes as an official decision.

4. **Conflict preservation has no concrete persistence contract.**

   - **Location:** `ARCHITECTURE-SPINE.md:110-112, 322-328`
   - **Trigger:** The Rule promises `ConflictItem`, while the ERD provides only opaque `HANDOFF_CARD.hr_tech_conflicts` JSON.
   - **Guard:** Model `CONFLICT_ITEM` with stable ID, sample/criteria references, both reviewer values, both evidence references, reason, resolution state, and timestamps; or specify a versioned JSON schema and constraints.
   - **Consequence:** Conflicts cannot be reliably queried, counted for approval, independently rendered, or audited.

5. **Reviewer independence is not enforceable from the schema.**

   - **Location:** `ARCHITECTURE-SPINE.md:106-112, 313-320`
   - **Trigger:** `REVIEW_LOG` stores `reviewer_role` but no reviewer identity, calibration-sample ID, unique reviewer/sample/criteria key, or append-only history.
   - **Guard:** Add reviewer/user ID, sample ID, created/updated timestamps, and uniqueness/ownership constraints that prevent one reviewer’s entry from overwriting the other’s.
   - **Consequence:** The system cannot prove two independent judgments or preserve their separate evidence and changes.

6. **The named “bidirectional” split-view contract defines only one direction.**

   - **Location:** `ARCHITECTURE-SPINE.md:113-118`
   - **Trigger:** The Rule specifies citation-panel click to PDF focus, but no PDF selection/scroll event updates the criteria panel or `active_citation_id`.
   - **Guard:** Specify both event directions, source-of-truth ownership, stale-event handling, and behavior when multiple citations share a snippet.
   - **Consequence:** The implementation can satisfy the written rule while delivering only one-way synchronization.

7. **The zero-match and ambiguous-match evidence paths are not explicit.**

   - **Location:** `ARCHITECTURE-SPINE.md:99-105, 303-311`
   - **Trigger:** Exact-match validation is stated, but the model does not define `UNVERIFIABLE`, ambiguous match, or `근거 없음` persistence; `context_box` and source-kind fallback fields are absent.
   - **Guard:** Define mapping outcomes such as `VERIFIED`, `UNVERIFIABLE`, and `FAILED_MAPPING`, with allowed nullability and a required fallback payload for non-coordinate evidence.
   - **Consequence:** A missing or non-unique match can be rejected without a user-visible explanation, or be stored as apparently valid evidence.

8. **In-progress applications are not barred from official handoff generation.**

   - **Location:** `ARCHITECTURE-SPINE.md:128-144, 217-245`
   - **Trigger:** Failed documents are excluded from completed mappings, but no rule requires `application.processing_status == COMPLETED` before handoff or final-decision creation.
   - **Guard:** Add `COMPLETED` as a mandatory precondition for official handoff and final decision; return a typed processing-state error for `RECEIVED`, `PARSING`, or `MAPPING`.
   - **Consequence:** A handoff can be generated with missing or partial evidence while still passing the approved-criteria gate.

9. **Pipeline retry isolation lacks idempotency and transaction rules.**

   - **Location:** `ARCHITECTURE-SPINE.md:128-144, 289-301`
   - **Trigger:** Retry and partial-result behavior are described, but no idempotency key, uniqueness constraint, transaction boundary, or stale-run ownership rule is defined.
   - **Guard:** Make `(application_id, stage, attempt_no)` and provider request identity explicit, serialize status transitions, and commit mappings atomically only for the active run.
   - **Consequence:** Concurrent retries can duplicate mappings, race status updates, or promote a stale run’s result.

10. **Timeout and retry limits are named but not decided.**

    - **Location:** `ARCHITECTURE-SPINE.md:142-144, 188`
    - **Trigger:** “Limited timeout and retry count” has no numeric defaults, per-provider policy, backoff, or user-facing terminal condition.
    - **Guard:** Define timeout, maximum attempts, backoff, and terminal error behavior in the runtime configuration contract, with safe defaults.
    - **Consequence:** The failure envelope is not testable and an external call can still stall or retry unpredictably.

### PRD capability coverage

11. **FR-017 interview verification has no domain model or comparison contract.**

    - **Location:** `ARCHITECTURE-SPINE.md:322-328`; PRD `prd.md:115-117`
    - **Trigger:** `HANDOFF_CARD.interview_feedback` is a free-text field; there is no interview result, initial hypothesis snapshot, verification outcome, or comparison record.
    - **Guard:** Define an interview-result resource linked to the handoff and its questions, with outcome, evidence/notes, actor, timestamp, and an explicit hypothesis-versus-result comparison.
    - **Consequence:** The required post-interview learning loop cannot be stored or reproduced as structured history.

12. **FR-018 decision-log replay is underspecified.**

    - **Location:** `ARCHITECTURE-SPINE.md:137-144, 313-328`; PRD `prd.md:119`
    - **Trigger:** There is no `DecisionLog` entity or explicit actor/action/time/versioned evidence snapshot; `REVIEW_LOG` lacks timestamps and reviewer identity.
    - **Guard:** Define immutable decision events with actor, action, criteria-version ID, evidence citation IDs, prior/new state, reason, and event time.
    - **Consequence:** The system can show current records but cannot reliably reconstruct who decided what and when.

13. **FR-014’s single-screen handoff payload is not defined.**

    - **Location:** `ARCHITECTURE-SPINE.md:381-387, 322-328`; PRD `prd.md:111`
    - **Trigger:** The map names a handoff service, but the card schema does not explicitly contain first-pass judgments, insufficient-evidence items, source citations, or a structured aggregate/read contract.
    - **Guard:** Define a handoff read model/API that composes criteria, evidence, reviewer judgments, conflicts, unresolved questions, interview candidates, and processing provenance with stable ordering.
    - **Consequence:** The implementation can satisfy separate endpoints yet fail the required one-screen handoff experience.

14. **Question-generation quality rules are not enforceable.**

    - **Location:** `ARCHITECTURE-SPINE.md:120-126, 160-172`; PRD `prd.md:121-139`
    - **Trigger:** AD-5 enforces provenance and selection, but not multiple candidates, verifiability, specificity, non-leading/fair wording, or duplicate minimization.
    - **Guard:** Define a structured generator output and server validator for grounding, question type, prohibited adjudication claims, duplicate similarity, and required reason/evidence links.
    - **Consequence:** A question may be traceable yet still be generic, repetitive, leading, or unrelated to an unresolved concern.

15. **The no-automatic-decision guardrail has no enforcement point.**

    - **Location:** `ARCHITECTURE-SPINE.md:120-126`; PRD `prd.md:127`
    - **Trigger:** The spine stores and selects generated questions but has no schema or validator preventing a question from asserting a hiring outcome or a new fact.
    - **Guard:** Restrict generator output to verification-question fields, reject outcome-bearing text or unsupported factual claims, and keep hiring status writes human-only.
    - **Consequence:** The UI can drift into automatic recommendation or unsupported factual assertions despite the product guardrail.

16. **FR-016 role access is deferred without an MVP authorization contract.**

    - **Location:** `ARCHITECTURE-SPINE.md:352-375, 391-397`; PRD `prd.md:49-55, 115`
    - **Trigger:** A role toggle is mentioned in the deferred section, but no actor identity, authorization matrix, or endpoint-level permissions are defined.
    - **Guard:** Decide the demo role model explicitly: permitted operations for HR, Tech Reviewer, and Hiring Lead, plus server-side enforcement even in the single-workspace mode.
    - **Consequence:** Any client can approve criteria, alter reviewer records, or select/delete questions, and the leader-view requirement is not demonstrably implemented.

### Deferred items and technology verification

17. **The spine’s deferral list omits PRD deferrals that affect architecture entry gates.**

    - **Location:** `ARCHITECTURE-SPINE.md:391-397`; PRD `prd.md:278-286`
    - **Trigger:** The spine carries only four deferred topics, omitting D-04 problem-card evidence, D-05 repository/deployment links, D-06 timing metric, and D-07 supported coordinate-highlight scope.
    - **Guard:** Add the omitted items when they affect implementation or submission readiness, each with owner/decision point and explicit “does not block” or “blocks” status.
    - **Consequence:** Downstream teams may treat unresolved submission, measurement, or PDF-support decisions as settled architecture.

18. **The fixed model and versions have no verification evidence in the spine.**

    - **Location:** `ARCHITECTURE-SPINE.md:176-189`
    - **Trigger:** Next.js, React, PDF.js, FastAPI, Pydantic, SQLite, and `gpt-5.6-luna` are presented as concrete choices, but no lockfile, compatibility check, account-availability result, or verification date is recorded.
    - **Guard:** Mark each unverified choice as provisional and record the verification gate; for the model, require an explicit account availability check and exact snapshot before implementation.
    - **Consequence:** The build can silently depend on unavailable or incompatible versions, contradicting the PRD’s no-silent-substitution rule.

### Operational and environmental envelope

19. **The deployment and process envelope is undecided.**

    - **Location:** `ARCHITECTURE-SPINE.md:44-86, 176-190, 352-377`
    - **Trigger:** “Local Store” and server-side environment variables are named, but host/runtime, startup, frontend-backend origin, CORS, TLS, single-process assumption, and public demo access are absent.
    - **Guard:** Decide or defer the target environment, process topology, service URLs, CORS/TLS policy, startup checks, and submission/demo access path.
    - **Consequence:** The architecture cannot be reproduced or safely exposed as the required clickable demo.

20. **File admission and resource limits are not specified.**

    - **Location:** `ARCHITECTURE-SPINE.md:128-144, 176-190, 217-232`
    - **Trigger:** PDF is the only input type, but maximum file size/count, total batch bytes, encrypted/corrupt PDF handling, storage quota, and memory/time budget are absent.
    - **Guard:** Define upload validation, size/count limits, batch identity, rejection codes, and resource/time budgets; explicitly defer the presentation dataset quantity if needed.
    - **Consequence:** A malformed or oversized input can exhaust local resources or remain stuck without a deterministic user-visible outcome.

21. **Persistence, retention, and recovery are not closed for local storage.**

    - **Location:** `ARCHITECTURE-SPINE.md:69-85, 176-190, 391-397`
    - **Trigger:** SQLite and PDF file storage are selected, but file layout, retention/deletion, backup/export, recovery after restart, and database migration/versioning are not decided or deferred.
    - **Guard:** Specify the demo persistence contract: durable paths, migration command/version, restart recovery, backup/export expectations, retention, and cleanup of uploaded PDFs.
    - **Consequence:** A restart or schema change can orphan evidence, lose audit records, or leave the demo unrecoverable.

22. **Operational observability and secret-safe diagnostics are incomplete.**

    - **Location:** `ARCHITECTURE-SPINE.md:128-144, 176-189`
    - **Trigger:** ProcessingRun records step metadata, but no health/readiness signals, structured application logs, metrics, alert/diagnostic policy, or redaction rule for PDF content and prompts is defined.
    - **Guard:** Define health endpoints, correlation-aware structured logs, failure metrics, and explicit redaction boundaries for secrets, applicant data, prompts, and provider responses.
    - **Consequence:** Demo failures are hard to diagnose and logs may expose sensitive applicant or provider data.

## Positive evidence retained

- AD-1 through AD-7 each expose `Binds`, `Prevents`, and `Rule` sections.
- The core product divergence points are correctly recognized: approval gating, exact evidence grounding, conflict preservation, split-view fallback, question selection, and processing failure isolation.
- All PRD functional requirement IDs, including FR-012a/FR-012b and FR-019–FR-022, are listed in the spine front matter and capability map.
- The spine explicitly defers presentation-scale queueing, multi-tenant/SSO, ATS integration, and PB-02 baseline execution instead of pretending they are implemented.

## Required gate before approval

Close the approval/immutability contract, reviewer/conflict persistence model, interview-result and decision-log model, question-safety enforcement, completed-processing precondition, retry/idempotency rules, technology verification gates, and the operational envelope. Until those are either decided or explicitly deferred with entry criteria, this spine should remain **REVISE**.
