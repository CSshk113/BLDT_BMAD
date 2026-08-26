# Final Technology Review R3 — Zero100_Builderthon

**Decision: REVISE**

This is a fresh finalization-gate review of the current contents only. No source artifact was edited, and prior review files were not used as evidence.

## Scope

Inspected:

- `C:\Users\kimsu\BLDT_BMAD\_bmad-output\planning-artifacts\architecture\architecture-Zero100_Builderthon-2026-08-26\ARCHITECTURE-SPINE.md`
- `C:\Users\kimsu\BLDT_BMAD\_bmad-output\planning-artifacts\architecture\architecture-Zero100_Builderthon-2026-08-26\PRESENTATION-SYSTEM-DESIGN.md`
- `C:\Users\kimsu\BLDT_BMAD\_bmad-output\planning-artifacts\prds\prd-Zero100_Builderthon-2026-08-25\prd.md`

Review focus: current package/runtime versions, OpenAI and LlamaCloud SDK/API contracts, PDF worker wiring, provider configuration, security boundaries, and demo operations.

## Gate summary

- Critical findings: **1**
- High findings: **9**
- Phase blockers: **5 definite**, plus 1 conditional provider-config blocker
- Deferred findings: **4**
- Overall: **REVISE before implementation/finalization approval**

The system design is coherent and the major human-control, provenance, and failure-isolation invariants are present. The result is not PASS because the OpenAI structured-output request is invalid as specified, page-level LlamaParse provenance is not guaranteed by the requested response expansion, the declared retry budget is not the runtime retry budget, and the PDF worker contract is not sufficiently executable for the required Korean browser smoke test.

## Critical/high findings

### F-01 — CRITICAL — OpenAI Structured Outputs request is missing the required schema name

