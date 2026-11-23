# Security and Privacy Requirements

## Authentication and authorization
- Require authentication for all project, document, question, job, answer, and export endpoints.
- Enforce ownership on every read, write, download, event stream, and background task.
- Workers must re-check resource ownership/scope from persisted job relationships; never trust user IDs supplied in task payloads alone.
- Use secure password hashing or a trusted identity provider. Protect session cookies with HttpOnly, Secure, and appropriate SameSite settings.

## File upload and parsing
- Allow only PDF and DOCX in the MVP.
- Validate extension, MIME signature, file structure, and configurable size limit (default 30 MB).
- Generate server-side storage names; never use user filenames as filesystem paths.
- Store originals outside the public web root/private object storage.
- Apply parser timeouts and resource limits. Consider malware scanning in production.
- Treat extracted text, embedded links, images, and document metadata as untrusted.

## Prompt injection and model safety
- Delimit uploaded question/reference text as untrusted data.
- Never allow document text to change system/developer instructions, tools, permissions, or secrets.
- Do not give the model direct database, filesystem, or arbitrary network tools.
- Validate all model outputs against strict schemas.
- Render Mermaid or other diagram content safely; do not execute arbitrary HTML/JS.
- Do not present model verification as a guarantee.

## Secrets and logging
- Keep provider keys and auth secrets on the server.
- Use environment/secret management; never commit `.env`.
- Redact credentials, signed URLs, and sensitive user content from logs.
- Log correlation IDs, error codes, model metadata, latency, and token usage instead of full prompts/documents by default.

## Abuse controls
- Enforce per-user upload, processing, and export quotas.
- Bound concurrent model calls, request size, retries, and timeouts.
- Add rate limiting to upload, process, regenerate, and authentication endpoints.
- Protect against denial-of-service through oversized files or pathological PDFs.

## Data lifecycle
- Use private storage and short-lived download links.
- Delete original uploads no later than 30 days after upload and exports 7 days after creation. Keep project questions and answers until the user deletes the project.
- Delete project content and active storage objects on user request; expire deleted content from rolling backups within 30 days. Keep operational metadata logs for 30 days and do not retain raw prompts/model responses by default.
- Send content only to configured providers that do not use it for training and disclose retention of no more than 30 days. Do not route content to providers whose terms cannot be confirmed.
- Backups must be access-controlled and expire within 30 days.

## Security acceptance checks
- Cross-user access tests pass for every resource type.
- No secrets appear in frontend bundles, source control, or logs.
- Upload validation cannot be bypassed by renaming a file.
- HTML/script content from documents is escaped in the UI and exports.
