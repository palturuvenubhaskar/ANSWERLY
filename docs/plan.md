# Implementation Plan

## Goal
Build an MVP that imports a PDF or DOCX question bank, extracts and reviews questions, generates answers in parallel, verifies and revises them, and exports PDF, DOCX, Markdown, and JSON.

## Architecture decision
Use a modular monolith: Next.js + FastAPI + PostgreSQL + Redis/Celery workers. Use PyMuPDF for PDFs, Tesseract OCR fallback for scanned pages, python-docx for DOCX extraction, and a provider-neutral model gateway.

## Milestones

### M0 — Repository and contracts
- Create repository structure, formatting, linting, typing, and CI.
- Define Pydantic schemas from `schemas.md`.
- Add environment template and Docker Compose for PostgreSQL/Redis.
- Add health/readiness endpoints and structured logging.

**Exit criteria:** clean local startup; schema tests; CI checks run.

### M1 — Authentication and projects
- Add authentication and ownership enforcement.
- Add project create/list/open/update/delete.
- Add private storage abstraction.

**Exit criteria:** cross-user access tests pass.

### M2 — Document ingestion
- Upload PDF/DOCX; validate and store privately.
- Extract text, preserve source locations, run OCR fallback.
- Parse units/questions/marks and show review UI.

**Exit criteria:** no silently lost questions in labeled fixtures; uncertain extraction is flagged.

### M3 — Question workspace
- CRUD and reorder extracted questions.
- Allow user correction before processing.
- Show original source wording and provenance.

**Exit criteria:** edits persist and are auditable.

### M4 — AI processing
- Add model gateway, prompts, schema validation, generator/verifier/refiner.
- Add per-question Celery jobs, bounded concurrency, idempotency, retries, cancellation.
- Persist immutable answer versions, reports, and model-call metrics.

**Exit criteria:** state machine and revision cap tests pass.

### M5 — Progress and review
- Add document-level dashboard, SSE/polling, question filters, answer history, manual review and approval actions.

**Exit criteria:** UI status matches persisted backend state.

### M6 — Exports
- Add PDF, DOCX, Markdown, JSON renderers.
- Export selected questions in original order and label unapproved answers.

**Exit criteria:** all export fixtures open and include each selected question exactly once.

### M7 — Hardening and release
- Security review, evaluation set, load/concurrency tests, staging deployment, backups, monitoring, retention settings.

**Exit criteria:** release gates in `evaluation.md` and `test.md` are met.

## Engineering principles
Keep provider-specific behavior isolated. Prefer small modules and explicit contracts. Do not add microservices, vector databases, or complex agent frameworks to the MVP without a validated requirement.
