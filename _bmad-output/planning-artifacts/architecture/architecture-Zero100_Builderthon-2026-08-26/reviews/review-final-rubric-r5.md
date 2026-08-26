# Finalization Gate — Rubric Reconciliation r5

**Verdict: REVISE**

## Scope

Reviewed only these current documents:

1. `ARCHITECTURE-SPINE.md`
2. `PRESENTATION-SYSTEM-DESIGN.md`
3. `prd.md`

Prior review files were not consulted. Source documents were not edited.

## Rubric reconciliation

| Check | Result | Evidence |
| --- | --- | --- |
| FR coverage | PASS | Architecture frontmatter binds FR-001 through FR-022, including FR-012a and FR-012b; capability map covers F1/F2/F3. Direct contracts cover calibration, evidence, review, handoff, interview verification, decision, safety, provenance, and failure paths. |
| D-01–D-07 reconciliation | PASS | Architecture Deferred section preserves the same identifiers and boundaries as PRD §13.3. D-07 explicitly defers only coordinate-highlight scope; snippet/page/context fallback remains required. |
| 90-second sequence | PASS | PRD `prd.md:189-195`, architecture `ARCHITECTURE-SPINE.md:332-339`, and presentation `PRESENTATION-SYSTEM-DESIGN.md:125-142` all specify 10+10+25+15+10+20 seconds in the same order. |
| Golden fixture | REVISE | Architecture `ARCHITECTURE-SPINE.md:341` defines the required state, but does not enforce exactly one golden application or define a stable tie-break for `golden_demo=true`. |
| Companion alignment | REVISE | Presentation stack, pipeline, guards, fallback, and 90-second sequence align with the spine. The companion inherits the unresolved demo-entry ambiguity described below. |
| Finalization metadata | REVISE | PRD is `status: final` (`prd.md:1-8`), but the architecture remains `status: draft` (`ARCHITECTURE-SPINE.md:1-10`), and the presentation companion has no finalization metadata block. |

## Unresolved phase-blockers

### B-01 — Finalization metadata is not final across the artifact set

**Evidence:** `ARCHITECTURE-SPINE.md:8` says `status: draft`; `PRESENTATION-SYSTEM-DESIGN.md:1-4` has no status, updated date, source, or gate-result metadata.

**Why it blocks:** The PRD is final, but the architecture set is still explicitly draft and the companion cannot be audited as a finalized companion artifact.

**Closure:** Set the architecture to the agreed final status and add companion finalization metadata recording the reviewed PRD, spine, gate result, and date.

### B-02 — The required demo scope does not reconcile with the 90-second entry state

**Evidence:** PRD `prd.md:187` requires the core demo to show actual input → processing → output. Architecture `ARCHITECTURE-SPINE.md:332` starts the presentation at an already approved `/review` state, and `:341` requires an `OFFICIAL + COMPLETED` pre-seeded golden application. Presentation `PRESENTATION-SYSTEM-DESIGN.md:125-144` follows the same post-processing start.

**Why it blocks:** It is unclear whether input/processing is part of the required demo, a prelude outside the 90-second click slice, or intentionally represented only by pre-seeded data.

**Closure:** Explicitly define the 90-second flow as a post-processing slice with a visible input/processing prelude, or change the golden fixture/storyboard so the required input → processing → output path is shown. All three documents must state the same boundary.

### B-03 — Calibration conflict provenance has contradictory nullability

**Evidence:** Architecture `ARCHITECTURE-SPINE.md:192` says calibration processing-run and normalized-hash provenance may be nullable, while the ERD declares `CONFLICT_ITEM.normalized_markdown_hash` without nullable qualification at `:681-682`.

**Why it blocks:** Independent schema implementation cannot determine whether calibration conflicts may omit normalized provenance.

**Closure:** Make the ERD and persistence constraints explicitly conditional and consistent for `CALIBRATION` versus `APPLICATION` conflict rows.

### B-04 — Golden application selection is not uniquely reproducible

**Evidence:** Architecture `ARCHITECTURE-SPINE.md:341` specifies `golden_demo=true` and calls selection deterministic, but does not require one matching application or specify ordering/tie-breaking.

**Why it blocks:** Multiple seeded rows could produce different 90-second content across runs, undermining the golden fixture contract.

**Closure:** Enforce exactly one golden application per criteria version, or specify and test a stable selection key/order; have seed validation fail on zero or multiple matches.

## Gate decision

**REVISE** until B-01 through B-04 are closed. No other unresolved phase-blockers were found in the requested FR, D-item, 90-second, or companion reconciliation.
