# Adversarial Data-Integrity Review

**Subject:** `ARCHITECTURE-SPINE.md`  
**Review mode:** Two independent implementation units, both constrained only by the adopted ADs and stated conventions.  
**Scope:** Shared data shapes, state transitions, ownership, API semantics, evidence/question provenance, secrets, raw Markdown, retries, and soft deletion.  
**Source reviewed:** `ARCHITECTURE-SPINE.md`, especially AD-1 through AD-7, the consistency conventions, the question contract, and the ERD.

## Verdict

**Not ready for parallel implementation without a contract-tightening pass.** The spine establishes the right trust boundaries—approved criteria, exact-source evidence, deterministic reviewer differences, bounded processing, and human question selection—but it does not define enough canonical identity or lifecycle semantics for two teams to produce interoperable data. The highest risks are stale or cross-run evidence being presented as current, question provenance collapsing into free text, retry duplication/partial promotion, and soft-deleted questions remaining actionable.

The findings below do not claim that either implementation violates an explicit AD. They demonstrate that two reasonable implementations can obey the literal AD text and still disagree at an integration seam.

## Two independently compliant implementation units

### Unit A — strict relational and snapshot-oriented

- Stores immutable PDF, raw Markdown, and normalized-Markdown artifacts as versioned records. `Application` points to the active artifact set; a `ProcessingRun` owns a candidate artifact set until atomic promotion.
- Uses an `EvidenceMapping` parent per `(application, criteria_version, processing_run, criteria_item)` and `EvidenceCitation` children with canonical text offsets, hashes, and location metadata.
- Stores reviewer citations in a join table, normalizes `ConflictItem` as a first-class table, and makes the handoff reference conflict IDs rather than copying conflict JSON.
- Enforces approval, role, application, and run checks server-side. A failed retry cannot expose the previous or partial run as the current completed result.
- Generates questions in an idempotent command, requires structured provenance, snapshots selected question IDs into the final handoff projection, and treats deletion as terminal.
- Returns the standard success envelope for success and an envelope containing RFC-7807 fields for errors.

### Unit B — current-row and permissive document-oriented

- Keeps the PDF and raw Markdown, but stores only the latest normalized Markdown path on `Application`; a retry replaces that normalized artifact and updates the current pointer.
- Stores one mapping row per citation, validates the citation against the current normalized text, and uses `markdown_block_id` plus a page/bounding-box payload as its anchor.
- Stores `cited_snippet_ids` as JSON on each independent `ReviewLog`, calculates conflict differences as ordered-array differences, and embeds the resulting conflict payload in `HandoffCard.hr_tech_conflicts`.
- Implements a bounded retry and records provider calls, but permits mapping rows to be inserted before the final `COMPLETED` transition. Queries hide them while the application is not completed.
- Allows a candidate to satisfy AD-5 through `concern_text` alone, generates candidates through the separate endpoint, calculates the final question list dynamically from non-deleted selected rows, and permits `SELECTED -> DELETED`.
- Returns `application/problem+json` errors with the RFC-7807 fields directly, while using the success envelope for successful calls.

Both units can claim compliance with the written ADs. Their outputs are nevertheless not safely interchangeable without the contracts below.

## Findings and dispositions

Each finding states the seam, the divergence, and the required disposition. “Tighten invariant” means it is a shared correctness contract, not an implementation preference. “Deferred” is acceptable only where the spine already identifies a bounded MVP omission. “Ignore” is safe only after the named external contract is fixed.

### F-01 — Artifact identity is not immutable across retries

- **Location:** AD-2 lines 99–105; AD-7 lines 137–144; `APPLICATION` lines 277–287.
- **Trigger condition:** Unit A binds mappings to an immutable artifact set; Unit B replaces the normalized-Markdown path during retry.
- **Guard:** Add immutable `artifact_set_id`, raw/normalized content hashes, and artifact version foreign keys to every mapping, citation, and processing run; never update an artifact referenced by a completed result.
- **Consequence:** A citation can still contain an exact substring while resolving against different Markdown than the one used to produce it.
- **Disposition:** **Tighten invariant.**

### F-02 — “Exact substring” has no canonical comparison definition

