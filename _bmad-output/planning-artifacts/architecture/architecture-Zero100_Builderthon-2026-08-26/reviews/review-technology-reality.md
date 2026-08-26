# Technology Reality Review

**Artifact reviewed:** `ARCHITECTURE-SPINE.md`  
**Review lens:** Configured technology/reality-check lens  
**Review date:** 2026-08-27  
**Scope:** Current technology/version validity, implementation fit, provider/API contracts, and environment/integration assumptions. The architecture spine was not modified.

## Verdict

**CONDITIONAL — not ready for implementation handoff without a short technology-lock and integration-hardening pass.**

The selected product shape and most of the broad technologies are suitable for a five-day local/demo build. `gpt-5.6-luna` exists and supports structured outputs; FastAPI, Pydantic v2, SQLAlchemy 2.0, and SQLite are all viable foundations. However, the spine currently commits to stale or non-reproducible versions and leaves several cross-system contracts implicit. The highest-risk items are the archived `react-pdf-viewer` stack, the ambiguous/legacy LlamaParse SDK and environment names, missing exact model/parser versions, missing secret protection in the repository, and unspecified job execution/database/browser integration behavior.

No implementation package manifests, lockfiles, backend/frontend source, or root `.gitignore` were present to validate the proposed stack against an existing build. The review therefore checks the spine, its PRD/addendum and companion design, and current primary documentation as of the review date.

## Findings

### 1. High — The committed PDF viewer stack is stale, archived, and has a licensing decision attached

**Spine evidence:** lines 181–182 specify `@react-pdf-viewer/core` with PDF.js `3.11.x`; lines 164–168 require PDF jump/highlight and bbox-aware focus.

The `react-pdf-viewer` repository is archived, and its latest package line is 3.12.0. PDF.js itself is now on the 6.x line. More importantly, the viewer and worker/runtime PDF.js versions must match exactly; independently upgrading PDF.js while retaining this viewer is not a safe fix. The viewer's license page also needs explicit confirmation for the intended hackathon/demo use.

This is a direct fit risk because the product's evidence-citation experience depends on reliable page navigation and highlighting. A PDF viewer can render a page without automatically providing the coordinate mapping needed to overlay LlamaParse-derived locations.

**Required action:** Decide whether to accept the archived viewer as a deliberately frozen demo dependency or replace it with an actively maintained option such as `react-pdf`/direct PDF.js after testing the required page jump, text selection, and custom overlay behavior. Pin the viewer and worker-compatible PDF.js versions as one tested pair, document the license decision, and define the overlay coordinate contract (page dimensions, units, origin, scaling, and rotation).

