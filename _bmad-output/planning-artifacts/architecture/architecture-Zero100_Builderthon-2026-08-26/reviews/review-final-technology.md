# Final Technology / Reality Check

## Verdict

**NO-GO for implementation as written. Conditional GO after the critical/high findings below are resolved.**

The selected frontend/backend versions are generally compatible, and `react-pdf 10.5.0`, FastAPI `0.141.1`, Pydantic `2.13.4`, SQLAlchemy `2.0.52`, and OpenAI `gpt-5.6-luna` are real available releases/models. The spine still contains four material reality gaps: the selected `llama-parse 0.6.94` package is deprecated; `Next.js 16.3.x` and `React 19.2.x` are unsafe ranges rather than secure reproducible pins; the PDF.js worker contract is incomplete; and the deferred role-toggle approach cannot enforce the stated reviewer/approver/decision permissions.

Review date: 2026-08-27. The spine was not edited.

## Version and fit verification

| Area | Result | Reality check |
|---|---|---|
| Next.js | Conditional fit | Next.js 16.3 exists and is aligned with React 19.2/App Router, but the official August 2026 security release identifies `16.3.3` as the Active LTS target. `16.3.x` is too broad for a secure build. Next.js 16 also requires Node.js `20.9+`. |
| React | Conditional fit | React 19.2 is supported by Next.js 16 and the model UI use case. However, React Server Components releases including `19.2.0` were affected by a CVSS 10.0 unauthenticated RCE; the fixed React line starts at `19.2.1`. Pin `react` and `react-dom` together to a patched exact version. |
| react-pdf | Fit with required integration changes | `react-pdf 10.5.0` is a real release and its package metadata pins `pdfjs-dist` to `5.4.296`. The spine must name that transitive version and require the worker to use the same version. The worker must be configured in the same client module that renders `<Document>`/`<Page>`, with SSR skipped. |
| PDF.js worker | Not sufficiently specified | “Compatible version in the lockfile” is not an executable contract. The build needs an explicit worker source, client-only loading, and a smoke test that the runtime PDF.js version and worker version match. Non-Latin text also requires cMaps configuration when applicable. |
| FastAPI | Fit | `0.141.1` was released 2026-07-29 and requires Python `>=3.10`; it is compatible with Pydantic v2. The spine still needs an explicit Python runtime and server execution model. |
| Pydantic | Fit with settings dependency | `2.13.4` was released 2026-05-06. It is appropriate for API schemas and semantic validation, but `.env`/environment loading in Pydantic v2 is provided by the separate `pydantic-settings` package, which is not named in the stack. |
| llama-parse | **Does not fit as selected** | PyPI marks `llama-parse 0.6.94` deprecated and says maintenance ended 2026-05-01, with migration to `llama-cloud>=1.0`. The old `result_type="markdown"` client contract must not be treated as the current SDK contract without a deliberate migration/exception. |
| LlamaParse configuration | Conditional fit | `LLAMA_CLOUD_API_KEY` and `LLAMA_CLOUD_BASE_URL` are recognized by the current Llama Cloud Python SDK, but the current SDK uses the `llama_cloud` package and a file-upload/parse-job flow. The architecture needs the exact SDK, API flow, output version/tier, polling, timeout, and page/location metadata contract. |
| OpenAI gpt-5.6-luna | Fit with reproducibility guard | The official model page lists Chat Completions and Responses endpoints and supports Structured Outputs. The alias is suitable for cost-sensitive extraction, but “fixed model identifier” alone does not make outputs reproducible; record the resolved model/snapshot and schema/prompt versions, and pin a snapshot where available. |
| SQLAlchemy / SQLite | Fit only for constrained demo operation | SQLAlchemy `2.0.52` is a current 2.0 release. SQLite is suitable for a single-process/local demo, but file-level write locking makes concurrent parsing, reviews, approvals, and decisions fragile unless access is serialized and lock/backoff settings are explicit. |

## Critical findings

### F-01 — Deprecated parser package is the selected MVP dependency

