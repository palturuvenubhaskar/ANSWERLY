# Project Tasks

## Epic 0 — Contracts and repository
- [x] Create the initial repository structure and root `AGENTS.md`.
- [x] Implement canonical Pydantic schemas from `schemas.md`.
- [x] Add formatting, linting, typing, tests, and CI.
- [x] Add `.env.example` and Docker Compose for PostgreSQL/Redis.
- [x] Add liveness/readiness endpoints and structured startup/error logs.

## Epic 1 — Projects and access control
- [x] Implement registration/login with password hashing and bearer authorization.
- [x] Implement project create/list/open/rename/delete.
- [x] Enforce ownership checks on all project resources.
- [x] Add private storage abstraction.

## Epic 2 — Document ingestion
- [x] Validate PDF/DOCX extension, MIME signature, size, and structure.
- [x] Store original files privately and calculate SHA-256.
- [x] Extract PDF text/page boundaries with PyMuPDF.
- [x] Extract DOCX paragraphs/tables.
- [x] Add OCR fallback for scanned PDF pages.
- [x] Detect units, sections, question numbers, marks, BL, and CO when present.
- [x] Preserve source page/range and extraction confidence.
- [x] Build extraction preview and correction endpoints.
- [x] Flag ambiguous records; never silently drop content.

## Epic 3 — Question workspace
- [x] Implement question list/detail/edit/reorder.
- [x] Preserve original extracted text alongside user-corrected text.
- [x] Add duplicate suggestions without automatic deletion.
- [x] Allow processing only after extraction confirmation.

## Epic 4 — AI processing
- [x] Implement provider-neutral model gateway.
- [x] Implement versioned generator/verifier/refiner prompts.
- [x] Validate model output against `schemas.md`.
- [x] Create one idempotent job per question per run.
- [x] Implement bounded execution engine and provider rate limits.
- [x] Implement transient retries, cancellation, and stale-lease recovery.
- [x] Enforce two-revision maximum.
- [x] Persist immutable answer versions and verification reports.
- [x] Track provider, model, prompt version, tokens, latency, and estimated cost.

## Epic 5 — Review and progress
- [x] Show queued/generating/verifying/revising/approved/manual-review/failed/cancelled counts.
- [x] Add SSE progress with polling fallback.
- [x] Show answer, verifier report, and version history.
- [x] Add edit, approve, regenerate, retry, and cancel actions.

## Epic 6 — Exports
- [ ] Implement PDF, DOCX, Markdown, and JSON.
- [ ] Preserve original unit/question order.
- [ ] Add include/exclude options for unapproved answers.
- [ ] Label included unapproved/manual-review answers.
- [ ] Validate each generated export.

## Epic 7 — Hardening and release
- [ ] Run automated tests in `test.md`.
- [ ] Build and review the labeled evaluation set in `evaluation.md`.
- [ ] Add rate limits, quotas, retention, and audit events.
- [ ] Deploy staging, configure backups/monitoring, and verify recovery.