- **Location:** AD-2 rule 1, lines 103–104.
- **Trigger condition:** Unit A compares Unicode-normalized code points and preserves offsets; Unit B compares whitespace-normalized text before storing the displayed snippet.
- **Guard:** Specify the exact normalization algorithm, Unicode form, newline/whitespace policy, case policy, encoding, and whether offsets refer to bytes, code points, or grapheme clusters; persist the canonical text hash.
- **Consequence:** Both services report “100% exact” while disagreeing on whether a citation is valid or where it starts.
- **Disposition:** **Tighten invariant.**

### F-03 — A block ID does not uniquely identify repeated evidence

- **Location:** AD-2 rule 2, lines 104–105; `EVIDENCE_CITATION` lines 303–311.
- **Trigger condition:** The same sentence appears twice in one Markdown block or in multiple blocks, and each unit resolves a different occurrence.
- **Guard:** Require a canonical anchor such as `(artifact_hash, markdown_block_id, start_offset, end_offset)` plus an occurrence ordinal when needed; validate the range on read as well as write.
- **Consequence:** A valid snippet can highlight the wrong occurrence, undermining the evidence claim without violating exact-text validation.
- **Disposition:** **Tighten invariant.**

### F-04 — `EvidenceMapping` is referenced but not defined

- **Location:** AD-1 lines 96–97; AD-2 lines 103–104; AD-7 line 144; ERD lines 248–350.
- **Trigger condition:** Unit A creates a mapping parent with status/run metadata; Unit B treats `EvidenceCitation` as the mapping itself.
- **Guard:** Define the entity, cardinality, required keys, lifecycle, active-run rule, and whether a mapping is per criterion, application, or processing run.
- **Consequence:** Foreign keys, queries, retry promotion, and “completed mapping” semantics cannot be implemented consistently.
- **Disposition:** **Tighten invariant.**

### F-05 — Reviewer logs lack criterion-level identity in the ERD

- **Location:** AD-3 lines 106–112; `REVIEW_LOG` lines 313–320.
- **Trigger condition:** Unit A stores one review row per `(reviewer, criteria_item)`; Unit B stores one application-level row whose status covers several criteria.
- **Guard:** Add non-null `criteria_item_id` (and, if calibration samples are distinct, `sample_application_id`) to `ReviewLog`; enforce one current submission per reviewer/item/version.
- **Consequence:** A deterministic conflict cannot be reliably attributed to the criterion that differs, and handoff provenance becomes ambiguous.
- **Disposition:** **Tighten invariant.**

### F-06 — Citation provenance can be structurally valid but referentially weak

- **Location:** AD-3 rule 1, lines 110–111; ERD `REVIEW_LOG` lines 313–320.
- **Trigger condition:** Unit A uses a join table; Unit B stores a JSON array of snippet IDs, with no declared FK enforcement or snapshot hash.
- **Guard:** Define `ReviewerLogCitation(review_log_id, citation_id)` with FK constraints, and record the citation/artifact version seen at submission.
- **Consequence:** Deleted, replaced, or cross-application citations can remain in a review log and appear to be the reviewer’s original evidence.
- **Disposition:** **Tighten invariant.**

### F-07 — Deterministic diff does not mean deterministic semantics

- **Location:** AD-3 rule 2, lines 111–112.
- **Trigger condition:** Unit A compares citation sets; Unit B compares ordered citation arrays; missing status and duplicate citations are treated differently.
- **Guard:** Define comparison keys, null/missing behavior, duplicate handling, ordering, status equivalence, and the exact `ConflictItem` schema. The server must emit the same conflict IDs/content for the same immutable inputs.
- **Consequence:** Re-running calibration can create different conflicts or falsely clear an unresolved disagreement.
- **Disposition:** **Tighten invariant.**

### F-08 — Reviewer ownership is represented only by a role

- **Location:** AD-3 lines 110–111; `REVIEW_LOG` lines 313–320; Deferred item 1, lines 393–395.
- **Trigger condition:** Unit A records immutable `reviewer_id` plus role-at-submission; Unit B treats the HR/Tech toggle as the author identity.
- **Guard:** Require immutable actor ID, role-at-submission, created/updated timestamps, and an append-only or versioned review submission. Keep full RBAC/SSO out of MVP if desired, but do not defer authorship integrity.
- **Consequence:** A role toggle can overwrite or impersonate an independent reviewer, invalidating the calibration and audit trail.
- **Disposition:** **Tighten invariant** for authorship; full multi-tenant RBAC/SSO remains **Deferred** as already stated.

