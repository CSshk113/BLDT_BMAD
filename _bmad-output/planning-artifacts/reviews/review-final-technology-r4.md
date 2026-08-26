# Final Technology Gate Review — Zero100_Builderthon

**Verdict: REVISE**

**Review date:** 2026-08-27  
**Review scope:** Current local source documents only. Prior review files were not used.  
**Source documents:**

- `ARCHITECTURE-SPINE.md`
- `PRESENTATION-SYSTEM-DESIGN.md`
- `prd.md`

No source document was edited.

## Gate result

The architecture is substantially synchronized with the PRD and has strong safety, provenance, role, failure-isolation, and MVP-boundary intent. The pins and named API surfaces are specific enough to review. However, four high-severity interoperability contracts remain underspecified or internally unsafe for implementation. They affect the core PDF-to-grounded-evidence path and the Korean PDF demo path, so the gate is **REVISE**.

There are **no Critical findings**.

## Phase-blockers

Only the following unresolved interoperability issues are classified as phase-blockers.

### HIGH / PB-01 — Responses schema passes a model symbol where the API contract requires a JSON Schema object

**Evidence:** `ARCHITECTURE-SPINE.md:139` specifies `text.format` with `schema: GroundedExtraction`, while `ARCHITECTURE-SPINE.md:212-241` separately describes a logical JSON Schema and Pydantic validation.

**Issue:** The source contract does not say whether `GroundedExtraction` is a JSON-serializable schema dictionary or a Pydantic model class. A Pydantic class cannot be sent as the Responses `text.format.schema` value. The implementation must explicitly derive and lock the JSON Schema before the provider call.

**Required resolution:** Define one canonical conversion, for example `GroundedExtraction.model_json_schema()`, and apply the same locked schema artifact to the request, `schema_version`, fixtures, and post-response validation. The contract must also require inspection of the Responses output for refusal, incomplete status, missing message content, and invalid structured text before any mapping is persisted or exposed.

**Consequence if shipped unresolved:** Every mapping request may fail at serialization/provider validation, or different implementations may send materially different schemas and undermine reproducibility.

### HIGH / PB-02 — LlamaParse page-level source and structured item coordinates are conflated

**Evidence:** `ARCHITECTURE-SPINE.md:138` says `parsing.get(expand=["items", "markdown", "job_metadata"])` is used and that `items` page-level Markdown is stored as the original Markdown and `DOCUMENT_PAGE`. The data model at `ARCHITECTURE-SPINE.md:551-569` and `610-628` then relies on page/block offsets and optional BBox coordinates.

**Issue:** The source contract does not define the canonical page text used for normalization and exact substring offsets versus the structured item stream used for location data. It also does not define the page-number basis used between provider output, database records, and the PDF viewer. A page-level text stream and item-level `md` values must not be silently treated as the same byte/code-point sequence.

**Required resolution:** Specify and test the mapping: canonical text comes from the provider's page-level Markdown result; structured page items are joined to that page only for BBox/location resolution; every stored block and citation must retain the provider page identifier and normalized viewer page number. Define the 0/1-based conversion, failed-page behavior, and exact offset coordinate space in the contract and fixtures. The upload call must also explicitly pass the `file_id` returned by `files.create` into `parsing.create`.

**Consequence if shipped unresolved:** Citations can point to the wrong page/block, exact-match validation can reject valid evidence or accept mislocated text, and split-view highlighting can be wrong while appearing trustworthy.

### HIGH / PB-03 — Parser “version lock” is incompatible with the documented `latest` request unless resolved-version capture is defined

**Evidence:** `ARCHITECTURE-SPINE.md:138` requests `version="latest"`, then requires comparison against `LLAMA_PARSE_VERSION_LOCK` and storage of a provider-returned parser version. `ARCHITECTURE-SPINE.md:571-595` includes `parser_requested_version` and `parser_resolved_version`, but no provider response field or extraction rule is defined.

**Issue:** The source does not establish where the resolved parser version comes from, what value `LLAMA_PARSE_VERSION_LOCK` contains, or what happens if the provider returns no resolved version. Requesting `latest` permits parser behavior to change without a new source revision, while an undocumented response field cannot support fail-closed behavior.

**Required resolution:** Either request a dated parser version and record that exact value as the locked parser version, or define the provider response field/metadata extraction and fail closed when it is absent or differs. Add startup validation for a non-empty lock and an acceptance fixture proving that a version mismatch cannot promote an OFFICIAL run.

**Consequence if shipped unresolved:** Reprocessing the same PDF can produce a different normalized source and invalidate the provenance/hash contract without a detectable, reproducible revision boundary.

### HIGH / PB-04 — PDF.js worker and non-Latin asset wiring is not a complete runtime contract

