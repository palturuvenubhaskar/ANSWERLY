# Test Plan

Tests should be automated where practical. Each case should assert an observable result, not merely that a function ran.

## 1. Upload and authorization
- Valid text PDF and DOCX are accepted and stored privately.
- Unsupported extension or mismatched MIME signature is rejected with 4xx.
- File larger than `MAX_UPLOAD_BYTES` is rejected before full processing.
- Empty, malformed, encrypted, or corrupted documents produce actionable errors.
- Unsafe filename/path traversal is neutralized.
- User A cannot access User B's projects, documents, questions, jobs, or exports.
- Confirmed project deletion removes its questions, references, answers, reports, and jobs for the owning user; an unconfirmed request does nothing.

## 2. Extraction
- Single-line and wrapped questions are reconstructed correctly.
- Unit/section headings and question order are preserved.
- Marks, BL, and CO are extracted when present and remain null when absent.
- A question spanning pages retains start/end page provenance.
- Scanned PDF invokes OCR fallback and records OCR warning/confidence.
- Ambiguous boundaries are flagged for review.
- Fixture-level expected questions are all present; no silent drops.
- DOCX paragraphs and tables are extracted in document order.

## 3. Question editing
- User edits persist without destroying original extracted wording.
- Reordering changes display/export order.
- Duplicate detection only suggests; it never deletes automatically.
- Processing cannot start while document extraction is in an unresolved review state unless user explicitly confirms.

## 4. Generation and schema
- 2-mark definition is concise and schema-valid.
- 10-mark multi-part explanation covers all subparts.
- Formula/calculation answer preserves mathematical notation.
- Malformed JSON, missing required fields, extra fields, and empty model output are handled safely.
- Prompt injection text inside uploaded document does not override system instructions.
- Provider/model/prompt version/token/latency metadata is recorded.

## 5. Verification and revision
- Correct complete answer can be approved.
- An approved report missing a required criterion, duplicating a criterion, or containing a failed/uncertain criterion is rejected.
- A human approval or rejection is recorded against the exact answer version and does not alter the verifier report.
- Omitted sub-question is flagged with actionable feedback.
- Controlled incorrect formula/calculation is flagged.
- Refiner addresses required issues and returns full answer.
- A second unsuccessful revision leads to `MANUAL_REVIEW`.
- Network timeout and rate-limit retries do not increment revision count.
- Verifier report references the exact answer version checked.
- No approval is possible without a valid approved verifier report.
- All versions remain available and immutable.

## 6. Queue and reliability
- Multiple questions process concurrently up to configured limits.
- Provider rate limits and global concurrency are respected.
- Repeated job creation with same idempotency key creates one logical job.
- Reusing a project-scoped idempotency key with a different document or selection returns `409` and creates no extra jobs.
- Duplicate Celery delivery does not duplicate answer versions.
- Worker restart recovers expired leases.
- Cancellation stops future model calls where possible and marks job `CANCELLED`.
- One question failure does not stop sibling questions.

## 7. API and UI
- API responses match `api.md`.
- SSE emits ordered state events with event IDs; reconnect can resume or fall back to polling.
- Dashboard counts match database states.
- Filters work by unit, marks, and status.
- User can inspect report/history and edit/approve/regenerate.
- Failed/manual-review/cancelled states are distinguishable.

## 8. Export
- PDF, DOCX, Markdown, and JSON are valid and downloadable by owner only.
- Unit/question ordering is preserved.
- Every selected question appears exactly once.
- Unicode, formulas, and special characters render safely.
- Long answers paginate correctly.
- Unapproved answers are excluded by default or visibly labeled when included.

## 9. Security
- Secrets are absent from frontend bundles and logs.
- Upload size/type checks cannot be bypassed by renaming.
- HTML/script payloads in extracted text are escaped in UI/export.
- Rate limits and per-user quotas are enforced.
- Private storage keys are not exposed as permanent public URLs.

## 10. Release gates
- No silent question loss on the labeled extraction fixtures.
- No cross-user access.
- No unbounded concurrency, retries, or revision loops.
- All export formats pass validation.
- Failed jobs are visible and recoverable.
- Human reviewers rate the evaluation set as acceptable for the intended study use.
