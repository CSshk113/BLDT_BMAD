---
name: 'Zero100_Builderthon'
type: final-adversarial-compatibility-data-integrity-review
subject: 'ARCHITECTURE-SPINE.md'
reviewed: '2026-08-27'
---

# Final Adversarial Compatibility/Data-Integrity Review

## Verdict

**FAIL — parallel implementation is not safe until the contracts below are tightened.**

Two independently built units can satisfy the written AD-1 through AD-9 and the listed fields while still producing non-interoperable or unsafe records. Unit A below is immutable, relational, and snapshot-oriented. Unit B uses current pointers, permissive joins, and dynamic projections. The divergence is caused by missing canonical constraints and lifecycle/wire semantics, not by optional technology choices.

## Independently constructed units

| Area | Unit A | Unit B | Resulting divergence |
|---|---|---|---|
| Evidence | Immutable artifact-set and run-scoped anchors; composite parent checks | Mutable application paths; mapping/citation resolved against the current normalized document | A citation can remain exact but point to a different document revision or run |
| Reviews/conflicts | One versioned submission per reviewer/item; conflict has explicit resolver and source snapshot | Multiple rows per reviewer/item; conflict pairs the rows selected by a query and stores a resolution note | The same calibration data yields different owners, conflict identity, and approval eligibility |
| Processing | Logical retry group with an atomic promoted run/artifact set | Independent `ProcessingRun` rows plus `is_current` mapping flags | A failed retry can hide a prior success, or a partial/new run can be selected as current |
| Questions | Provenance object and immutable selected-question snapshot | Free-text concern provenance and dynamic selected-row projection | The same question list can have different sources and change after handoff/verification |
| Interview/decision | Time/version snapshots with append-only events | Current question/card joins and mutable feedback/decision rows | Later edits or deletions change the meaning of past verification and decisions |
| API/roles | Server-enforced RBAC and one envelope contract | UI role toggle and a separate RFC-7807 response shape | Clients and authorization behavior are incompatible at the boundary |

## Critical findings

### C-01 — Evidence identity is not anchored to an immutable artifact set

**Location:** AD-2 rules 1–3 (lines 103–106), AD-7 rules 1–4 (lines 144–147), `APPLICATION` and `PROCESSING_RUN`/`EVIDENCE_MAPPING`/`EVIDENCE_CITATION` entities (lines 351–402).

**Construction:** Unit A gives every PDF, raw Markdown, normalized Markdown, mapping, and citation an immutable artifact-set/revision identity. Unit B keeps `original_pdf_path`, `raw_markdown_path`, and `normalized_markdown_path` on `APPLICATION`, replaces the normalized path on retry, and uses `normalized_text_hash` as the citation identity check. Both retain raw artifacts and record a processing run, so both can claim to obey AD-2 and AD-7.

The ERD has no artifact/document revision entity or foreign key. `input_fingerprint` is only a field on `PROCESSING_RUN`; it is not bound to the Markdown object used by a citation. `EVIDENCE_CITATION` reaches the run only indirectly through `EVIDENCE_MAPPING`, and the database shape does not prove that the mapping’s application, criteria version, criteria item, and source run are the same parent tuple. `is_current` is also an unscoped boolean rather than a constrained active-run relation.

**Impact:** After reprocessing, the same citation may still pass exact-substring validation while being resolved against a different normalized document, criteria version, or run. `GET /evidence` can therefore return evidence that is internally text-valid but not the evidence used to produce the displayed mapping. This breaks reproducibility and can contaminate a handoff or decision.

**Required contract:** Introduce immutable artifact/document revision records with content hashes and an explicit artifact-set ID. Bind processing runs, mappings, and citations to that set. Enforce composite parent consistency for application/version/item/run and a database-defined uniqueness rule for the single promoted current mapping set.

### C-02 — Criteria-version immutability and reviewer/conflict ownership are not enforceable

**Location:** AD-1 rules 1–3 (lines 96–98), AD-3 rules 1–2 (lines 112–113), `CRITERIA_VERSION`/`CRITERIA_ITEM`/`REVIEW_LOG`/`CONFLICT_ITEM` entities (lines 336–434), calibration flow (lines 254–262).

