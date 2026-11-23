# Database Design

Use PostgreSQL, SQLAlchemy, Alembic, and UUID primary keys. This is a logical design; exact column types and constraints should be implemented in migrations.

## Entity relationships
```text
User
 ├── Project
 │    ├── Document (versioned uploads)
 │    │    ├── Unit
 │    │    │    └── Question
 │    │    │         ├── AnswerVersion (immutable)
 │    │    │         ├── VerificationReport
 │    │    │         ├── ProcessingJob
 │    │    │         └── HumanApproval
 │    ├── ProcessingRun
 │    ├── ReferenceMaterial
 │    └── Export
 └── ModelCallAttempt (audit/cost metadata, scoped to job)
```

## Tables

### users
`id` UUID PK; `email` unique; `password_hash` or external auth subject; `created_at`; `updated_at`.

### projects
`id` UUID PK; `user_id` FK; `name`; `description` nullable; timestamps. Index `(user_id, updated_at)`.

### documents
`id` UUID PK; `project_id` FK; `version_number`; `title`; `original_filename`; `storage_key`; `mime_type`; `file_size_bytes`; `sha256`; `status` (`UPLOADED`, `EXTRACTING`, `REVIEW_REQUIRED`, `READY`, `FAILED`); `extraction_warnings` JSONB; timestamps. Unique `(project_id, version_number)`.

### units
`id` UUID PK; `document_id` FK; `name`; `position`; unique `(document_id, position)`.

### questions
`id` UUID PK; `document_id` FK; `unit_id` nullable FK; `question_number` nullable; `section` nullable; `question_text`; `marks` nullable positive integer; `bl` nullable; `co` nullable; `source_page_start`, `source_page_end`; `source_excerpt` nullable; `extraction_confidence` nullable numeric; `status` (`PENDING`, `QUEUED`, `GENERATING`, `VERIFYING`, `REVISING`, `RETRY_WAIT`, `VERIFIER_APPROVED`, `MANUAL_REVIEW`, `FAILED`, `CANCELLED`); `position`; timestamps. Index `(document_id, unit_id, position)` and `(document_id, status)`. Human approval is not stored in this status.

### reference_materials
`id` UUID PK; `project_id` FK; optional `document_id` FK; `title`; `storage_key`; `mime_type`; `extracted_text_location` or private text reference; `created_at`. Reference excerpts passed to a model must retain source/page provenance.

### answer_versions
`id` UUID PK; `question_id` FK; `version_number`; `answer_json` JSONB conforming to `AnswerContent`; `rendered_markdown` nullable; `provider`; `model`; `prompt_version`; `created_at`. Unique `(question_id, version_number)`. Treat rows as append-only.

### verification_reports
`id` UUID PK; `question_id` FK; `answer_version_id` FK; `verifier_provider`; `verifier_model`; `verdict`; `report_json` JSONB conforming to `VerificationReport`; `created_at`.

### processing_jobs
`id` UUID PK; `processing_run_id` FK; `question_id` FK; `job_type`; `status`; `generation_attempt_count`; `revision_count` (0–2); `retry_count`; `lease_owner` nullable; `lease_expires_at` nullable; `cancel_requested_at` nullable; `last_error_code` nullable; `last_error_message` nullable; `started_at`; `finished_at`; timestamps. Unique `(processing_run_id, question_id)`. A job does not duplicate the request idempotency key.

### processing_runs
`id` UUID PK; `project_id` FK; `user_id` FK; `idempotency_key`; `request_hash` (including document ID and selected question/reference IDs); selected `reference_ids`; `created_at`; timestamps. Unique `(user_id, project_id, idempotency_key)`. A retry with the same key and request hash returns this run; the same key with a different hash is a conflict. Create the run and all child jobs in one transaction.

### human_approvals
`id` UUID PK; `question_id` FK; `answer_version_id` FK; `user_id` FK; `decision` (`APPROVED`, `REJECTED`); `created_at`. Append-only. A new answer version requires a new decision.

### model_call_attempts
`id` UUID PK; `processing_job_id` FK; `role` (`GENERATOR`, `VERIFIER`, `REFINER`); provider/model; prompt version; input/output tokens nullable; latency_ms nullable; estimated_cost nullable; outcome; error_code nullable; created_at.

### exports
`id` UUID PK; `project_id` FK; `document_id` FK; `user_id` FK; `format` (`PDF`, `DOCX`, `MD`, `JSON`); `storage_key` nullable; `status`; `options_json` JSONB; `included_question_ids` JSONB; `created_at`; `finished_at`.

## Integrity and concurrency
- Every resource query must enforce ownership through project/user relationships.
- Add database constraints for valid enum states, positive marks, unique positions/version numbers, and revision count 0–2.
- Answer versions are immutable; manual edits create a new version with an `edited_by_user` audit marker. Human approvals reference the exact version and are separate from verifier verdicts.
- Save answer version and corresponding verification report in separate but transactionally consistent steps; a report must reference the exact version it checked.
- Scope request idempotency to `(user_id, project_id, idempotency_key)` on `processing_runs`; include the document ID and all selected IDs in the request hash, then create per-question jobs under that run. Use atomic job claiming/leases. Do not rely only on Celery task IDs.
- Deleting a project/document requires explicit confirmation and a documented retention policy. Apply deliberate cascade behavior.