**Evidence:** `ARCHITECTURE-SPINE.md:181` and `:350` require `react-pdf`/`pdfjs-dist` worker setup plus bundled cMaps and standard fonts; `PRESENTATION-SYSTEM-DESIGN.md:144` repeats the requirement. No exact worker import/copy path or `Document` options are specified.

**Issue:** Bundling assets alone does not define how PDF.js locates them in a production Next.js build. The source does not require `cMapUrl`, `cMapPacked`, or `standardFontDataUrl` values, nor does it state that `workerSrc` is configured in the same client module that renders `Document`/`Page`. This is material because Korean PDF rendering is an explicit smoke-test gate.

**Required resolution:** Pin the tested `react-pdf`/`pdfjs-dist` pair as already stated, define the exact client-only worker import or public copy path, define the cMap and standard-font asset paths/options, and require a production-build browser smoke test covering Korean text, worker loading, cMaps, standard fonts, and fallback behavior.

**Consequence if shipped unresolved:** The demo can render blank pages, emit fake-worker/worker-version errors, or fail on Korean glyphs in production even when the local development viewer works.

## High-severity issues that are not separate phase-blockers

None. The high findings above are all unresolved interoperability issues and are therefore the only phase-blockers.

## Technology/version review summary

The following areas are acceptable in intent and do not add separate blockers, subject to the phase-blocker resolutions above:

- **OpenAI Responses surface:** `client.responses.create`, `store=false`, `text.format.type=json_schema`, strict output, fixed `gpt-5.6-luna`, refusal/incomplete rejection, and server-issued citation IDs are coherently specified. The canonical JSON Schema conversion remains required by PB-01.
- **OpenAI SDK pin:** `openai==3.3.1` is explicitly named in the architecture and is paired with Python 3.12.14. The source still needs the actual lockfile and schema fixture to bind the claim during implementation.
- **LlamaCloud SDK pin/calls:** `llama_cloud` 2.14.1, `LlamaCloud`, `files.create(purpose="parse")`, `parsing.create`, and `parsing.get` are explicitly named. The missing `file_id` handoff and page-result distinction are covered by PB-02.
- **Parser versioning:** the intent to record requested/resolved version, tier, polling deadline, and processing attempts is sound; the `latest`/lock contract is not yet implementable as written (PB-03).
- **Page-level response:** page/block provenance, hashes, offsets, page number, and BBox fields are modeled. The canonical provider field and numbering conversion must be made explicit (PB-02).
- **Runtime:** Node.js 24.20.0 LTS, Python 3.12.14, Next.js 16.3.3, React 19.2.4, FastAPI 0.141.1, Pydantic 2.13.4, SQLAlchemy 2.0.52, and `pydantic-settings` 2.15.0 are clearly stated. `package-lock.json` and hash-locked `requirements.lock` are named as deployment inputs, but their contents were outside this source-only gate.
- **Base URLs:** the source correctly keeps keys server-side, requires HTTPS and explicit allowlists, validates paths at readiness, and avoids wildcard CORS. A compatible endpoint should additionally be required to prove the same Responses/LlamaCloud resource and schema contract; this is not a separate blocker for the constrained MVP.
- **Security:** server-derived session actor/role, HttpOnly/Secure/SameSite cookie, MIME/magic-byte validation, non-public file root, path isolation, redacted provider audit records, no secrets in logs, and synthetic/de-identified demo PDFs are appropriately bounded.
- **Operational boundary:** the single DB-backed worker, SQLite WAL/busy-timeout, CAS ownership, heartbeat recovery, bounded retry policy, 90-second LlamaCloud polling deadline, 60-second OpenAI timeout, failure isolation, and explicit deferral of multi-tenant/SSO/ATS/production retention/large-scale queueing are coherent for a five-day demo.

## Deferred items

D-01 through D-07 are correctly treated as deferred decisions where they do not change the interoperability contracts above:

- **D-01:** exact interview-question candidate count.
- **D-02:** demo dataset quantity and composition.
- **D-03:** baseline reproduction contract.
- **D-04:** final problem-definition evidence.
- **D-05:** repository and deployment links.
- **D-06:** supplementary two-minute metric measurement.
- **D-07:** supported scope of PDF coordinate highlighting.

D-07 does not defer the required PDF worker, cMap, standard-font, or text-rendering contract; only the supported BBox coverage may remain deferred.

## Exit criteria for PASS

Change the verdict to PASS after the source contracts explicitly:

1. bind a JSON-serializable, strict Responses schema artifact;
2. bind LlamaParse upload `file_id`, canonical page Markdown, structured-item/BBox mapping, and page numbering;
3. bind parser version locking to a dated request or a documented resolved-version field; and
4. bind exact production PDF.js worker/cMap/standard-font wiring with a Korean browser smoke test.