**Construction:** Unit A treats an approved criteria version and its item set as an immutable snapshot, allows one current submission per reviewer/item/version, and records conflict ownership/resolution as an append-only actor event. Unit B allows multiple `REVIEW_LOG` rows for the same reviewer, item, and version, then selects “the current” HR and TECH rows in service code; it marks `CONFLICT_ITEM.status = RESOLVED` with only a note and timestamp. Both retain independent reviewer records and compute conflicts server-side, satisfying the prose of AD-1 and AD-3.

There is no uniqueness/current-submission rule for `REVIEW_LOG`, no resolver identity or resolution event, no conflict scope/version snapshot, and no conflict-resolution endpoint or authorized owner contract. `CONFLICT_ITEM` hardcodes `hr_review_log_id` and `tech_review_log_id`, but does not define how multiple submissions are paired. `CRITERIA_ITEM` has no immutable content/version hash and the model does not enforce that an item belongs to the same version named by a review or conflict. The approval rule depends on “unresolved conflict” without defining whether a stale, superseded, or unpaired conflict blocks approval.

**Impact:** The same reviewer inputs can yield different canonical conflict IDs and different approval eligibility. A later review can silently replace the row that a prior conflict cites, or a conflict can be marked resolved without an identifiable authorized owner. Editing an approved item in place also changes the criteria named by prior evidence, reviews, handoffs, and decisions.

**Required contract:** Define immutable criteria snapshot identity and approval actor/time; enforce criterion-to-version and review-to-parent composite integrity; define one current/versioned submission per reviewer/item; define deterministic conflict pairing and comparison keys; and add append-only conflict resolution with resolver identity, timestamp, and authorization.

### C-03 — Retry identity, failed-run isolation, and current-result promotion are underspecified

**Location:** AD-6 rule 4 (lines 135–138), AD-7 rules 2–4 (lines 145–147), `PROCESSING_RUN` and `EVIDENCE_MAPPING` (lines 363–402), retry/evidence API contracts (lines 198–200 and 207).

**Construction:** Unit A models a logical processing attempt with a parent retry group, stage-specific attempt records, immutable artifact set, and one transaction that promotes a successful run. Unit B creates independent `PROCESSING_RUN` rows with `attempt_no`, writes mappings as they arrive, updates `APPLICATION.processing_status`, and makes the latest successful rows current by query or by toggling `is_current`. Both use bounded retries, retain failed runs, and never deliberately promote a known partial result.

The ERD has no logical-run parent, no current promoted run/artifact-set FK on `APPLICATION`, no stage-scoped uniqueness for `idempotency_key`, no uniqueness for one active mapping per `(application, criteria_version, criteria_item)`, and no defined transition graph for retrying a completed application. “Latest successful” is not defined as run ID, attempt number, completion time, or an atomic promotion record. The contract also does not say whether a failed retry preserves a prior completed result or makes the application failed and hides that prior result.

**Impact:** A timeout-after-acceptance or a failed mapping retry can create duplicate provider work, mix parsing artifacts from one run with mappings from another, or make a previously valid result disappear. Different readers can select different “current” mappings while all rows remain individually valid.

**Required contract:** Define the state-transition graph, logical retry identity and uniqueness scope, provider-attempt relation, artifact set per run, cleanup/retention of partial rows, and an atomic promotion record. `GET` operations must select only that promoted result; a failed retry must have an explicit prior-success visibility rule.

## High findings

### H-01 — Exact evidence and location semantics are not canonical

**Location:** AD-2 rules 1–2 (lines 103–105), AD-4 rule 2 (lines 119–120), `EVIDENCE_CITATION` (lines 382–392), consistency conventions (lines 169–175).

Unit A can compare Unicode-normalized code points with one-based offsets and PDF-point coordinates. Unit B can compare whitespace-normalized strings with byte offsets and zero-based normalized coordinates. Both can report a 100% exact substring and emit the permitted `{ page_number?, location?, bounding_box? }` shape. The spine does not define Unicode/newline/whitespace/case/encoding policy, offset units, page numbering, coordinate origin/units, rotation/crop-box handling, or the actual `context_box` schema. `markdown_block_id` also does not disambiguate repeated text occurrences.

**Impact:** Identical source data can produce different citation identity, offsets, or highlights; a citation may focus the wrong repeated occurrence or silently fall back despite coordinates being present.