**Sources:** [react-pdf-viewer organization/repository](https://github.com/react-pdf-viewer), [react-pdf-viewer core package](https://raw.githubusercontent.com/react-pdf-viewer/react-pdf-viewer/master/packages/core/package.json), [react-pdf-viewer basic usage](https://react-pdf-viewer.dev/docs/basic-usage/), [PDF.js getting started](https://mozilla.github.io/pdf.js/getting_started/?lang=en), [react-pdf package](https://github.com/wojtekmaj/react-pdf/blob/main/packages/react-pdf/package.json).

### 2. High — LlamaParse is not committed as a reproducible current integration

**Spine evidence:** lines 64, 133–135, 181–182, and 359–360 describe “LlamaParse API,” `LLAMAPARSE_API_KEY`, `LLAMAPARSE_BASE_URL`, and account-configured behavior, but do not specify the client package, tier, parser version, or markdown expansion mode.

The current official Python flow is centered on the `llama_cloud` client and `LLAMA_CLOUD_API_KEY`/`LLAMA_CLOUD_BASE_URL`. Current parsing requires an explicit tier and version; markdown is requested through `expand=["markdown"]`, and the fast tier does not provide markdown. The spine's variable names may be intentional application aliases for a legacy SDK, but that is not stated and cannot be implemented reproducibly from the document.

The PRD correctly says the exact API snapshot should be verified before use, but that gate has not been carried through into the spine's committed stack or `ProcessingRun` contract. Account-configured defaults also make two otherwise identical environments parse differently.

**Required action:** Commit the exact SDK/package, API version, tier, parser version, and requested output mode. Prefer a dated/versioned production parser rather than an unbounded `latest` alias; if `latest` is deliberately used, record the resolved version in each processing run. Rename the variables to the official current names or explicitly document a compatibility adapter and its mapping. Record parser configuration and provider request identifiers alongside the existing run metadata.

**Sources:** [LlamaParse parse documentation](https://developers.llamaindex.ai/llamaparse/parse/), [official llama-parse Python SDK README](https://github.com/run-llama/llama-parse-py), [current typed parsing parameters](https://github.com/run-llama/llama-parse-py/blob/main/src/llama_cloud/types/parsing_create_params.py), [Llama Cloud releases](https://github.com/run-llama/llama_cloud_services/releases).

### 3. High — Markdown citation data is not enough to guarantee bbox highlighting

**Spine evidence:** AD-2 lines 106–111 and AD-4 lines 113–118 require `page_number`, `markdown_block_id`, snippet, optional location, and optional bbox, with a fallback when exact location fails.

The current parser documentation establishes page-level markdown output, but the spine does not identify a guaranteed source for word/block bounding boxes. A markdown normalizer can preserve page and block identity, but it cannot invent reliable PDF coordinates. Depending on the selected parser tier/output, spatial text may be available separately from markdown, and the coordinate system may differ from the PDF viewer's coordinate system.

The fallback is a sound product safeguard, but the primary path is underspecified for scanned PDFs, multi-column documents, tables, rotation, and parser normalization that changes whitespace. Exact substring verification alone does not establish that a bbox is correct.

**Required action:** Define the authoritative location source and a normalized citation schema containing page index, PDF page width/height, coordinate units, origin, rotation, and confidence. Store both the exact source snippet and the normalized text used for verification. Add fixtures for text PDFs, scanned PDFs, multi-column layouts, tables, and no-bbox results; make page/snippet focus the accepted fallback.

### 4. High — Next.js, FastAPI, and Pydantic versions are behind current lines and are not pinned

**Spine evidence:** lines 176–180 specify Next.js App Router `15.x`, React `19`, FastAPI `0.115.x`, and Pydantic `v2.10.x`; line 182 says Tailwind and shadcn/ui “Latest.”

Current official documentation places Next.js on the 16.x line, with 15.5.x in maintenance LTS. React is currently on the 19.2 line. FastAPI current release notes show 0.141.1, and Pydantic current releases show 2.13.4. The chosen older lines may still be usable for a short build, but the spine presents them as current technology without an intentional compatibility rationale. `Latest` is especially non-reproducible.

The issue is not that every dependency must be upgraded immediately; it is that the architecture cannot be recreated or meaningfully tested from these ranges. The spine also omits the Node.js and Python runtime versions. Current Next.js 16 requires Node.js 20.9 or newer, while current FastAPI requires Python 3.10 or newer.

**Required action:** Choose a tested release set and pin exact versions (including Tailwind/shadcn package snapshots where relevant) in lockfiles. State the supported Node.js and Python versions. If retaining Next 15/FastAPI 0.115/Pydantic 2.10 for hackathon stability, record that as a deliberate compatibility lock and run a clean-install smoke test. Add `pydantic-settings` explicitly for environment-backed settings.

**Sources:** [Next.js 16 release](https://nextjs.org/blog/next-16), [Next.js blog/current release line](https://nextjs.org/blog), [React versions](https://react.dev/versions), [FastAPI release notes](https://fastapi.tiangolo.com/pt/release-notes/), [FastAPI current package metadata](https://raw.githubusercontent.com/fastapi/fastapi/master/pyproject.toml), [Pydantic releases](https://github.com/pydantic/pydantic/releases), [FastAPI settings](https://fastapi.tiangolo.com/advanced/settings/).

### 5. High — `gpt-5.6-luna` is real and broadly fit, but the API/output contract is underspecified

**Spine evidence:** lines 65, 133–135, and 185–186 commit `gpt-5.6-luna`, a fixed MVP model, “structured JSON mode,” and a server-side OpenAI API key/base URL. The PRD says the exact snapshot still needs an availability check.

The model exists in the current OpenAI catalog, supports structured outputs, and is positioned for cost-sensitive workloads, so the technology choice is plausible for the extraction stage. The risk is reproducibility and correctness: the alias is not an immutable snapshot, “structured JSON mode” is ambiguous, and the spine does not state the Responses vs Chat Completions API, strict schema, reasoning effort, refusal/incomplete handling, or maximum input/output assumptions.

Because this model produces recruitment evidence and criteria mappings, a low-cost choice should still be validated against representative documents. The base URL is also a meaningful integration switch: a non-OpenAI-compatible endpoint cannot be assumed to implement the same model or structured-output contract.

**Required action:** Use the current Structured Outputs JSON Schema contract, preferably through the Responses API, with `strict` schema validation and explicit handling for refusal, truncation, timeout, and schema failure. Pin or record the exact model snapshot when available, record reasoning effort and API mode in `ProcessingRun`, and prohibit silent model fallback. Add an extraction acceptance set and a cost/latency budget before treating the model choice as final.

**Sources:** [GPT-5.6 Luna model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-luna), [OpenAI model catalog](https://developers.openai.com/api/docs/models), [latest-model guidance](https://developers.openai.com/api/docs/guides/latest-model), [Responses API reference](https://developers.openai.com/api/reference/cli/resources/beta/subresources/responses), [official OpenAI Python client environment settings](https://github.com/openai/openai-python/blob/main/src/openai/_client.py).

### 6. High — Secret hygiene is asserted but not mechanically protected by the repository

**Spine evidence:** AD-6.3 lines 131–134 says provider keys must stay server-side and out of the browser/repository; the hypothetical source tree lines 359–360 includes `backend/.env.example`.

The rule is directionally correct, and current Next.js guidance confirms that only `NEXT_PUBLIC_` values are exposed to the client bundle. However, no root `.gitignore` is present in the project. Therefore, the stated “never commit” invariant is not enforced for a future `backend/.env` or other root-level environment file. There are also no committed examples for the frontend API URL, CORS origins, timeout/retry defaults, or settings validation.

**Required action:** Add a repository-level ignore policy for `.env`, `.env.*`, secrets, local databases, uploaded PDFs, and parser artifacts while explicitly allowing `.env.example`. Add a secret scan/pre-commit or CI check. Load provider clients only from backend/server modules, validate required settings at startup, and document which values are safe public build-time variables. Do not put provider keys in `NEXT_PUBLIC_*` variables.

**Source:** [Next.js server/client environment guidance](https://nextjs.org/docs/app/getting-started/server-and-client-components), [Next.js environment variables guide](https://nextjs.org/docs/pages/guides/environment-variables), [Next.js production checklist](https://nextjs.org/docs/app/guides/production-checklist).

### 7. High — SQLite is fit for the demo, but the FK and concurrency invariants are missing

**Spine evidence:** lines 69–71 and 189 select SQLite with SQLAlchemy 2.0 and SQLite `3.45+`; the ERD relies on relationships and foreign keys throughout lines 248–350; async execution and retries are described in lines 228–239.

SQLite and SQLAlchemy 2.0 are reasonable for a single-machine, low-concurrency five-day demo. Current SQLite is 3.53.4 and current SQLAlchemy 2.0 is 2.0.52, so the floor is not a reproducible version commitment. More importantly, SQLite foreign-key enforcement is disabled by default and must be enabled on every connection. The spine's data integrity depends on FK behavior but never commits that connection invariant.

SQLite permits only one writer at a time. WAL can improve reader/writer interaction but does not create multi-writer scalability, and it is unsuitable for a network filesystem. The design also leaves “SQLAlchemy 2.0 (or SQLModel)” unresolved, and does not specify sync/async sessions or migration tooling.

**Required action:** Select SQLAlchemy 2.0 or SQLModel, not “or,” and pin it with the compatible Pydantic/driver set. Add a SQLAlchemy connection hook that enables `PRAGMA foreign_keys=ON` for every connection; define journal mode, busy timeout, transaction boundaries, and migration/bootstrap behavior. Keep the database and file store on local storage for the demo and include WAL sidecar handling in backup/cleanup rules. Treat SQLite as a demo/local deployment boundary, not a production multi-worker claim.

**Sources:** [SQLite release history](https://sqlite.org/changes.html), [SQLAlchemy 2.0 changelog](https://docs.sqlalchemy.org/en/20/changelog/changelog_20.html), [SQLite foreign-key support](https://www.sqlite.org/foreignkeys.html), [SQLite WAL](https://www2.sqlite.org/wal.html), [SQLAlchemy SQLite guidance](https://docs.sqlalchemy.org/en/13/dialects/sqlite.html).

### 8. High — The synchronous sequence conflicts with the deferred async-job decision

**Spine evidence:** lines 193–246 show API-triggered processing, parser polling, LLM extraction, persistence, and status updates in one sequence; deferred decisions lines 391–397 explicitly defer Celery/Redis.

The spine calls this “async pipeline control,” but no execution mechanism is committed. Holding an HTTP request open while LlamaParse uploads/polls and OpenAI retries is fragile. A FastAPI in-process background task can be adequate for a demo, but process restart loses in-flight work unless a recovery scan resumes `RECEIVED`, `PARSING`, or `MAPPING` runs. The current Llama SDK also performs its own polling/retry behavior, so an unbounded application retry layer can duplicate work and amplify latency/cost.

**Required action:** Define the MVP as an accepted-job endpoint plus status polling/SSE, with a durable processing-run state machine. Select an in-process worker/background mechanism for the demo and add startup recovery for non-terminal runs. Set one clear owner for retries, use bounded per-stage deadlines, deduplicate by `processing_run_id`/provider request where supported, and make stage completion idempotent. Specify whether database access is sync/threadpooled or async and test cancellation/restart behavior.

**Sources:** [LlamaParse SDK retry/timeout behavior](https://github.com/run-llama/llama-parse-py), [FastAPI background tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/).

### 9. High — Browser-to-FastAPI integration lacks the API-base and CORS contract

**Spine evidence:** lines 76–77 show frontend HTTP/JSON to API; lines 74–85 define server configuration but no frontend API base URL, origin list, proxy, or credentials policy.

This is an implementation blocker for a separate Next.js frontend and FastAPI backend. The spine must choose either a same-origin Next.js proxy or a browser-visible API base URL. If the browser calls FastAPI directly, the backend needs explicit CORS origins, methods, headers, and credential behavior. A provider base URL is not the frontend API base URL and must not be reused for it.

**Required action:** Commit the topology: same-origin proxy or direct browser-to-API. For direct calls, add a non-secret `NEXT_PUBLIC_API_BASE_URL` (or equivalent build/runtime strategy), an explicit `CORS_ORIGINS` setting, and a credentials policy. For a proxy, define the route and server-only forwarding behavior. Add a clean-browser smoke test covering upload, status polling, error envelope, and citation focus.

**Source:** [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/), [Next.js environment variables](https://nextjs.org/docs/pages/guides/environment-variables).

### 10. Medium — The stated RFC 7807 error contract is not actually RFC-compatible

**Spine evidence:** lines 153–155 say errors are “standard RFC 7807 compatible,” while the example contains only `{code, message}`.

RFC 7807 has been obsoleted by RFC 9457. The standard problem-details members include fields such as `type`, `title`, `status`, `detail`, and `instance`, and the response media type is `application/problem+json`. The current example may be a useful application envelope, but it is not enough to claim RFC compatibility. This matters because the frontend and API need a stable distinction between validation, authorization, provider, retryable, and terminal pipeline errors.

**Required action:** Either adopt RFC 9457 problem details and place application `code`/metadata in extensions, or rename the contract as a project-specific error envelope and document it precisely. Make the envelope consistent with the success wrapper and map 403/422/provider/timeouts to stable client behavior.

**Sources:** [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457.html), [RFC 9457 information page](https://www.rfc-editor.org/info/rfc9457/), [RFC 7807](https://www.rfc-editor.org/rfc/rfc7807.html).

## Confirmed-fit decisions

- The single-application, local-file, SQLite scope is appropriate for a constrained demo if concurrency and restart boundaries are explicit.
- FastAPI plus Pydantic v2 is a fit for typed API contracts and settings, provided `pydantic-settings` and exact versions are committed.
- `gpt-5.6-luna` is a current, available model with structured-output support and a cost-sensitive positioning that matches the MVP; its extraction quality and immutable version still need acceptance evidence.
- The spine's failed states, retry intent, preservation of original/raw/normalized artifacts, exact-substring verification, and no-promotion-of-partial-mappings rules are good reliability foundations.
- The page/snippet fallback is necessary and should remain even if bbox support is added.

## Minimum technology-lock checklist before implementation

1. Pin Node.js, Python, Next.js, React, FastAPI, Pydantic, settings package, viewer/worker/PDF.js, SQLAlchemy/driver, and parser/OpenAI SDK versions in lockfiles.
2. Decide the PDF viewer/license and prove page focus plus bbox/text fallback on representative PDFs.
3. Decide the current Llama Cloud SDK contract: key/base URL names, tier, version, markdown/spatial output, timeout, retry ownership, and run metadata.
4. Decide the OpenAI API mode, strict JSON Schema, model snapshot, reasoning effort, and failure/refusal handling.
5. Add root secret/file ignores and startup environment validation; define frontend API URL and CORS/proxy topology.
6. Define the in-process job/recovery strategy, SQLite connection pragmas, transaction/migration policy, and RFC 9457-or-project-specific error contract.

Until these items are resolved, the architecture should remain **conditional** rather than being treated as a reproducible implementation baseline.
