# Final Adversarial Review R4

## Verdict

**REVISE/FAIL — do not pass the final gate.**

The current source documents contain unresolved interoperability contracts. Two reasonable implementations can both claim conformance while producing incompatible processing states, provenance, citation links, calibration results, API behavior, revisions, and handoff snapshots.

Only the three current source documents were reviewed:

- `ARCHITECTURE-SPINE.md`
- `PRESENTATION-SYSTEM-DESIGN.md`
- `prd.md`

Old review files were ignored. No source document was edited.

## Adversarial construction

Implementation A uses mutable logical runs, derives question citations server-side, treats conflict snapshots as display projections, and uses service-level “current” checks. Implementation B uses terminal per-stage runs/attempts, requires citation IDs in generated question output, stores full conflict-pair snapshots, and uses database-enforced current-row constraints. The documents do not choose between these behaviors or provide enough constraints for the two implementations to interoperate.

## Phase-blockers — unresolved interoperability issues

### PB-01 — Processing-run retry state machine is contradictory

**Severity:** Critical  
**Location:** `ARCHITECTURE-SPINE.md:141-152, 320`

The document requires retrying a failed stage within the same logical `PROCESSING_RUN`, but also permits only `QUEUED → STARTED → SUCCEEDED|FAILED`. It never defines `FAILED → STARTED` or a separate retrying state. Implementation A reopens a terminal run; Implementation B creates another run. Both conflict with part of the stated contract.

**Required correction:** Define one run-level and one attempt-level state machine, including the exact retry transition, ownership/CAS rule, and whether a retry keeps or replaces the logical run.

### PB-02 — Attempt numbering and provider polling scope are incompatible

**Severity:** Critical  
**Location:** `ARCHITECTURE-SPINE.md:148-152, 598-608, 320`

Attempts are described as per-provider-call and per-stage, while uniqueness is `(processing_run_id, attempt_no)` and `PROCESSING_RUN` also has `attempt_no`. Parsing and mapping can both naturally begin at attempt 1, causing a collision, or use a global number and lose the stated stage-local meaning. LlamaParse polling is also not defined as one attempt or multiple provider attempts.

**Required correction:** Make attempt identity explicit, for example global run ordinal plus `stage`, `provider_operation`, and `poll_no`, or remove the duplicate run-level counter and define polling semantics.

### PB-03 — Current-run promotion checks different provenance tuples

**Severity:** Critical  
**Location:** `ARCHITECTURE-SPINE.md:151, 187-191, 320-322`

Promotion is described as checking only the current source fingerprint, while the persistence rule requires source fingerprint, criteria version, normalized hash, and artifact mode. Implementation A can promote a same-PDF result under the wrong criteria/mode; Implementation B checks the full tuple.

**Required correction:** Specify the canonical compare-and-set key and require the same exact tuple in the promotion transaction, including run status and source revision where applicable.

### PB-04 — “Artifact set” is not one contract, and calibration rows may have no run

**Severity:** Critical  
**Location:** `ARCHITECTURE-SPINE.md:106-107, 187-191, 318-323, 645-689`

The canonical artifact set omits `source_fingerprint`, `artifact_mode`, and `source_revision`, although other rules require them. Calibration `ReviewLog` and `ConflictItem` rows allow `source_processing_run_id = NULL`, although AD-10 says all downstream records bind to an artifact set containing that run. Implementation A uses a four-field application set and nullable calibration provenance; Implementation B uses the larger tuple.

**Required correction:** Define separate, explicit calibration and official artifact-set contracts, or make the processing run mandatory and include every required provenance field in one canonical identity.

### PB-05 — Citation creation conflicts with the question-generation schema

**Severity:** Critical  
**Location:** `ARCHITECTURE-SPINE.md:128-132, 206-212, 241, 263-269`

The pipeline says the model must not generate citation IDs because the server creates them after exact-match validation, but the question-generation schema requires `citation_ids[]`. No deterministic server rule maps a generated question to already-created citations. Implementation A derives citations from criteria/concern; Implementation B asks the model to return existing IDs.

**Required correction:** Choose a two-phase contract: either generate question text without IDs and deterministically attach server-selected citations, or pass an immutable existing-citation catalog and require validated references. Define failure behavior for zero, multiple, or invalid matches.

### PB-06 — Duplicate exact-substring location resolution is undefined

**Severity:** High  
**Location:** `ARCHITECTURE-SPINE.md:105-107, 212-233`

The extractor returns quote text, block ordinal, and optional page, while the server performs exact matching. The contract does not say what happens when the same quote occurs more than once in the same block/page or when the supplied ordinal/page identifies multiple candidates. Implementation A chooses the first occurrence; Implementation B rejects or stores multiple citations.

**Required correction:** Add an occurrence identifier and deterministic resolution rule, or fail closed with a canonical ambiguity error.

### PB-07 — Calibration “exactly one current review” is not represented by the stated uniqueness rule

**Severity:** High  
**Location:** `ARCHITECTURE-SPINE.md:99, 113-115, 318, 645-664`

The approval gate requires exactly one current HR and TECH review per sample×criterion, but the stated unique key includes `revision_no`, allowing multiple current rows. The document does not require a partial unique index or define the atomic replacement transaction. Concurrent implementations can approve different cardinalities.

**Required correction:** Enforce one current row per `(version, sample, criterion, reviewer role)` at the database and service layers, with explicit supersession and approval-time locking behavior.

### PB-08 — Criteria-item revisions promised by the API have no persistence model

**Severity:** High  
**Location:** `ARCHITECTURE-SPINE.md:188-190, 276-277, 528-533`