- **Location:** `ARCHITECTURE-SPINE.md:138`, AD-6 rule 2.
- **Classification:** **Phase blocker — F2 grounded extraction.**
- **Trigger:** `text.format` is specified with `type`, `strict`, and `schema`, but no `name`.
- **Evidence:** The official OpenAI Python Responses type requires `name`, `schema`, and `type`; the official Structured Outputs examples also include a named format.
- **Required correction:** Define an executable request contract, for example `text={"format":{"type":"json_schema","name":"grounded_extraction","strict":true,"schema":...}}`, and test the exact serialized request against the pinned SDK.
- **Consequence:** The provider request can be rejected before extraction, causing every mapping run to fail.
- **Official sources:** [OpenAI Responses JSON-schema type](https://github.com/openai/openai-python/blob/main/src/openai/types/responses/response_format_text_json_schema_config.py), [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

### F-02 — HIGH — The strict GroundedExtraction schema is not defined to the provider’s strict-schema rules

- **Location:** `ARCHITECTURE-SPINE.md:138` and `198-204`; `PRESENTATION-SYSTEM-DESIGN.md:53-54`.
- **Classification:** **Phase blocker — F2/F3 extraction and question generation.**
- **Trigger:** The documents name `GroundedExtraction` and a question schema but do not define the complete JSON Schema, required arrays/fields, `additionalProperties`, nullability, or the exact schema name/version.
- **Evidence:** OpenAI’s strict Structured Outputs contract requires all fields to be required and uses `additionalProperties: false`; optional semantics must be represented explicitly with `null` unions.
- **Required correction:** Add versioned executable schemas for `GroundedExtraction` and question generation, including `name`, `required`, `additionalProperties: false`, enum values, nullability, array item schemas, and a schema-validation test fixture.
- **Consequence:** A Pydantic model may serialize to a schema the API rejects, or missing/optional values may be silently mishandled.
- **Official source:** [OpenAI Structured Outputs limitations and examples](https://developers.openai.com/api/docs/guides/structured-outputs).

### F-03 — HIGH — The declared OpenAI retry budget conflicts with the pinned SDK defaults

- **Location:** `ARCHITECTURE-SPINE.md:150`, AD-7 rule 5.
- **Classification:** **Phase blocker — AD-7 runtime audit/idempotency contract.**
- **Trigger:** The application worker is limited to one retry, but only the LlamaCloud client is explicitly configured with `max_retries=0`; OpenAI Python retries certain failures twice by default.
- **Evidence:** The official OpenAI Python SDK documents default retries of 2 for connection errors, 408, 409, 429, and 5xx responses, and supports `max_retries=0` to disable them.
- **Required correction:** Explicitly construct the OpenAI client with `max_retries=0` (or define and test an equivalent per-request policy), then let the application worker own the single retry and log every attempt.
- **Consequence:** A nominal one-retry job can make up to three SDK attempts per worker attempt, breaking attempt counts, timeout expectations, cost bounds, and provider-call audit records.
- **Official source:** [OpenAI Python SDK retries and timeouts](https://github.com/openai/openai-python#retries).

### F-04 — HIGH — LlamaParse response expansion does not guarantee the page-level data the design stores

- **Location:** `ARCHITECTURE-SPINE.md:106-107`, `137`, `146`; `PRESENTATION-SYSTEM-DESIGN.md:49-58`.
- **Classification:** **Phase blocker — F2 provenance/location contract.**
- **Trigger:** The pipeline requests `parsing.get(expand=["markdown"])` but stores page Markdown, page records, block ordinals, and page/location provenance.
- **Evidence:** The official SDK documents `markdown` as Markdown output and `items` as structured page-by-page output; the one-shot `parsing.parse()` example requests `expand=["text", "markdown"]`, while page-level output is separately represented by `items`.
- **Required correction:** Request and persist the page-level expansion needed for the model, at minimum `items` (and `job_metadata` where parser/version metadata is required), or specify and test a deterministic page-boundary reconstruction algorithm. Record the exact provider payload shape in the contract.
- **Consequence:** The implementation may have one merged Markdown string without reliable page/block boundaries, so `DOCUMENT_PAGE`, citation offsets, and PDF fallback cannot be guaranteed.
- **Official source:** [LlamaCloud Python SDK parsing resource](https://github.com/run-llama/llama-parse-py/blob/main/src/llama_cloud/resources/parsing.py).

### F-05 — HIGH — The PDF worker contract is incomplete for the required React-PDF/Next.js smoke test

- **Location:** `ARCHITECTURE-SPINE.md:175-180`, `312`; `PRESENTATION-SYSTEM-DESIGN.md:28-30`, `140`.
- **Classification:** **Phase blocker — presentation/demo readiness.**
- **Trigger:** The design promises client-only rendering, a bundled worker, cMaps, standard fonts, and Korean PDF coverage but does not specify the exact worker import/URL, same-module placement, or runtime asset URLs/options.
- **Evidence:** React-PDF’s official integration guidance requires `pdfjs.GlobalWorkerOptions.workerSrc` to be set in the same module that renders `Document`/`Page`, recommends the `pdfjs-dist/build/pdf.worker.min.mjs` import, and shows explicit `cMapUrl`, `standardFontDataUrl`, and `wasmUrl` options. PDF.js requires the API and worker versions to match exactly. React-PDF 10.5.0 pins `pdfjs-dist` 5.4.296, so the dependency alignment is available but must be wired explicitly.
- **Required correction:** Specify the exact client component and worker import, the copied/served asset paths, `Document` options for cMaps/standard fonts/WASM, the SSR boundary, and a browser test that asserts no fake-worker warning, no version mismatch, and successful Korean text-layer rendering.
- **Consequence:** The viewer can fall back to a fake worker, fail to load the worker, show API/worker mismatch errors, or render Korean text incorrectly in the demo.
- **Official sources:** [React-PDF worker setup](https://github.com/wojtekmaj/react-pdf#configure-pdfjs-worker), [React-PDF 10.5.0 dependency pin](https://github.com/wojtekmaj/react-pdf/blob/main/packages/react-pdf/package.json), [PDF.js worker-version requirement](https://github.com/mozilla/pdf.js/wiki/Frequently-Asked-Questions#faq-worker).

### F-06 — HIGH — `version="latest"` weakens the claimed LlamaParse reproducibility contract

- **Location:** `ARCHITECTURE-SPINE.md:137`, `146-150`; `PRESENTATION-SYSTEM-DESIGN.md:49-56`; `prd.md:149`, `219`, `270`.
- **Classification:** **Deferred — PB-02/reprocessing reproducibility; not a local MVP blocker if returned parser version is persisted.**
- **Trigger:** Every parse requests the moving `latest` tier version while the documents claim reproducible source processing and baseline snapshot control.
- **Evidence:** The official LlamaCloud SDK supports dated tier versions and exposes the currently accepted version list; the current official type documentation identifies a dated current `agentic` version rather than making `latest` a stable immutable identifier.
- **Required correction:** Pin a dated parser version for reproducible runs, or explicitly define `latest` as an ingestion-time resolver whose returned version is mandatory, retained, and replayable for the life of the artifact set.
- **Consequence:** Reprocessing the same PDF can produce different normalized Markdown, hashes, offsets, citations, and downstream mappings.
- **Official source:** [LlamaCloud parsing version and retrieval contract](https://github.com/run-llama/llama-parse-py/blob/main/src/llama_cloud/resources/parsing.py).

### F-07 — HIGH — The runtime table mislabels Node.js 24.20.0 as LTS

- **Location:** `ARCHITECTURE-SPINE.md:322`.
- **Classification:** **Deferred — documentation/runtime lifecycle correction; not a functional phase blocker.**
- **Trigger:** The stack says `Node.js 24.20.0 LTS`.
- **Evidence:** Node’s official archive confirms 24.20.0 exists, but the same official page identifies Node 26.8.0 as the latest LTS and Node 24.x as Current. Next.js 16 requires Node 20.9+, so 24.20.0 satisfies the minimum but is not LTS under the current release status.
- **Required correction:** Change the lifecycle label to `Node.js 24.20.0 Current` or move to the explicitly selected LTS line, and record the container/image digest or lifecycle policy used by CI and deployment.
- **Consequence:** Operators may assume an incorrect support/security lifecycle and select inconsistent CI or deployment images.
- **Official sources:** [Node.js v24.20.0 archive/status](https://nodejs.org/en/download/archive/v24.20.0), [Next.js 16 system requirements](https://nextjs.org/docs/app/getting-started/installation).

### F-08 — HIGH — Provider base URL configuration does not define the required API path contract

- **Location:** `ARCHITECTURE-SPINE.md:139`, `164`, `167`, `319-320`; `PRESENTATION-SYSTEM-DESIGN.md:140`.
- **Classification:** **Conditional phase blocker — required if a non-default provider endpoint is used; otherwise deferred.**
- **Trigger:** The documents allow `OPENAI_BASE_URL` and `LLAMA_CLOUD_BASE_URL` but validate only HTTPS and host allowlists; they do not define whether the configured value includes `/v1` or `/api/v2` and do not require a normalized final endpoint.
- **Evidence:** The official OpenAI Python client defaults to `https://api.openai.com/v1` and joins resource paths from the configured base URL; the LlamaCloud SDK exposes its own base URL and resource paths. A host-only custom base URL can therefore resolve to the wrong resource path.
- **Required correction:** Define the accepted canonical values, normalize/reject empty values at startup, validate the final URL path per provider, and add readiness plus mocked-request tests for default and compatible endpoints.
- **Consequence:** A deployment can pass host/HTTPS validation yet return 404s or route requests to the wrong provider API surface.
- **Official sources:** [OpenAI Python client base URL behavior](https://github.com/openai/openai-python/blob/main/src/openai/_client.py), [LlamaCloud SDK base URL configuration](https://github.com/run-llama/llama-parse-py#configuring-the-http-client).

### F-09 — HIGH — Public demo authentication permits role impersonation by design

- **Location:** `ARCHITECTURE-SPINE.md:175-178`, `234-261`; `prd.md:151`, `228`, `284`.
- **Classification:** **Deferred — public-demo security boundary; not a local synthetic-fixture blocker.**
- **Trigger:** Anyone who can reach `POST /api/session/demo` can request an allowlisted principal such as `demo_lead`, receive a valid signed cookie, and perform that role’s allowed actions.
- **Required correction:** Before exposing a public deployment, restrict demo access at the deployment boundary or issue one-time/short-lived role-scoped launch tokens; keep synthetic/de-identified data and make the public-demo threat model explicit.
- **Consequence:** An unauthenticated visitor can impersonate HR/TECH/LEAD, alter demo review state, select questions, or record decisions.
- **Current mitigation acknowledged:** Signed HttpOnly/Secure/SameSite cookie validation and server-side role derivation are good controls against client-side role toggles, but they do not authenticate the person requesting a public demo principal.

### F-10 — HIGH — Demo operations lack global abuse and resource-cost controls

- **Location:** `ARCHITECTURE-SPINE.md:150`, `177-178`, `319-322`, `744-756`; `prd.md:146`, `151`, `153`.
- **Classification:** **Deferred — public/extended operations; not a five-day local demo blocker.**
- **Trigger:** The design limits each PDF to 10 MB/30 pages and one concurrent run per application, but does not define global queue depth, upload rate limits, disk quota, provider-call budget, shutdown/cancellation behavior, or cleanup/backup policy.
- **Required correction:** Add explicit demo limits and operational behavior: per-principal/IP rate limits, maximum queued runs, disk quota, provider spend/call budget, orphaned-job cancellation/recovery, and a reset/cleanup procedure. Keep production retention and multi-tenant policy separate if intentionally deferred.
- **Consequence:** A public or repeated demo can exhaust local disk, starve the single worker, or create unbounded external parser/model cost.

## Verified technology baseline

The following current-content claims were verified as real package/model/runtime references as of 2026-08-27. “Verified” means the pin exists and the cited upstream contract supports the described integration; it does not replace lockfile/build verification.

| Area | Current document claim | Review result |
| :--- | :--- | :--- |
| Next.js | 16.3.3 | Exists and is the current npm `latest` in the checked source; Next.js 16 requires Node 20.9+. |
| React | 19.2.4 | Exists and is compatible with React-PDF’s React 19 peer range, but npm currently shows 19.2.8 as `latest`; retain 19.2.4 only as an intentional lockfile pin. |
| React-PDF / PDF.js | 10.5.0 / 5.4.296 | Verified; React-PDF 10.5.0 pins PDF.js 5.4.296 exactly. Worker wiring still requires F-05. |
| FastAPI | 0.141.1 | Verified on PyPI; supports Python 3.12. |
| Pydantic | 2.13.4 | Verified on PyPI. |
| OpenAI Python SDK | 3.3.1 | Verified on PyPI; Responses API and `text.format` are supported. F-01–F-03 remain. |
| OpenAI model | `gpt-5.6-luna` | Verified in the official model catalog; Responses and Structured Outputs are supported. |
| LlamaCloud SDK | 2.14.1 | Verified on PyPI; `LlamaCloud`, `files.create`, `parsing.create`, `parsing.get`, `expand`, and retry configuration are supported. F-04/F-06 remain. |
| pydantic-settings | 2.15.0 | Verified on PyPI. |
| SQLAlchemy | 2.0.52 | Verified on PyPI. |
| Python | 3.12.14 | Verified as the current 3.12 security release; Python 3.14.7 is the latest feature release, so 3.12 is acceptable as an intentional compatibility pin. |
| Node.js | 24.20.0 | Version exists and satisfies Next.js, but the lifecycle label is wrong; see F-07. |

Official package/runtime sources: [Next npm package](https://www.npmjs.com/package/next?activeTab=versions), [React npm package](https://www.npmjs.com/package/react?activeTab=versions), [React-PDF npm package](https://www.npmjs.com/package/react-pdf), [FastAPI PyPI](https://pypi.org/project/fastapi/), [Pydantic PyPI](https://pypi.org/project/pydantic/), [OpenAI PyPI](https://pypi.org/project/openai/), [LlamaCloud PyPI](https://pypi.org/project/llama-cloud/), [pydantic-settings PyPI](https://pypi.org/project/pydantic-settings/), [SQLAlchemy PyPI](https://pypi.org/project/SQLAlchemy/), [Python 3.12.14](https://www.python.org/downloads/release/python-31214/).

## Phase-gate disposition

### Must resolve before implementation/finalization approval

1. F-01 — make the OpenAI Responses JSON-schema request valid.
2. F-02 — freeze executable strict schemas and validation fixtures.
3. F-03 — make application retry counts equal actual provider-call counts.
4. F-04 — guarantee page-level LlamaParse data for the provenance model.
5. F-05 — make PDF worker, cMaps, fonts, WASM, and Korean smoke-test wiring executable.

F-08 is also a blocker if compatible/custom provider base URLs are part of the accepted runtime contract; otherwise narrow the MVP contract to validated default endpoints and defer compatibility.

### Safe to defer only with the stated boundary preserved

- F-06 to PB-02/reprocessing reproducibility, provided parser version returned by `latest` is persisted and replay policy is documented.
- F-07 as a runtime lifecycle/documentation correction.
- F-09 until a public deployment link is exposed; synthetic/de-identified data remains mandatory.
- F-10 until public or repeated operation; local demo limits must still be enforced.

## Final gate statement

**REVISE.** The current artifacts should not be accepted as final technology-ready contracts yet. The findings are concrete and repairable; after F-01 through F-05 are resolved and F-08 is either resolved or explicitly narrowed, the technology gate can be re-run for PASS.
