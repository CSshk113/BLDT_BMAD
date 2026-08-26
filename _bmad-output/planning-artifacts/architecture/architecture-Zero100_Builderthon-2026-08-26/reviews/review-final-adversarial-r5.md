# Finalization Gate — Adversarial Divergence R5

## Result

**REVISE**

The current three documents are not yet implementation-final. Eight unresolved phase-blockers remain. This review used only:

- `ARCHITECTURE-SPINE.md`
- `PRESENTATION-SYSTEM-DESIGN.md`
- `prd.md`

Prior review files were not used. No source document was edited.

For each item, two independent implementers were tested against the written contract. A blocker is listed only when both implementations are plausible from the current documents and can produce different persisted behavior or gate decisions.

## Unresolved phase-blockers

### 1. Citation creation has no deterministic ambiguity contract

**Evidence:** `ARCHITECTURE-SPINE.md:105-107, 213-234`.

**Divergence:** Implementer A resolves an exact `quote_text` using the first matching substring. Implementer B uses `markdown_block_ordinal`/`page_number` to choose an occurrence, or rejects when multiple occurrences remain. The documents do not define tie-breaking, block/page consistency checks, cross-block quote handling, or the required behavior for an unresolved match.

**Guard required:** Specify one canonical resolver: validate candidate block/page, return exact normalized offsets and hash, and reject ambiguous or inconsistent candidates before creating `EVIDENCE_CITATION`/`VERIFIED` output.

**Why it blocks:** Identical inputs can receive different citation IDs, offsets, locations, and downstream provenance.

### 2. Calibration and application provenance are not one implementable schema

**Evidence:** `ARCHITECTURE-SPINE.md:187-192, 613-697, 319-324`.

**Divergence:** The scope rule permits `CALIBRATION` processing-run/hash fields to be nullable, while the ERD makes `CONFLICT_ITEM.normalized_markdown_hash` non-null and the citation model requires a processing run. Implementer A creates calibration rows without the full artifact tuple; Implementer B applies the application/official tuple constraints to calibration and rejects or misbinds valid calibration records.

**Guard required:** Define scope-specific schemas and constraints explicitly: calibration rows bind to `(criteria_version_id, calibration_sample_id, criteria_item_id, reviewer_role, revision_no)` with only the documented nullable fields; application/official rows require the full artifact tuple and matching `artifact_mode`. Add service-level and database checks for each scope.

**Why it blocks:** Calibration evidence can be rejected, attached to the wrong run, or leak into official provenance depending on implementation.

### 3. Processing retry lifecycle is internally under-specified

**Evidence:** `ARCHITECTURE-SPINE.md:141, 149-152, 285, 576-599`.

**Divergence:** Implementer A retries a failed `PROCESSING_RUN` by transitioning `FAILED → QUEUED`; Implementer B creates a new logical run; Implementer C appends an attempt to the failed run. The stated transition `QUEUED → STARTED → SUCCEEDED|FAILED` defines none of these retry transitions, despite requiring retry from the failed stage and same-logical-run attempts.

**Guard required:** Publish the complete state machine, including expired-heartbeat recovery, failed-stage retry, attempt numbering, logical-run identity, application status derivation, and when a new source revision/run is mandatory.

**Why it blocks:** Retry behavior, current-run promotion, and failure isolation can differ and may either strand retries or promote stale/partial output.

### 4. Calibration sample scope lacks registration/readiness invariants

**Evidence:** `ARCHITECTURE-SPINE.md:99, 279-281, 493-499, 319`.

**Divergence:** Implementer A allows duplicate `(criteria_version_id, application_id)` samples or approves after review rows exist even if the sample application is not a completed preview artifact. Implementer B deduplicates samples and requires a completed preview run for the exact criteria version before approval. Current approval language checks review cardinality and conflicts but does not state these sample identity/readiness constraints.

**Guard required:** Require a unique criteria-version/sample-application association; require the sample application and preview processing result to belong to the same criteria version and be ready before calibration review/approval; freeze the sample set at approval.

**Why it blocks:** Different implementers can approve different calibration populations, undermining the meaning of the approved criteria version.

### 5. Handoff-generation authorization is not resolved

**Evidence:** `ARCHITECTURE-SPINE.md:132, 166-170, 264, 293, 415-418`; `prd.md:51-53, 115`.

**Divergence:** The sequence shows the `TECH` actor initiating `POST /api/handoff/generate`; the API contract does not state the caller role; AD-5 says `LEAD` or a card-creation transaction may call it; AD-12 explicitly grants `LEAD` handoff reading and downstream actions. Implementer A permits TECH after reviews; Implementer B requires LEAD; Implementer C treats generation as an internal transaction only.

**Guard required:** Add an endpoint-level authorization matrix covering handoff creation, read, question generation/edit/delete/select, verification, and decision, including ownership and whether generation is user-initiated or internal.

**Why it blocks:** The demo flow and the server’s authorization behavior can disagree, and a valid handoff may be inaccessible or creatable by the wrong role.

### 6. Question revision does not define grounding/safety invalidation

**Evidence:** `ARCHITECTURE-SPINE.md:129-132, 207-209, 266-270, 757-764`.

**Divergence:** Implementer A patches `question_text`, appends `QUESTION_REVISION`, and retains existing citations/safety status. Implementer B reruns grounding and safety validation, marks the edited revision review-required, invalidates selection/verification, and requires re-selection. The documents require re-selection/re-verification for selected edits but do not require citation revalidation or define revision-level safety/grounding state.

**Guard required:** Make edit one transaction that appends the revision, revalidates exact artifact-set citations and safety, resets the candidate to `CANDIDATE`/review-required as applicable, and stales all prior verification for that revision.

**Why it blocks:** An edited question can retain evidence and approval that no longer support its current text.

### 7. Handoff conflict snapshot membership and payload are not fixed

**Evidence:** `ARCHITECTURE-SPINE.md:114-115, 187-191, 322, 712-720, 341`.

**Divergence:** Implementer A snapshots only `OPEN` conflicts. Implementer B snapshots every current application conflict, including resolved conflicts. The contract says “current conflict” but does not define the membership predicate; the snapshot table stores only a conflict ID/revision and display fields, without an explicit snapshot of the paired review/citation payload or artifact tuple.

**Guard required:** Define whether the snapshot contains all current conflicts or only open conflicts, and atomically persist the complete immutable display payload plus conflict revision and artifact tuple. Reads must use the snapshot, not a later current-conflict query.

**Why it blocks:** Two official cards for identical inputs can show different conflict sets or later-changing conflict detail.

### 8. Decision invalidation/revision after upstream changes is not defined

**Evidence:** `ARCHITECTURE-SPINE.md:159-160, 189-191, 293-296, 323, 786-805`.

**Divergence:** Implementer A permits a prior `ADVANCE/HOLD/REJECT` to remain current after a question revision, new source revision, or reopened conflict. Implementer B voids it and requires a new decision; Implementer C appends a superseding decision only when explicitly requested. `DECISION_RECORD` contains revision/void fields, but no transition or automatic invalidation contract.

**Guard required:** Define the current-decision invariant and all invalidating events; require exact current handoff/source/question revisions and current artifact-set citations, then specify whether the result is voided, superseded, or forced to `UNDECIDED`.

**Why it blocks:** The system can expose a decision whose evidence, questions, or conflict state no longer matches the official handoff.

## Gate conclusion

**REVISE before implementation-phase handoff.** Resolve the eight contracts above in the current architecture/PRD set, then rerun the finalization gate.
