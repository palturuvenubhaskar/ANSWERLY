# System Architecture

## 1. Product shape
Answerly accepts a question-bank document, extracts individual questions, generates an answer for each question, independently verifies and revises answers, then exports selected results.

Use a **modular monolith** initially. Do not split into microservices without a demonstrated scaling or ownership need.

## 2. Technology baseline
- Frontend: Next.js, React, TypeScript.
- API: FastAPI, Python, Pydantic.
- Database: PostgreSQL, SQLAlchemy, Alembic.
- Queue: Redis broker with Celery workers.
- PDF text extraction: PyMuPDF.
- OCR fallback: Tesseract (with required language packs).
- Model access: provider-neutral OpenRouter gateway, with configurable provider/model routing.
- Progress: Server-Sent Events (SSE), with polling fallback.
- Exports: reportlab for PDF, python-docx for DOCX, native Markdown/JSON serialization.

## 3. Logical components
### Frontend
Upload and document management, extraction preview/correction, unit/question list, answer workspace, processing progress, answer history, and export center.

### FastAPI modules
`auth`, `projects`, `documents`, `extraction`, `questions`, `processing`, `ai_gateway`, `answers`, `exports`, `events`.

### Workers
One independently retryable processing task per question. Bound concurrency globally and per provider. Use database-backed state as the source of truth; Redis/Celery is transport, not the only record of work.

### Storage
Keep originals and exports in private object storage in production. Local private filesystem storage is acceptable in development. Store storage keys and metadata in PostgreSQL, not public URLs.

## 4. Ingestion workflow
1. Authenticate user and verify project ownership.
2. Validate extension, MIME signature, size, and PDF/DOCX structure.
3. Store original file privately and calculate SHA-256.
4. Extract text page-by-page (PDF) or paragraph/table-by-paragraph (DOCX).
5. Run OCR on scanned PDF pages when text extraction is insufficient.
6. Detect units, sections, question boundaries, marks, BL, and CO when present.
7. Save questions with source page/range and extraction confidence.
8. Show preview; user can correct ambiguous records.
9. Mark document `READY` only after the user confirms extraction.

## 5. Question processing state machine
```text
PENDING -> QUEUED -> GENERATING -> VERIFYING
                                  | approved
                                  v
                          VERIFIER_APPROVED
                                  |
                       needs_revision (if < 2 revisions)
                                  v
                               REVISING
                                  |
                                  v
                               VERIFYING
                                  |
                    still not approved after 2 revisions
                                  v
                           MANUAL_REVIEW

Operational errors: RETRY_WAIT -> prior active state, or FAILED
User cancellation: CANCELLED
```
The initial generation is not a revision. At most two refiner passes are allowed. Transient provider errors, rate limits, and timeouts use retry/backoff and do not consume revision attempts. Permanent operational errors become `FAILED`.

## 6. AI processing sequence
1. Orchestrator claims a question job using a database lock/lease.
2. Build a prompt using trusted system instructions plus clearly delimited untrusted question/reference text.
3. Call generator; validate `AnswerContent`.
4. Save immutable answer version and model-call metadata.
5. Call verifier; validate `VerificationReport`; save report.
6. If approved, set question/job to `VERIFIER_APPROVED`. Human approval is stored separately against the exact answer version.
7. If revision required and revision count is below two, call refiner, save a new version, and verify again.
8. Otherwise set `MANUAL_REVIEW`.
9. Publish state changes for SSE clients.

## 7. Parallelism and idempotency
- One logical job per question per processing run.
- Store the request idempotency key on a parent processing run, scoped by user and project. Hash the request payload, including the document ID; return the existing run for an identical retry and reject a different payload with the same key.
- Create the run and all per-question jobs in one transaction.
- Claim jobs atomically; use row locks or leases to prevent two workers processing the same logical attempt.
- A retried Celery delivery must detect an already completed attempt and return safely.
- Configure worker concurrency, provider rate limits, per-user quotas, and global in-flight request limits.
- One question failing must not stop other questions in the document.

## 8. Reliability and observability
Persist state in PostgreSQL. Record correlation IDs, structured errors, provider/model, prompt version, token counts, latency, and estimated cost. Use exponential backoff with jitter for transient failures. Support cancellation and recovery of stale leases after worker restarts.

## 9. Deployment topology
Initial deployment: one Next.js service, one FastAPI service, one or more Celery worker processes, managed PostgreSQL, managed Redis, and private object storage. Keep local development runnable with Docker Compose.