- **Severity:** Critical
- **Location:** Stack, “Document Parser” (line 231); AD-6 rules 1–2 (lines 135–136); source tree `llamaparse_client.py` (line 534)
- **Trigger condition:** The implementation installs `llama-parse==0.6.94` after its upstream maintenance window has ended.
- **Finding:** The official PyPI page for `llama-parse 0.6.94` carries a deprecation notice stating that the repository/packages were maintained only until 2026-05-01 and directs users to `pip install llama-cloud>=1.0`. The review date is 2026-08-27. This is not merely an old patch; it is the wrong package line for a new implementation.
- **Required guard:** Replace the dependency and client contract with the current `llama_cloud` SDK/API, or explicitly document and accept a frozen deprecated dependency as a time-boxed demo exception with a successful clean-environment install and API smoke test. Update the parser module name and the processing-run metadata to record the parser package/API version.
- **Consequence:** Installation, authentication, request shape, polling, maintenance, and output behavior can diverge from the architecture; the core PDF-to-Markdown pipeline can fail before any evidence mapping occurs.
- **Source:** [LlamaParse 0.6.94 on PyPI](https://pypi.org/project/llama-parse/0.6.94/), [current Llama Cloud Python SDK](https://github.com/run-llama/llama-parse-py)

### F-02 — The deferred role toggle defeats the stated authorization model

- **Severity:** Critical
- **Location:** Deferred item 1 (line 542); AD-9 rule 2 (line 162); Core API contracts (lines 196–205)
- **Trigger condition:** A browser user changes the HR/Tech role toggle or submits a caller-controlled `reviewer_id`, `reviewer_role`, `recorded_by`, or approval identity.
- **Finding:** The spine requires per-reviewer ownership, role-gated approval, handoff finalization, verification, and decision recording, but defers SSO and replaces identity with a simple role toggle. CORS allowlisting does not authenticate a caller. Without a server-verified principal, any client can impersonate HR, Tech, or Lead and mutate another reviewer’s records or enter a final decision.
- **Required guard:** Add server-side authentication and authorization with a verified principal on every mutation; derive reviewer/role/recorded-by fields from that principal. If this is strictly a local demo, bind the API to localhost or place it behind explicit demo authentication and label all outputs non-production.
- **Consequence:** AD-1, AD-3, AD-8, and AD-9 are unenforceable; audit history and final decisions are forgeable.
- **Source:** [FastAPI security documentation](https://fastapi.tiangolo.com/tutorial/security/)

### F-03 — Next.js version range includes known vulnerable or non-current releases

- **Severity:** Critical
- **Location:** Stack, “Frontend Framework” (line 226); frontend labels in diagram/source tree (lines 50 and 515)
- **Trigger condition:** Dependency resolution selects an older `16.3.x` patch instead of the current security-patched release.
- **Finding:** The official Next.js release feed states that the 2026-08-25 security release targets `16.3.3` as Active LTS and addresses two Critical severity vulnerabilities. `16.3.x` does not guarantee that patch. The spine also still labels parts of the system “Next.js 15,” creating a direct implementation ambiguity.
- **Required guard:** Pin `next` to the exact patched release verified at build time (currently `16.3.3` in the reviewed source), commit the package-manager lockfile, and make all diagrams/source-tree labels consistently say Next.js 16.3.3. Add a dependency audit/update gate before the demo build.
- **Consequence:** A clean install can deploy a vulnerable framework or a Next.js 15/16-mixed codebase with incompatible assumptions.
- **Source:** [Next.js official release feed](https://nextjs.org/blog), [Next.js 16 upgrade guide](https://nextjs.org/docs/app/guides/upgrading/version-16)

### F-04 — React 19.2.x range includes a CVSS 10.0 RSC vulnerability

- **Severity:** Critical
- **Location:** Stack, “Frontend UI/Styling” (line 227); Next.js App Router/RSC usage (lines 50 and 226)
- **Trigger condition:** The lockfile resolves `react`/`react-dom` to `19.2.0` or another unpatched RSC dependency.
- **Finding:** The official React security advisory says the unauthenticated RCE affected React Server Components packages in `19.2.0`, and identifies `19.2.1` as a fixed version. Next.js App Router uses React Server Components, so a broad `19.2.x` requirement is not an acceptable security boundary.
- **Required guard:** Pin `react` and `react-dom` together to a patched exact release at or above `19.2.1`, verify the resolved `react-server-dom-*` packages through the lockfile/audit, and rebuild after every framework security advisory.
- **Consequence:** A public deployment could expose unauthenticated server-side code execution through the RSC protocol.
- **Source:** [React security advisory for React Server Components](https://react.dev/blog/2025/12/03/critical-security-vulnerability-in-react-server-components)

## High findings

### F-05 — PDF.js worker compatibility is underspecified for react-pdf 10.5.0

- **Severity:** High
- **Location:** Stack, “PDF Rendering” (line 228); Deferred item 6 (line 547); `PDFViewer`/split-view components (lines 510 and 534)
- **Trigger condition:** The app uses a worker file from a different `pdfjs-dist` release, configures it in a separate module, or lets the PDF component load during SSR.
- **Finding:** The official `react-pdf 10.5.0` package metadata pins `pdfjs-dist` to `5.4.296`. Its README requires `workerSrc` to be configured in the same module that renders React-PDF components and says the module must skip SSR in Next.js. The current spine delegates the exact worker version to a future build decision and does not state the client-module/SSR rule.
- **Required guard:** Pin `react-pdf==10.5.0` and `pdfjs-dist==5.4.296`, configure `pdfjs.GlobalWorkerOptions.workerSrc` from that exact package in the PDF client component, dynamically import that client component with SSR disabled, and add a browser smoke test that loads a real PDF and asserts no fake-worker/version-mismatch error.
- **Consequence:** The split viewer can fail at runtime with worker loading/version errors, making the core presentation path unusable.
- **Source:** [react-pdf 10.5.0 README](https://raw.githubusercontent.com/wojtekmaj/react-pdf/v10.5.0/packages/react-pdf/README.md), [react-pdf 10.5.0 package metadata](https://raw.githubusercontent.com/wojtekmaj/react-pdf/v10.5.0/packages/react-pdf/package.json)

### F-06 — PDF text fidelity for Korean/non-Latin resumes is not closed

- **Severity:** High
- **Location:** Stack, “PDF Rendering” (line 228); AD-2 location/fallback rule (line 106)
- **Trigger condition:** A resume contains Korean or another non-Latin character set and the viewer has no cMap assets/options.
- **Finding:** The react-pdf 10.x documentation states that non-Latin rendering may require shipping cMaps and passing `cMapUrl`/`cMapPacked`. The current fallback contract only addresses missing BBox/page location, not missing font/cMap assets.
- **Required guard:** Decide whether cMaps are bundled under `public/` or served from a pinned same-version asset source, pass the corresponding `Document` options, and include Korean/non-Latin fixture PDFs in the browser smoke test.
- **Consequence:** The PDF may render with missing glyphs or warnings even when citation coordinates and fallback snippets are correct.
- **Source:** [react-pdf 10.5.0 README, cMaps section](https://raw.githubusercontent.com/wojtekmaj/react-pdf/v10.5.0/packages/react-pdf/README.md)

### F-07 — Runtime and dependency reproducibility is incomplete

- **Severity:** High
- **Location:** Stack (lines 226–235); source tree `requirements.txt`/lockfile assumptions (lines 513–515); Deferred item 5 (line 546)
- **Trigger condition:** A new developer or clean runner uses a different Node, Python, package manager, SQLite library, or transitive dependency set.
- **Finding:** Next.js 16 requires Node.js 20.9+, FastAPI 0.141.1 requires Python 3.10+, and the spine says `SQLite 3.45+`, but no Node/Python/package-manager versions, lockfile policy, hashes, or SQLite runtime verification are defined. A plain `requirements.txt` does not by itself freeze Python transitive dependencies. Deferring the deployment environment also defers the conditions needed to reproduce the demo.
- **Required guard:** Commit exact `next/react/react-dom/react-pdf/pdfjs-dist` lockfile entries; define Node.js (at least 20.9), Python (at least 3.10), package managers, a Python lockfile/hashed requirements, and a startup diagnostic that logs and rejects unsupported SQLite versions.
- **Consequence:** “Works on one laptop” can become a clean-install failure, worker mismatch, security drift, or incompatible database behavior during presentation.
- **Source:** [Next.js installation requirements](https://nextjs.org/docs/app/getting-started/installation), [FastAPI 0.141.1 on PyPI](https://pypi.org/project/fastapi/0.141.1/)

### F-08 — Pydantic v2 settings dependency is missing from the stack contract

- **Severity:** High
- **Location:** Stack, “Data Validation” and “Runtime Configuration” (lines 230 and 234); `backend/app/core/config.py` (line 534)
- **Trigger condition:** `core/config.py` attempts to load `.env` through `BaseSettings` while only `pydantic` is installed.
- **Finding:** Pydantic v2 places settings management in the separate `pydantic-settings` package. FastAPI also lists `pydantic-settings` as an additional dependency rather than a dependency of the base framework. The spine relies on `.env` and environment variables but does not name or pin the package.
- **Required guard:** Add and pin `pydantic-settings`; define a typed settings object with required secret fields, explicit defaults, URL validation, fail-closed startup checks, and no secret values in error output.
- **Consequence:** Configuration can fail at import/startup or silently fall back to unsafe defaults, depending on the implementation.
- **Source:** [Pydantic Settings documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/), [FastAPI 0.141.1 dependency notes](https://pypi.org/project/fastapi/0.141.1/)

### F-09 — The external pipeline lacks a real asynchronous job boundary

- **Severity:** High
- **Location:** AD-6/AD-7 pipeline rules (lines 135–146); sequence diagram upload-to-completion flow (lines 265–279); Deferred item 3 (line 544)
- **Trigger condition:** `POST /api/applications/upload` waits for LlamaCloud parsing, polling, normalization, and OpenAI extraction in the FastAPI request path.
- **Finding:** Current Llama Cloud SDK usage is a file-upload/parse-job flow and documents automatic retries and timeouts. The spine defers concrete timeout/retry values and omits a queue/worker while also requiring durable ProcessingRun state and retry-from-stage semantics. Atomic database state does not make a long-running HTTP request reliable.
- **Required guard:** Return `202 Accepted` after persisting `RECEIVED`/`ProcessingRun`, execute parsing/mapping in a bounded worker or explicitly serialized background runner, persist each stage transition, enforce total/per-provider deadlines, and make retry ownership/idempotency explicit. For the demo, precompute fixtures or constrain the endpoint to one bounded job at a time.
- **Consequence:** Requests can time out while work continues, duplicate processing can occur, and the UI can show a terminal failure even though a provider call later succeeds.
- **Source:** [current Llama Cloud SDK retry/timeout behavior](https://github.com/run-llama/llama-parse-py)

### F-10 — SQLite atomicity does not solve concurrent write locking

- **Severity:** High
- **Location:** Database stack (line 235); AD-7 rule 3 and AD-9 rule 3 (lines 146 and 163); sequence diagram concurrent reviewer/pipeline writes (lines 267–289)
- **Trigger condition:** Pipeline processing, two reviewers, or approval/decision requests write SQLite concurrently.
- **Finding:** SQLAlchemy documents SQLite’s limited write concurrency and file-level locking. The spine requires atomic transactions but does not define WAL mode, busy timeout, retry policy for database locks, process count, or write serialization. A direct FastAPI deployment with more than one worker/process makes the local-store assumption especially fragile.
- **Required guard:** State “single process/single writer” for the MVP, enable and verify foreign keys plus an explicit lock/busy-timeout policy, serialize critical writes, and test simultaneous review/processing/approval requests. Do not claim multi-user reliability from transactions alone.
- **Consequence:** Legitimate saves can return `database is locked`, leaving retries, reviewer edits, or current-mapping promotion inconsistent.
- **Source:** [SQLAlchemy SQLite dialect concurrency documentation](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html)

### F-11 — Overridable base URLs are not constrained as security-sensitive configuration

- **Severity:** High
- **Location:** AD-6 rule 3 (line 137); Runtime Configuration row (line 234)
- **Trigger condition:** `OPENAI_BASE_URL` or `LLAMA_CLOUD_BASE_URL` is set to an arbitrary host, an insecure HTTP URL, or a provider-compatible endpoint with different semantics.
- **Finding:** The architecture treats base URLs as generic environment values while also fixing model/parser identifiers and handling applicant documents. A base URL override can redirect PII and API credentials, defeat the promised provider/model contract, or create an SSRF-like outbound trust boundary if later exposed through configuration APIs.
- **Required guard:** Make base URLs deployment-only, never user-controlled; validate HTTPS and an allowlist of approved origins at startup; reject unexpected hosts; redact URLs/authorization headers from logs; and record the resolved provider endpoint fingerprint in `ProcessingRun`.
- **Consequence:** Applicant PDFs and secrets can be sent to an unintended endpoint, or a compatible endpoint can return materially different extraction behavior.

### F-12 — The model alias is not enough for evidence reproducibility

- **Severity:** High
- **Location:** AD-6 rule 2/3 (lines 136–137); AD-7 rule 2 (line 145); Stack, “LLM Provider” (line 233)
- **Trigger condition:** OpenAI resolves the `gpt-5.6-luna` alias to a changed backend snapshot while the stored run only says `model_identifier = gpt-5.6-luna`.
- **Finding:** The official model documentation distinguishes aliases/snapshots and states that snapshots are the mechanism for locking behavior. The architecture records a model identifier, prompt version, and input fingerprint, but the fixed alias itself does not prove which model snapshot produced a mapping.
- **Required guard:** Pin a supported snapshot when the API exposes one; otherwise store the response’s resolved model identifier, endpoint/API mode, schema hash, prompt version, reasoning settings, and provider request ID, and define an explicit upgrade/re-baseline procedure.
- **Consequence:** The same application and criteria version can produce different evidence mappings without an auditable technology change.
- **Source:** [OpenAI GPT-5.6 Luna model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-luna)

### F-13 — “JSON mode” is weaker than the required structured-output contract

- **Severity:** High
- **Location:** Stack, “LLM Provider” (line 233); AD-6 rule 2 (line 136)
- **Trigger condition:** The extractor requests generic JSON and relies on Pydantic parsing without an API-enforced schema/refusal/incomplete-output branch.
- **Finding:** The official GPT-5.6 Luna page lists Structured Outputs as supported. The spine says “structured JSON mode” but does not specify Responses API versus Chat Completions, the exact schema, strictness, refusal handling, truncation handling, or semantic validation before exact-substring checks.
- **Required guard:** Use the provider’s Structured Outputs schema contract, validate every response with Pydantic, reject refusals/truncation/unknown schema versions, then perform server-side criteria/citation/substring validation before persisting mappings.
- **Consequence:** Syntactically valid JSON can still omit required evidence, invent unsupported enum values, or leave a partial mapping marked as a successful run.
- **Source:** [OpenAI GPT-5.6 Luna model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-luna), [OpenAI Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs)

### F-14 — Uploaded PDF and local-store security controls are incomplete

- **Severity:** High
- **Location:** AD-6 rule 1 (line 135); AD-9 rule 1 (line 161); `APPLICATION.original_pdf_path` and local file store (lines 335 and 369)
- **Trigger condition:** A user uploads a large, malformed, polyglot, password-protected, or adversarial PDF, or an API response exposes a stored path.
- **Finding:** PDF-only input and server-side storage do not provide content validation or isolation. The spine does not specify byte-size/page limits, magic-byte validation, safe generated filenames, path traversal prevention, storage outside the web root, malware scanning, password-PDF behavior, download authorization, file permissions, or retention/deletion rules. Recruitment documents contain personal data and are also sent to external parsing/model providers.
- **Required guard:** Enforce request/body/page limits, validate magic bytes and parseability, generate opaque storage keys, canonicalize and boundary-check paths, store outside static roots, authorize every download, redact provider/error logs, and define demo retention/deletion plus external-provider data handling.
- **Consequence:** Disk exhaustion, parser denial of service, unauthorized resume disclosure, path traversal, or uncontrolled third-party retention can occur.

### F-15 — The API contract has a concrete endpoint mismatch

- **Severity:** High
- **Location:** Interview Question Candidate Contract (lines 183–194) versus presentation sequence diagram (line 286)
- **Trigger condition:** Frontend implements the sequence diagram’s `POST /api/handoff/generate` while backend implements the table’s `POST /api/handoff/{handoff_id}/questions/generate`.
- **Finding:** The same operation has two different paths. The table requires an existing handoff ID; the sequence diagram omits it and implies a combined handoff/question generation operation.
- **Required guard:** Choose one canonical endpoint and update the OpenAPI contract, client, sequence diagram, idempotency key scope, and authorization preconditions together.
- **Consequence:** The demo flow can fail at the handoff-to-question step despite all individual services being available.

## Medium/low findings retained for completeness

### F-16 — Next.js 16 build/lint behavior is not reflected in the delivery contract

- **Severity:** Medium
- **Location:** Frontend source tree and implied build workflow (lines 515–517)
- **Trigger condition:** CI assumes `next build` runs linting as it did in an older setup.
- **Finding:** Next.js 16 no longer runs the linter automatically during `next build`. The spine does not name separate lint/typecheck/test commands.
- **Guard:** Add explicit `lint`, `typecheck`, unit, browser smoke, and production build steps.
- **Consequence:** A presentation build can pass while lint/type errors remain undiscovered.
- **Source:** [Next.js installation documentation](https://nextjs.org/docs/app/getting-started/installation)

### F-17 — OpenAI extraction quality is not gated for a lower-cost model

- **Severity:** Medium
- **Location:** Stack, “LLM Provider” (line 233); Deferred item 4 (line 545)
- **Trigger condition:** `gpt-5.6-luna` produces a valid but incomplete or weak evidence mapping on a real resume.
- **Finding:** The official model page positions Luna for cost-sensitive/high-volume workloads. The spine defers the baseline comparison while making Luna the sole MVP extractor and requiring evidence-grade output.
- **Guard:** Add a small fixed acceptance fixture set with expected citation/enum/substring assertions and a human review gate; fail the run or mark evidence incomplete when thresholds are not met.
- **Consequence:** The system can produce formally valid but operationally untrustworthy recruitment evidence.
- **Source:** [OpenAI GPT-5.6 Luna model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-luna)

### F-18 — External provider request IDs and error classification need provider-specific handling

- **Severity:** Medium
- **Location:** AD-7 rule 2/3 (lines 145–146)
- **Trigger condition:** A provider returns a timeout, rate limit, validation error, partial job, or request ID in a provider-specific header/body shape.
- **Finding:** The architecture requires one generic `provider_request_id` and generic error code but does not define provider-specific extraction, retryability, or idempotency semantics.
- **Guard:** Define provider adapters with normalized error classes (`retryable`, `non_retryable`, `unknown`), request-ID extraction, timeout stage, and retry budget; persist raw provider status without sensitive payloads.
- **Consequence:** Non-retryable errors may be retried, retryable jobs may be abandoned, or audit records may lose the provider correlation needed for diagnosis.

## Official sources consulted

- [Next.js installation/system requirements](https://nextjs.org/docs/app/getting-started/installation)
- [Next.js 16 upgrade guide](https://nextjs.org/docs/app/guides/upgrading/version-16)
- [Next.js official release feed/security releases](https://nextjs.org/blog)
- [React 19.2 release](https://react.dev/blog/2025/10/01/react-19-2)
- [React Server Components security advisory](https://react.dev/blog/2025/12/03/critical-security-vulnerability-in-react-server-components)
- [react-pdf 10.5.0 README](https://raw.githubusercontent.com/wojtekmaj/react-pdf/v10.5.0/packages/react-pdf/README.md)
- [react-pdf 10.5.0 package metadata](https://raw.githubusercontent.com/wojtekmaj/react-pdf/v10.5.0/packages/react-pdf/package.json)
- [FastAPI 0.141.1 on PyPI](https://pypi.org/project/fastapi/0.141.1/)
- [Pydantic 2.13.4 release](https://github.com/pydantic/pydantic/releases/tag/v2.13.4)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [LlamaParse 0.6.94 on PyPI](https://pypi.org/project/llama-parse/0.6.94/)
- [Current Llama Cloud Python SDK](https://github.com/run-llama/llama-parse-py)
- [OpenAI GPT-5.6 Luna model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
- [OpenAI Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs)
- [SQLAlchemy SQLite dialect](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html)
- [FastAPI security documentation](https://fastapi.tiangolo.com/tutorial/security/)
