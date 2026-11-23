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
- [ ] Validate PDF/DOCX extension, MIME signature, size, and structure.
- [ ] Store original files privately and calculate SHA-256.
- [ ] Extract PDF text/page boundaries with PyMuPDF.
- [ ] Extract DOCX paragraphs/tables.
- [ ] Add OCR fallback for scanned PDF pages.
- [ ] Detect units, sections, question numbers, marks, BL, and CO when present.
- [ ] Preserve source page/range and extraction confidence.
- [ ] Build extraction preview and correction UI.
- [ ] Flag ambiguous records; never silently drop content.

## Epic 3 — Question workspace
- [ ] Implement question list/detail/edit/reorder.
- [ ] Preserve original extracted text alongside user-corrected text.
- [ ] Add duplicate suggestions without automatic deletion.
- [ ] Allow processing only after extraction confirmation.

## Epic 4 — AI processing
- [ ] Implement provider-neutral model gateway.
- [ ] Implement versioned generator/verifier/refiner prompts.
- [ ] Validate model output against `schemas.md`.
- [ ] Create one idempotent job per question per run.
- [ ] Implement bounded parallel workers and provider rate limits.
- [ ] Implement transient retries, cancellation, and stale-lease recovery.
- [ ] Enforce two-revision maximum.
- [ ] Persist immutable answer versions and verification reports.
- [ ] Track provider, model, prompt version, tokens, latency, and estimated cost.

## Epic 5 — Review and progress
- [ ] Show queued/generating/verifying/revising/approved/manual-review/failed/cancelled counts.
- [ ] Add SSE progress with polling fallback.
- [ ] Show answer, verifier report, and version history.
- [ ] Add edit, approve, regenerate, retry, and cancel actions.

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
