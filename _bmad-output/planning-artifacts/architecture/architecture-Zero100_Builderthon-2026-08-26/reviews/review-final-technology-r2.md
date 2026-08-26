# Final Technology / Version Reality Review (r2)

## Verdict

**REVISE/FAIL.** The stack names are mostly real and the recent `llama_cloud 2.14.1` migration is valid, but the finalization gate is not clear for implementation or external-data demo use. Two critical findings and seven high findings remain. No critical/high finding is safely deferred without an explicit contract change.

Review date: 2026-08-27. Source documents were not edited.

## Critical findings

### C-01 — React pin is below the currently safe RSC patch level

- **References:** `ARCHITECTURE-SPINE.md` §Stack, Frontend UI/Styling (line 255); §Design Paradigm (line 50); `PRESENTATION-SYSTEM-DESIGN.md` §2 (line 23).
- **Finding:** The spine pins React 19.2.1, while the official React security notice identifies 19.2.4 as the safe 19.2 line for the later React Server Components DoS fixes. Next.js App Router uses RSC. The presentation companion also broadens this to `React 19.2`.
- **Required disposition:** Pin `react` and `react-dom` together to the current patched release compatible with the selected Next.js release (at least 19.2.4 as of this review), verify all `react-server-dom-*` resolutions in the lockfile, and synchronize the companion diagram.
- **Classification:** **Genuine phase-blocker** — security/runtime boundary, not a deferred enhancement.
- **Official source:** [React RSC security update](https://react.dev/blog/2025/12/11/denial-of-service-and-source-code-exposure-in-react-server-components).

### C-02 — Demo identity and authorization are asserted, not implementable

- **References:** `ARCHITECTURE-SPINE.md` AD-9 rules 1–5 (lines 163–167); Core API Contracts (lines 223–231); role contract (line 235); ERD `REVIEW_LOG.reviewer_id/reviewer_role` (lines 462–464), question actor fields (lines 514–516), verification/decision actor fields (lines 547 and 560).
- **Finding:** The document says “server-verified demo session,” but defines no authentication/session mechanism, principal schema, session endpoint, token/cookie validation, or rule deriving actor identity and role from the server principal. Client-provided string fields remain the only modeled authorship boundary. A role toggle cannot enforce ownership, HR-only approval, or LEAD-only decision recording.
- **Required disposition:** Specify the MVP demo authentication mechanism, verified principal/session fields, server-derived actor identity, role-at-event capture, expiry/revocation behavior, and endpoint-level read/write matrix. Keep SSO and multi-tenancy deferred only after this local authorization contract exists.
- **Classification:** **Genuine phase-blocker** — audit integrity and applicant-data access cannot be safely implemented as written.
- **Official source:** [FastAPI security utilities and OAuth2 guidance](https://fastapi.tiangolo.com/tutorial/security/).

## High findings

### H-01 — Llama Cloud SDK is pinned, but the parser API/output contract is still floating

- **References:** `ARCHITECTURE-SPINE.md` AD-6 rules 1–2 (lines 136–137); AD-7 rules 2 and 5 (lines 146 and 149); Stack, Document Parser (line 259); Deferred section (line 622); source tree parser boundary (line 581).
- **Finding:** `llama_cloud` 2.14.1 is current and real, but the official v2 flow is file upload plus parsing job/result retrieval and exposes explicit `tier`, `version`, and `expand=["markdown"]` choices. The spine does not pin or record the parser `tier`, parser `version` (the official quickstart uses `latest`), page/Markdown result shape, or the exact SDK client call. Its 90-second/one-retry policy also does not say how the SDK defaults are overridden; the SDK documents five automatic retries and a one-minute default request timeout.
- **Required disposition:** Name the exact install/import package, client calls, parse tier/version, Markdown/page/location projection, polling/total deadline, `max_retries`, and provider error mapping; record those values in `ProcessingRun`.
- **Classification:** **Genuine phase-blocker** — the core PDF-to-Markdown boundary is not reproducible.
- **Official sources:** [LlamaParse quickstart](https://developers.llamaindex.ai/llamaparse/), [Llama Cloud Python SDK](https://github.com/run-llama/llama-parse-py), [llama-cloud 2.14.1 on PyPI](https://pypi.org/project/llama-cloud/2.14.1/).

### H-02 — Node.js floor permits an EOL runtime and deployment pins are incomplete

- **References:** `ARCHITECTURE-SPINE.md` §Stack, Runtime (line 265); source tree/package inputs (lines 584–594); Deferred D-05 and runtime note (lines 618 and 622).
- **Finding:** `Node.js 20.9+` permits the entire Node 20 line, which the official release schedule marks EOL as of 2026-03-24. The artifact does not name a supported LTS major, package manager/version, exact lockfile policy, or the Python dependency lock it claims will be a deployment input; the source tree lists only `requirements.txt`.
- **Required disposition:** Select a currently supported Node LTS line, pin the exact runtime/package-manager policy, commit the frontend lockfile and a hash-locked Python dependency lock, and state the single-process deployment command/configuration. Do not use D-05 to defer the runtime boundary.
- **Classification:** **Genuine phase-blocker** for implementation/deployment reproducibility; public-domain/link selection itself remains deferred.
- **Official source:** [Node.js EOL policy](https://nodejs.org/en/about/eol).

### H-03 — OpenAI SDK/package and strict Responses schema boundary are unspecified

- **References:** `ARCHITECTURE-SPINE.md` AD-6 rule 2 (line 137); Stack, LLM Provider (line 261); source tree dependency input (line 585).
- **Finding:** The stack names the OpenAI service/model but no `openai` SDK package/version and no raw HTTP client alternative. “Structured JSON mode” is also ambiguous: the official Responses API distinguishes older `json_object` JSON mode from `json_schema` Structured Outputs with `strict` schema adherence. The document does not define the request field (`text.format`), exact schema, refusal/incomplete-output handling, `store` behavior, or resolved response model metadata.
- **Required disposition:** Choose and pin the SDK (or explicitly choose raw HTTPS), then define the exact Responses request/response contract, strict schema, semantic validation order, refusal/truncation handling, timeout, and metadata persisted per run.
- **Classification:** **Genuine phase-blocker** — the extractor cannot be independently implemented against a stable external boundary.
- **Official sources:** [OpenAI Responses API reference](https://developers.openai.com/api/reference/cli/resources/beta/subresources/responses), [official OpenAI Python SDK](https://github.com/openai/openai-python).

### H-04 — PDF.js worker and non-Latin rendering requirements remain deferred

- **References:** `ARCHITECTURE-SPINE.md` Stack, PDF Rendering (line 256); AD-4 rule 2 (lines 120–121); source tree PDF viewer (lines 588–590); Deferred D-07 and worker note (lines 620 and 622).
- **Finding:** `react-pdf` 10.5.0 is real and pins `pdfjs-dist` 5.4.296, but “compatible version in the lockfile” is not an executable worker contract. The official integration requires the worker to be configured from the same client module that renders `Document/Page` and SSR to be skipped in Next.js. The official guide also requires cMaps for reliable non-Latin rendering. D-07 may defer the supported BBox range, but it cannot defer worker source/version, client-only loading, or fixture validation.
- **Required disposition:** Pin `pdfjs-dist` 5.4.296 explicitly, define the same-module worker and no-SSR integration, decide bundled cMaps/standard-font assets, and run a real PDF browser smoke test including the intended Korean/non-Latin fixture or explicitly scope the demo to ASCII-only PDFs.
- **Classification:** **Genuine phase-blocker** for the core split-view demo; only unsupported BBox coverage may remain deferred.
- **Official sources:** [react-pdf 10.5.0 package metadata](https://raw.githubusercontent.com/wojtekmaj/react-pdf/v10.5.0/packages/react-pdf/package.json), [react-pdf 10.5.0 integration guide](https://raw.githubusercontent.com/wojtekmaj/react-pdf/v10.5.0/packages/react-pdf/README.md).

### H-05 — The operational diagram contradicts the declared asynchronous worker contract

- **References:** `ARCHITECTURE-SPINE.md` AD-7 rule 5 (line 149) versus sequence diagram upload flow (lines 295–309); `PRESENTATION-SYSTEM-DESIGN.md` §2, Router-to-pipeline edge (line 70).
- **Finding:** AD-7 requires `202 Accepted`, persisted `QUEUED/STARTED` state, and a DB-backed single worker, but the sequence diagram shows the API directly invoking the parser and the presentation diagram shows the router directly connected to the pipeline. There is no worker participant, enqueue boundary, status response, or ownership of recovery/heartbeat transitions in the diagrams.
- **Required disposition:** Make the worker/enqueue boundary explicit in both diagrams and the OpenAPI contract: upload persists an idempotent job and returns 202; worker owns provider calls and stage transitions; status polling and retry semantics are defined separately.
- **Classification:** **Genuine phase-blocker** — otherwise API behavior and failure recovery will diverge between independently built units.
- **Official source:** [LlamaParse quickstart job/polling flow](https://developers.llamaindex.ai/llamaparse/).

### H-06 — Preview processing required by the PRD has no matching upload API contract

- **References:** `prd.md` UF-1 and FR-004/FR-011 (lines 63, 83, and 99); `ARCHITECTURE-SPINE.md` AD-1 rule 2 (line 97); Core API Contracts, upload (line 219), and status/output contracts (lines 220–222).
- **Finding:** The PRD permits exploratory processing/review with an unapproved criteria version, marked as preview, while the only upload contract says it receives an approved version. No preview-mode upload/request field, preview response shape, or persisted watermark/status contract is defined. A builder can satisfy either document while violating the other.
- **Required disposition:** Define one upload command with explicit `mode=PREVIEW|OFFICIAL` (or a separate preview endpoint), its approval preconditions, response/status fields, and the rule preventing preview outputs from becoming official handoff/decision inputs.
- **Classification:** **Genuine phase-blocker** for PRD coverage and API interoperability.

### H-07 — Base-URL allowlisting is named but not operationally closed

- **References:** `ARCHITECTURE-SPINE.md` AD-6 rule 3 (line 138); AD-9 rules 1 and 4 (lines 163 and 166); Runtime Configuration (line 263); `prd.md` AI model criterion (line 149).
- **Finding:** Both providers accept environment-configured base URLs, but the artifacts do not enumerate approved origins, distinguish the official OpenAI/Llama Cloud endpoints from allowed compatible endpoints, define startup failure behavior, or state whether `.env` is permitted outside local development. With applicant PDFs and provider API keys, “HTTPS and allowed host list” is not enough for an implementer to produce the same security boundary.
- **Required disposition:** Enumerate approved hosts or make provider URLs fixed/default-only for the MVP; reject unexpected hosts at startup, prohibit user-controlled overrides, redact endpoint/auth headers, and record the resolved provider contract in `ProcessingRun`.
- **Classification:** **Genuine phase-blocker** for any run that sends applicant data to external providers. It can be deferred only if the MVP is explicitly offline/precomputed and the environment variables are disabled.

## Deferred items that remain legitimate

The following can remain deferred as scoped: exact question count (D-01), demo dataset quantity/selection (D-02), baseline comparison (D-03), problem-card evidence selection (D-04), public repository/deployment link selection (D-05), metric measurement (D-06), and the supported BBox range (D-07). None of these deferrals covers the phase-blockers above; in particular D-07 does not cover worker wiring or PDF text assets.

## Verification note

The configured `lint_spine.py` mechanical pass could not run because `uv` is not installed in the review environment. Direct inspection found no basis to convert the verdict to PASS; source artifacts remain unmodified.

## Official sources consulted

- [Next.js official release feed](https://nextjs.org/blog)
- [React RSC security updates](https://react.dev/blog/2025/12/11/denial-of-service-and-source-code-exposure-in-react-server-components)
- [Node.js EOL policy](https://nodejs.org/en/about/eol)
- [LlamaParse quickstart](https://developers.llamaindex.ai/llamaparse/)
- [Llama Cloud Python SDK](https://github.com/run-llama/llama-parse-py)
- [llama-cloud 2.14.1 package](https://pypi.org/project/llama-cloud/2.14.1/)
- [OpenAI GPT-5.6 Luna model page](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
- [OpenAI Responses API reference](https://developers.openai.com/api/reference/cli/resources/beta/subresources/responses)
- [official OpenAI Python SDK](https://github.com/openai/openai-python)
- [react-pdf 10.5.0 package metadata](https://raw.githubusercontent.com/wojtekmaj/react-pdf/v10.5.0/packages/react-pdf/package.json)
- [react-pdf 10.5.0 README](https://raw.githubusercontent.com/wojtekmaj/react-pdf/v10.5.0/packages/react-pdf/README.md)
- [FastAPI security guidance](https://fastapi.tiangolo.com/tutorial/security/)