### F-09 — Conflict source of truth is unspecified

- **Location:** AD-3 line 112; `HANDOFF_CARD.hr_tech_conflicts` lines 322–328.
- **Trigger condition:** Unit A stores normalized `ConflictItem` rows; Unit B stores a copied JSON snapshot on the handoff.
- **Guard:** Choose one canonical conflict representation and define a snapshot relation: either handoff references immutable conflict records, or the JSON schema includes source review IDs, citation IDs, criteria version, and a snapshot hash.
- **Consequence:** Later reads can disagree with the handoff shown at decision time, and conflict corrections cannot be audited.
- **Disposition:** **Tighten invariant.**

### F-10 — Approval immutability and revocation are underdefined

- **Location:** AD-1 title and rules, lines 92–98; criteria status convention, lines 152–153.
- **Trigger condition:** Unit A makes an approved version immutable and creates a new version for edits; Unit B edits approved criteria in place or archives it after handoffs exist.
- **Guard:** Forbid mutation of approved criteria content and version identity. Define whether `ARCHIVED` affects existing handoffs, new reviews, reads, and final decisions; preserve the approval actor/time.
- **Consequence:** A previously generated card can no longer be reproduced from the criteria version it names.
- **Disposition:** **Tighten invariant.**

### F-11 — Preview gating is not defined as a persisted server-side property

- **Location:** AD-1 rule 2, lines 97–98; AD-6 line 135.
- **Trigger condition:** Unit A persists `preview_mode` and rejects all official writes server-side; Unit B derives a watermark in the client from the latest criteria status.
- **Guard:** Make preview/official mode server-authoritative, persist the mode and criteria status snapshot on every exploratory artifact, and reject official creation and finalization on the API regardless of client claims.
- **Consequence:** A stale client or direct API caller can present an exploratory result as official or create a final decision after criteria state changes.
- **Disposition:** **Tighten invariant.**

### F-12 — Processing states do not define the retry transition graph

- **Location:** AD-6 rule 4, lines 135–136; AD-7 rule 3, lines 143–144; `APPLICATION.processing_status` lines 277–287.
- **Trigger condition:** Unit A creates a new run and atomically promotes it; Unit B mutates the same application from `FAILED_MAPPING` back to `MAPPING` while old mapping rows remain.
- **Guard:** Define legal transitions, retry command semantics, whether retry reuses the application ID, and which run/artifact set is active. State explicitly that reads select only the promoted successful run.
- **Consequence:** Old and new mappings can be mixed, or a failed retry can hide a valid prior result without a reproducible snapshot.
- **Disposition:** **Tighten invariant.**

### F-13 — Partial mapping isolation is asserted but not modeled

- **Location:** AD-7 rules 3–4, lines 143–144; `EVIDENCE_MAPPING` omission in the ERD.
- **Trigger condition:** Unit B inserts valid mappings before a later citation fails; Unit A writes the entire mapping set transactionally.
- **Guard:** Add `processing_run_id` and mapping status, write to a non-active run, and expose mappings only after an atomic completion/promotion transaction. Define cleanup/retention for failed partial rows.
- **Consequence:** A future endpoint that forgets the application-status filter can expose incomplete or mixed evidence.
- **Disposition:** **Tighten invariant.**

### F-14 — Provider retry identity and idempotency are absent

- **Location:** AD-7 rules 2–3, lines 142–143; `PROCESSING_RUN` lines 289–301.
- **Trigger condition:** A provider call times out after acceptance; the bounded retry submits the same document again and receives a second result.
- **Guard:** Use a stable idempotency key per `(application, artifact_set, stage, logical attempt)` where providers support it; otherwise deduplicate by request fingerprint and define which response wins. Store every attempt as an immutable call record.
- **Consequence:** Duplicate parsing/mapping can produce conflicting Markdown, citations, cost, and audit histories.
- **Disposition:** **Tighten invariant.**

### F-15 — Processing-run fields cannot fully reproduce the input to a result

- **Location:** AD-7 rule 2, lines 141–143; `PROCESSING_RUN` lines 289–301; PRD baseline requirements referenced by the spine.
- **Trigger condition:** Unit A stores prompt/template hash, provider parameters, model snapshot, and artifact hashes; Unit B stores only the fixed model name and request ID.
- **Guard:** Persist model snapshot/version, prompt or prompt hash, relevant parameters, input artifact hashes, output hash, and provider request metadata for every runtime result. Keep the broader PB-02 comparison set deferred if necessary.
- **Consequence:** The system cannot explain why the same application produced different evidence or questions.
- **Disposition:** **Tighten invariant** for runtime provenance; PB-02 multi-run comparison remains **Deferred**.