**Required contract:** Publish one canonical normalization and offset algorithm, anchor tuple and occurrence rule, hash scope, and typed location/fallback schema. Validate the anchor on both write and read.

### H-02 — Question provenance and generation idempotency can collapse into free text

**Location:** AD-5 rules 1 and 4 (lines 126–129), question entity/joins (lines 445–468), question generation contract (lines 181–191 and 207).

Unit A requires stable criterion/review/conflict/citation source IDs and snapshots the generation input. Unit B creates a candidate with `concern_type = OTHER` and `concern_text`, optionally omits `criteria_item_id`, and stores no source review/conflict ID or generation-run ID. Both satisfy the written alternative “criteria, concern, or evidence” and the nullable ERD fields. The generation key uses `handoff_id + source_revision + prompt_version`, but `source_revision` has no defined content/snapshot semantics, and the endpoint has no required idempotency header or duplicate-response behavior.

**Impact:** A plausible candidate can be selected without an auditable source identity, and retried/concurrent generation can create duplicate or materially different candidates under the same handoff. Two clients cannot reliably determine whether a candidate is a repeat, a regeneration, or a new source revision.

**Required contract:** Replace free-text-only provenance with typed source IDs and source artifact/review/conflict snapshots; define the generation input projection, prompt/model/run metadata, uniqueness, idempotency key, and replay response.

### H-03 — Candidate lifecycle and final-question finalization are ambiguous

**Location:** AD-5 rules 2–3 (lines 127–129), question state transition text and endpoints (lines 186–191), handoff entity (lines 436–443), AD-8 rule 3 (lines 153–155).

Unit A treats selection as a finalization boundary, snapshots selected question IDs/text hashes and selection actor/time into the handoff, and makes deletion terminal. Unit B dynamically projects all non-deleted `SELECTED` rows, permits `SELECTED → DELETED`, and allows selected-question edits to change what a previously displayed handoff contains. Both preserve `original_question_text` and implement soft delete as required.

The stated transition list describes `CANDIDATE → SELECTED` or `CANDIDATE → DELETED`, but the DELETE endpoint does not say whether a selected row may be deleted. There is no finalization endpoint, selected-question snapshot, deletion actor/reason, edit revision, or rule for regeneration against deleted history.

**Impact:** The final interview list can change after selection, verification, or decision; a deleted question may remain in a cached/final projection or be regenerated as an unexplained duplicate. The same `handoff_id` is not a stable artifact for downstream consumers.

**Required contract:** Define legal transitions and authorization, make deleted rows non-editable/non-selectable/non-finalizable, record deletion/edit events, and define whether finalization snapshots or creates a new handoff revision.

### H-04 — Interview verification has no time/version identity and is not truly append-only

**Location:** AD-8 rules 1 and 3 (lines 153–155), verification API (line 204), `INTERVIEW_VERIFICATION` entity (lines 470–480).

Unit A records the selected-question snapshot, criteria version, handoff revision, and a new immutable verification event for every correction. Unit B stores the current `question_id` and `handoff_card_id`, edits or deletes the question later, and treats multiple rows or the last row as the append-only history. Both link verification to a question and separate `initial_hypothesis_snapshot` from `interview_finding`.

The verification entity has no criteria-version FK, source revision, selected-at-time snapshot, event sequence/supersession field, or uniqueness/history rule. It therefore cannot prove which question text, criterion, evidence, or handoff revision was verified. The rule forbidding unselected/deleted questions has no temporal semantics: it is unclear whether selection is checked at write time, at read time, or for existing records after a later deletion.

**Impact:** Editing or deleting a question can rewrite the apparent meaning of an old interview result, and two implementations can show different verification histories for the same handoff.

**Required contract:** Bind verification to an immutable handoff/question/criteria snapshot, capture question text hash and selection state at recording time, define append-only event ordering and correction semantics, and make read projections deterministic.

### H-05 — Decision records can be cross-wired and have no stable final-decision projection

**Location:** AD-8 rule 2 (lines 154–155), AD-9 rule 2–3 (lines 162–163), decision API (line 205), `DECISION_RECORD`/`DECISION_CITATION` (lines 482–497).

