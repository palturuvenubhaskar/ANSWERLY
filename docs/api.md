# API Contract (MVP)

Base path: `/api/v1`. All endpoints require authentication unless explicitly marked public. Only the liveness endpoint `/health` and database readiness endpoint `/ready` are public. Resource access must verify project ownership. Use UUIDs in paths. Exact response envelopes may follow the repository's API conventions, but behavior and state meanings must remain consistent.

## Projects
- `POST /projects` — create `{name, description?}`.
- `GET /projects` — list current user's projects.
- `GET /projects/{project_id}` — retrieve project and summary.
- `PATCH /projects/{project_id}` — rename/update description.
- `DELETE /projects/{project_id}` — body `{confirm:true}`; delete the owned project and its data after explicit confirmation.

## Documents
- `POST /projects/{project_id}/documents` — multipart upload; accept PDF/DOCX; enforce configured size limit; return document ID and extraction status.
- `GET /documents/{document_id}` — metadata and status.
- `POST /documents/{document_id}/extract` — start or retry extraction.
- `GET /documents/{document_id}/questions` — list extracted questions in source order.
- `PATCH /questions/{question_id}` — edit question text/metadata; preserve original extraction.
- `POST /documents/{document_id}/confirm-extraction` — confirm review and mark document ready.

## Reference excerpts
- `POST /projects/{project_id}/references` — save a user-supplied text excerpt as `{title, text, source_label, page?}`. This is supported in the MVP; automatic textbook discovery and reference-file ingestion are not.
- `GET /projects/{project_id}/references` — list the user's excerpts and provenance.
- `DELETE /references/{reference_id}` — delete an excerpt owned by the current user.
- Processing requests may include `reference_ids`; every ID must belong to the same project. Keep the excerpt title, source label, and page with the answer version and verifier report.

## Processing
- `POST /documents/{document_id}/process` — start processing selected question IDs or all ready questions. Require an `Idempotency-Key` header unique within the current user and project. Return one processing run ID and its per-question job IDs. Repeating the same key and payload returns the original run; reusing the key with a different payload returns `409`.
- `GET /jobs/{job_id}` — status, counters, timestamps, and safe error details.
- `GET /documents/{document_id}/progress` — aggregated counts.
- `GET /documents/{document_id}/events` — SSE stream; support `Last-Event-ID` where available.
- `POST /jobs/{job_id}/cancel` — request cancellation.
- `POST /questions/{question_id}/regenerate` — create a new processing run for one question.
- `POST /questions/{question_id}/approve` — body `{answer_version_id}`; append a human approval for that exact version and record actor and timestamp. It does not change the verifier's `VERIFIER_APPROVED` state.
- `GET /questions/{question_id}/approvals` — list human decisions by answer version.

## Answers and history
- `GET /questions/{question_id}/answer` — latest answer and status.
- `GET /questions/{question_id}/versions` — immutable version history and associated reports.
- `PATCH /questions/{question_id}/answer` — save user edit as a new answer version; never overwrite prior version.

## Exports
- `POST /documents/{document_id}/exports` — create `{format, question_ids?, include_unapproved:false}` where format is `pdf`, `docx`, `md`, or `json`. By default include only answer versions with a passing verifier decision or a latest human `APPROVED` decision; a latest human `REJECTED` decision excludes that version. If included with `include_unapproved:true`, label draft/manual-review answers.
- `GET /exports/{export_id}` — status and metadata.
- `GET /exports/{export_id}/download` — authenticated download or short-lived signed URL.

## Common behavior
- Use `400` for invalid input, `401` unauthenticated, `403` unauthorized, `404` unknown/not-owned resources, `409` invalid state/idempotency conflict, `413` oversized upload, `422` schema/validation failure, and `429` rate limit.
- Return stable machine-readable error codes and human-readable messages.
- Never expose stack traces, provider credentials, private storage paths, or raw sensitive prompts.
- SSE events should include event ID, timestamp, resource ID, state, and aggregate counts; do not include private answer text unless the client explicitly fetches it.