### F-16 — API secrets can leak despite server-only configuration

- **Location:** AD-6 rules 2–3, lines 132–134; runtime configuration lines 187–189.
- **Trigger condition:** A provider error, debug log, exception, request URL, client bundle, or crash dump contains an API key or a URL embedding credentials.
- **Guard:** Load secrets only in server process memory; prohibit logging/serializing secret values and authorization headers; redact provider errors; validate that base URLs are not user-controlled; restrict `.env` permissions and exclude it from artifacts, images, and commits; fail closed when a secret is missing.
- **Consequence:** A demo log or browser response can expose provider credentials or enable calls to an attacker-controlled endpoint.
- **Disposition:** **Tighten invariant.**

### F-17 — Raw Markdown and PDF confidentiality/integrity controls are missing

- **Location:** AD-2 lines 103–105; AD-6 line 132; AD-7 lines 141–144; file storage lines 69–72 and 184–189.
- **Trigger condition:** A resume PDF or raw Markdown is readable through a guessed path, shared local directory, backup, or an unscoped application/citation ID.
- **Guard:** Store opaque server-side object IDs rather than user paths, enforce application-scoped authorization on every file/evidence read, use restrictive filesystem permissions, record content hashes and size/type limits, and define retention/deletion behavior for PII. Do not put raw Markdown in client logs or URLs.
- **Consequence:** Applicant PII can be disclosed or silently altered while citations still appear linked.
- **Disposition:** **Tighten invariant** for MVP access and integrity; broader tenant isolation/retention policy can be **Deferred** only with an explicit risk acceptance.

### F-18 — PDF-only input is not a trustworthy content-validation rule

- **Location:** AD-6 rule 1, lines 132–133; upload flow lines 217–220.
- **Trigger condition:** Unit B accepts a file named `.pdf` or with `application/pdf` while Unit A validates the magic bytes and parser result.
- **Guard:** Enforce maximum size, content signature, parser-safe handling, filename/path sanitization, and storage outside the static web root; reject malformed/encrypted/unsupported PDFs with a typed failure stage.
- **Consequence:** Non-PDF payloads, path traversal, or parser bombs can reach the pipeline and contaminate stored artifacts or exhaust the demo service.
- **Disposition:** **Tighten invariant.**

### F-19 — Question provenance permits a free-text-only candidate

- **Location:** AD-5 rule 1, lines 124–126; `INTERVIEW_QUESTION_CANDIDATE` lines 330–343; `QUESTION_EVIDENCE` lines 345–349.
- **Trigger condition:** Unit A requires a criterion and evidence/conflict source; Unit B supplies only `concern_text`, which satisfies the written “criteria item, concern, or evidence” alternative.
- **Guard:** Replace the free-text alternative with a typed provenance object: source review/conflict/criteria IDs, source citation IDs when the concern derives from evidence, source artifact hash, and generation run. Require at least one stable source ID; display the provenance with the question.
- **Consequence:** A plausible question can enter the final handoff with no auditable reason or evidence trail.
- **Disposition:** **Tighten invariant.**

### F-20 — Question generation has no idempotency or source snapshot

- **Location:** Question contract lines 160–172; flow lines 238–245; AD-5 lines 124–126.
- **Trigger condition:** The browser retries `POST /api/handoff/{handoff_id}/questions/generate` or two reviewers invoke it concurrently.
- **Guard:** Require an idempotency key or deterministic generation fingerprint over handoff, criteria version, review/conflict snapshot, and model/prompt snapshot; return the existing generation result for duplicates and record a generation run.
- **Consequence:** Duplicate candidates, inconsistent provenance, and non-repeatable question lists appear on one handoff.
- **Disposition:** **Tighten invariant.**

### F-21 — Candidate creation timing is inconsistent with the API contract