Draft item edits are said to create new revisions, but `CRITERIA_ITEM` has no revision number, parent/supersedes link, current flag, or revision table. Implementation A mutates the item; Implementation B inserts a replacement item. Calibration samples and review logs can therefore reference different meanings under the same criteria version.

**Required correction:** Add an item-revision model and explicit current-item selection, or remove the new-revision promise and define immutable item rows for a draft version.

### PB-09 — Handoff conflict snapshots cannot reconstruct the required disagreement

**Severity:** Critical  
**Location:** `ARCHITECTURE-SPINE.md:114-115, 187-191, 293, 459-460, 672-714`; `prd.md:109-115`

`HANDOFF_CONFLICT_SNAPSHOT` stores only a conflict ID, conflict revision, display status, and display reason. It does not snapshot the HR/TECH review IDs, statuses, reasons, citation links, or conflict type. The handoff GET contract says it returns “conflicts” without saying whether these are immutable snapshots or live canonical conflicts. Implementation A rehydrates live rows; Implementation B renders the snapshot.

**Required correction:** Define an immutable snapshot payload containing both reviewer positions and their citations, and make the handoff response explicitly return the snapshot for its source revision.

### PB-10 — Question provenance does not bind to the conflict revision shown on the card

**Severity:** High  
**Location:** `ARCHITECTURE-SPINE.md:128-132, 187-191, 706-743`

Question candidates may reference `conflict_item_id`, but neither the candidate nor `QUESTION_REVISION` records `conflict_revision_no` or a snapshot ID. A later review revision can therefore change the conflict while the question still appears to be grounded in the original handoff.

**Required correction:** Bind the candidate/revision to `handoff_conflict_snapshot_id` or `(conflict_item_id, conflict_revision_no)` and require that binding in generation, display, and verification.

### PB-11 — Question verification stale/current semantics are incomplete

**Severity:** High  
**Location:** `ARCHITECTURE-SPINE.md:158-160, 269, 322, 760-778`

The contract says verification is stale after question editing and that latest state is selected by `revision_no`, but `INTERVIEW_VERIFICATION` has no stale/current field, supersession link, or stated unique key for concurrent writes. Implementation A writes an explicit stale row; Implementation B derives latest by max revision and may still treat old verification as valid.

**Required correction:** Define verification revision uniqueness, current/stale representation, and the transaction that invalidates verification when a question revision changes.

### PB-12 — Decision revision behavior has no API contract

**Severity:** High  
**Location:** `ARCHITECTURE-SPINE.md:159-160, 294-300, 780-799, 322`

`DECISION_RECORD` is append-only with `revision_no` and `is_current`, but the only route is `POST /api/handoff/{handoff_id}/decision`; no request field or route defines revision, supersession, voiding, or concurrent-current handling. Implementation A treats a second POST as a correction; Implementation B rejects it because the official decision is immutable.

**Required correction:** Specify create/revise/void semantics, current-row enforcement, idempotency behavior, and the exact response/error for a stale source revision.

### PB-13 — Handoff-generation authorization is unspecified

**Severity:** High  
**Location:** `ARCHITECTURE-SPINE.md:167-170, 178, 292, 327`; `prd.md:51-53, 69-71`

The handoff-generation route lists provenance prerequisites but no caller role. The role rules explicitly assign LEAD to handoff reading and question selection, but do not state whether HR or TECH may generate the card. Implementation A permits a reviewer to generate; Implementation B permits only LEAD.

**Required correction:** Assign the route to an explicit role/ownership policy and define `401` versus `403` behavior.

### PB-14 — Review revision and ownership routes are underspecified

**Severity:** High  
**Location:** `ARCHITECTURE-SPINE.md:113, 167, 286, 290, 318, 645-664`

Review history is append-only and reviewer-owned, but the API exposes only POST save operations, with no request contract for revision/current/supersedes fields and no update route. “Own review” and “corresponding reviewer” are not mapped to a concrete principal/row rule. Implementation A creates a new revision on POST; Implementation B updates the current row or rejects a duplicate.

**Required correction:** Define review request schemas, revision allocation, ownership predicate, current-row transition, and conflict recomputation transaction.

### PB-15 — Error envelope is called RFC 7807-compatible but is a different shape

**Severity:** High  
**Location:** `ARCHITECTURE-SPINE.md:251-252, 302-314`

The stated envelope is `{success, data, error, correlation_id}`, while RFC 7807 clients expect problem fields such as `type`, `status`, `title`, and `detail`. The matrix also leaves alternatives such as `404/409` and `200/202` without per-route selection rules. Implementation A builds against the custom envelope; Implementation B builds against RFC 7807.

**Required correction:** Choose one normative media type and schema, define exact status/code selection per endpoint, and provide one stable error payload for idempotent replay and provenance failures.

## Deferred items — correctly not phase-blocking this gate

The following remain deferred as explicitly documented and are not reclassified as phase-blockers:

- **D-01:** exact interview-question candidate count.
- **D-02:** presentation dataset quantity and composition.
- **D-03:** PB-02 baseline reproduction contract.
- **D-04:** final evidence and numbers for the problem-definition card.
- **D-05:** repository and deployment links.
- **D-06:** measurement contract for the “within two minutes” supporting metric.
- **D-07:** supported scope of PDF coordinate highlighting; snippet/page/context fallback remains required.

## Gate disposition

**REVISE/FAIL.** Resolve PB-01 through PB-15 in the source contracts before implementation handoff. The D-01..D-07 decisions may remain deferred under their stated decision points.