Unit A accepts a decision only for an official handoff whose application, criteria version, promoted evidence snapshot, selected-question snapshot, and verification snapshot all match; it stores an immutable decision event and explicit evidence set. Unit B accepts the application-level endpoint, joins any supplied `handoff_id` and `criteria_version_id` through independent FKs, and exposes the newest or all decision rows. Both use a human actor and append rows, satisfying the human-entry and append-only prose.

The ERD does not enforce that the three parent IDs describe the same application/version/card. `DECISION_CITATION` is optional in the shape even though AD-8 requires a decision connection to original evidence. There is no official handoff/status field, handoff revision, selected-question/verification snapshot, active/superseded decision rule, or endpoint request schema that binds the decision to a specific handoff.

**Impact:** A human decision can be attached to the wrong card or criteria version, lack evidence, or be rendered differently depending on whether a client selects the latest row or the full append-only history. The decision cannot be reproduced from the named IDs alone.

**Required contract:** Use composite parent constraints and a handoff-specific decision command; require a matching approved/official snapshot and required evidence relation; define immutable decision events and a deterministic current/final projection.

### H-06 — Role and ownership semantics omit the Lead and are not endpoint-complete

**Location:** AD-9 rule 2 (line 162), `REVIEW_LOG` (lines 404–414), `INTERVIEW_VERIFICATION`/`DECISION_RECORD` (lines 470–491), sequence actors (lines 246–248 and 293–298), Deferred item 1 (lines 536–537).

Unit A uses an authenticated actor identity with role-at-submission and server-side permissions: HR/TECH own review submissions, Lead can read/verify, and only an explicitly authorized decision actor can record a decision. Unit B implements the deferred HR/Tech role toggle, treats `reviewer_id`, `recorded_by`, and `created_by` as client strings, and grants the same generic “authorized person” path to verification and decision. Both can claim to keep full SSO/multi-tenancy deferred and to protect reviewer logs at a nominal API layer.

The only role enum is `HR | TECH`; Lead exists only as a sequence-diagram actor. No actor/role entity, role-at-event field for verification/decision, read matrix, ownership rules for handoff/question/conflict resolution, or per-endpoint authorization contract is defined.

**Impact:** Independently built clients disagree on who may read or mutate evidence, resolve conflicts, select questions, record verification, and decide. A UI toggle or caller-supplied role can impersonate an owner or allow a Lead action to be treated as a reviewer action.

**Required contract:** Define MVP actors and endpoint-level read/write permissions, require server-derived immutable actor identity and role-at-submission, and keep SSO/multi-tenant expansion deferred without deferring authorship and authorization integrity.

### H-07 — API envelope and endpoint contracts are mutually interpretable

**Location:** AD-1 HTTP error rule (line 97), AD-9 rule 2 (line 162), data-envelope/error conventions (lines 169–175), sequence flow (lines 285–298), question and core API tables (lines 183–207).

Unit A returns every failure, including 403/422, inside `{ success:false, data:null, error:{code,message}, correlation_id }` and nests or maps RFC-7807 fields according to one documented media type. Unit B returns bare `application/problem+json` RFC-7807 objects for failures and the success envelope only for successful calls. Both can read “standard error envelope,” “RFC 7807 compatible,” and the explicit 403/422 requirement as satisfied.

The convention does not define HTTP status/content type, `type/title/status/detail/instance` mapping, error extensions, or whether RFC-7807 is nested. More importantly, the sequence calls `POST /api/handoff/generate` (line 285), while the question table defines only `POST /api/handoff/{handoff_id}/questions/generate`; the handoff-card creation endpoint is absent. Upload/retry/question-generation idempotency is asserted, but request headers, persistence scope, fingerprint mismatch behavior, and replay response are not specified.

**Impact:** A frontend generated by one unit cannot reliably decode failures from the other, and the two units can implement different handoff creation flows and duplicate behavior while both conform to the document’s tables/diagram.

**Required contract:** Publish one OpenAPI-level request/response contract, exact status/media-type/envelope rules, RFC-7807 mapping, correlation behavior, and the canonical handoff creation versus question-generation endpoints. Add idempotency persistence and mismatch/replay semantics.

## Required disposition

Do not split implementation ownership on the current spine. First publish the canonical identity tuple and composite constraints, processing promotion/state machine, reviewer/conflict ownership model, question/verification/decision snapshot lifecycles, MVP role matrix, and one API wire contract. The architecture spine was not modified by this review.