- **Location:** AD-5 line 124; question endpoint table lines 164–170; sequence lines 238–245.
- **Trigger condition:** Unit A creates candidates as part of handoff creation; Unit B creates the handoff first and generates questions later through the separate endpoint.
- **Guard:** Define whether handoff creation is atomic with candidate generation. If generation is asynchronous/separate, expose `questions_status`, source snapshot IDs, and a rule that the handoff is not final until generation succeeds or is explicitly marked unavailable.
- **Consequence:** A handoff may be displayed as complete while its questions are absent, stale, or based on a later review state.
- **Disposition:** **Tighten invariant.**

### F-22 — Question selection is either live or snapshotted, with no canonical read model

- **Location:** AD-5 rule 3, lines 126–127; question transition text lines 172–172; flow lines 242–245.
- **Trigger condition:** Unit A snapshots selected IDs into the handoff; Unit B dynamically queries current `SELECTED` rows.
- **Guard:** Define a finalization operation and immutable selected-question snapshot containing question IDs, text hashes, editor versions, and selection actor/time. Clarify whether later edits update the final handoff or create a new revision.
- **Consequence:** The same handoff ID can show different interview questions at different times, defeating decision-log reproduction.
- **Disposition:** **Tighten invariant.**

### F-23 — Soft deletion has unsafe transition and authorization semantics

- **Location:** AD-5 rule 2, lines 125–126; question endpoint table lines 167–172; candidate fields lines 330–343.
- **Trigger condition:** Unit A rejects edits/selections after deletion; Unit B permits a selected question to be deleted and does not define restore, deleted-by, or delete reason.
- **Guard:** Specify legal transitions, including whether `SELECTED -> DELETED` is allowed; enforce deleted rows as non-editable/non-selectable/non-finalizable; record `deleted_by`, `deleted_at`, reason, and audit event; make DELETE idempotent and prevent deleted rows from being resurrected by generation.
- **Consequence:** A deleted question can remain in a cached/final snapshot, be selected again, or disappear without explaining who removed it and why.
- **Disposition:** **Tighten invariant.**

### F-24 — Soft-deleted rows can collide with regeneration

- **Location:** AD-5 lines 124–126; question generation endpoint lines 164–170.
- **Trigger condition:** Unit B excludes deleted rows from GET, then regeneration creates a semantically duplicate candidate while the deleted row remains in the database.
- **Guard:** Add a generation fingerprint/source snapshot and uniqueness rule that includes active/deleted history; define whether regeneration creates a new revision or reopens the old candidate, never an unexplained duplicate.
- **Consequence:** Reviewers see repeated questions and cannot tell whether a deleted question was regenerated or independently proposed.
- **Disposition:** **Tighten invariant.**

### F-25 — Final decision provenance is not modeled

- **Location:** AD-1 lines 94–98; AD-3/AD-5; FR-017/FR-018 source requirements; `HANDOFF_CARD` lines 322–328.
- **Trigger condition:** Unit A creates an append-only decision record; Unit B stores interview feedback as a mutable `HandoffCard.interview_feedback` field.
- **Guard:** Define a decision/interview-result entity with criteria version, handoff revision, selected-question snapshot, reviewer/decision actor, evidence/conflict snapshot, timestamps, and immutable event history.
- **Consequence:** The system can show a current feedback string but cannot reproduce the final decision or distinguish post-decision edits.
- **Disposition:** **Tighten invariant** if FR-017/FR-018 are MVP; otherwise add an explicit **Deferred** item rather than leaving the shape ambiguous.

### F-26 — API envelope and RFC-7807 semantics can diverge

- **Location:** Consistency conventions lines 154–155; AD-1 error example line 98; question endpoints lines 164–170.
- **Trigger condition:** Unit A returns `{success:false,data:null,error:{...}}`; Unit B returns bare `application/problem+json` for the same failure.
- **Guard:** Choose one wire contract, document content type/status/code/message fields, and specify whether RFC-7807 is nested in the standard envelope. Add contract tests for 403/422, not-approved, stale version, not-found, and retryable failure.
- **Consequence:** The frontend may treat a blocked official handoff as a generic network error or incorrectly display an error as successful data.
- **Disposition:** **Tighten invariant.**

### F-27 — Location coordinates and fallback payload are underspecified

- **Location:** AD-2 line 104; AD-4 lines 117–118; `bbox_coordinates` line 310.
- **Trigger condition:** Unit A uses one-based page numbers and PDF points; Unit B uses zero-based pages and normalized `[0,1]` coordinates; both emit the allowed shape.
- **Guard:** Define page numbering, coordinate origin/units, rotation/crop-box treatment, null semantics, and the schema for `context_box` including context range and artifact hash.
- **Consequence:** A citation can be exact but highlight the wrong location or silently fall back when a coordinate is technically present.
- **Disposition:** **Tighten invariant.**

### F-28 — Citation selection is not scoped by application and artifact

- **Location:** AD-4 lines 117–118; `EVIDENCE_CITATION` lines 303–311; source tree/API boundary lines 352–375.
- **Trigger condition:** Unit B accepts an `active_citation_id` and resolves it globally; Unit A verifies application, handoff, and artifact ownership.
- **Guard:** Every citation read/focus request must authorize the application, criteria version, handoff, and active artifact set; reject orphaned or stale citation IDs.
- **Consequence:** A reviewer can view another applicant’s evidence or focus a PDF on a citation from a different processing run.
- **Disposition:** **Tighten invariant.**

### F-29 — Identifier format does not guarantee uniqueness

- **Location:** ID naming convention lines 152–153; `crit_ver_<timestamp>` and entity PKs in the ERD.
- **Trigger condition:** Unit A uses UUIDs; Unit B uses timestamp precision insufficient for concurrent criteria versions or retries.
- **Guard:** Require database-enforced uniqueness and collision-safe opaque IDs; treat the naming convention as presentation only, not as the identity algorithm.
- **Consequence:** Records can overwrite, foreign keys can point to the wrong version, or concurrent approval requests can bind to different content under one ID.
- **Disposition:** **Tighten invariant.**

### F-30 — Existing deferred scope is acceptable only if the boundary is explicit

- **Location:** Deferred items 1–4, lines 391–397; AD-6/AD-7 operational requirements.
- **Trigger condition:** A team interprets “single workspace,” “no queue,” or “PB-02 deferred” as permission to omit server authorization, run audit, or bounded retries.
- **Guard:** Keep the explicit deferrals: full multi-tenant permissions/SSO, ATS, large queue, and PB-02 comparison. State that they do not defer server-side role checks for the two MVP roles, immutable processing audit, bounded retry, or runtime provenance.
- **Consequence:** A non-goal becomes an excuse to weaken core evidence and ownership integrity.
- **Disposition:** **Deferred** only for the listed product scope; the boundary clarification is a **Tighten invariant**.

## Disagreements that can be ignored after the contract is fixed

These are real implementation differences, but they do not threaten interoperability if the external contracts above are made canonical:

- SQLAlchemy versus SQLModel (line 189).
- Whether the frontend splits calibration/split/handoff into separate components or shares a view (lines 352–375).
- UUID versus another collision-safe opaque ID encoding, provided database uniqueness and the public format are fixed (lines 152–153).
- Retry backoff values within the configured timeout/retry bounds, provided attempt recording, idempotency, and promotion rules from F-12–F-15 are fixed (AD-7 lines 142–144).
- Normalized relational conflict storage versus an immutable JSON projection, provided F-09 defines the source of truth and snapshot hash.

## Deferred items that remain valid

- Exact interview-question count may remain deferred as D-01, but provenance, idempotency, selection, deletion, and finalization semantics may not be deferred with it.
- Large asynchronous queue infrastructure may remain deferred for the five-day demo, but the bounded state machine and retry isolation are required even for synchronous/background-task execution.
- Full multi-tenant authorization and SSO may remain deferred, but actor identity, role-at-submission, application scoping, and server-side MVP authorization are required.
- PB-02 broad baseline comparison may remain deferred, but every runtime processing/question generation result still needs enough prompt/model/input metadata to be explained.

## Minimum contract-tightening set before two teams split

1. Define versioned artifact sets and canonical evidence anchors/hashes.
2. Complete the missing `EvidenceMapping`, `ConflictItem`, reviewer-citation, and decision entities.
3. Add criterion-level review identity, immutable actor ownership, and deterministic diff rules.
4. Publish the processing/run state graph, retry idempotency key, active-run promotion transaction, and read isolation rules.
5. Publish one API envelope/error contract and one location/fallback coordinate contract.
6. Replace question free-text provenance with stable source IDs; define generation idempotency and final-question snapshotting.
7. Make soft deletion terminal and auditable, including regeneration/uniqueness behavior.
8. Add secret redaction/base-URL validation and scoped, integrity-checked storage access for PDF/Markdown.

No changes were made to the architecture spine.
