# Engineering Rules

## Code quality
- Use TypeScript strict mode in the frontend.
- Use Python type hints and Pydantic validation in the backend.
- Format/lint automatically; add tests for every business rule.
- Keep modules cohesive and avoid circular dependencies.
- Centralize configuration and validate required environment variables at startup.

## Contracts
- `schemas.md` is the single source of truth for answer and verification JSON.
- `api.md` is the source of truth for endpoint behavior.
- Do not duplicate schema definitions manually across services; generate or share them where practical.
- Version prompts and record the version on every model call.

## Processing
- Each question is processed independently.
- Enforce a maximum of two answer revisions.
- Operational retries do not count as revisions.
- Store every answer version; never overwrite history.
- Queue delivery must be idempotent and concurrency-safe.
- A worker must not mark a question `VERIFIER_APPROVED` without a valid approved verifier report for that exact answer version.
- A human approval is an append-only decision tied to an answer version, actor, and timestamp; it never changes or overwrites the verifier verdict.
- Export by default only versions with a verifier approval or latest human approval. A latest human rejection excludes that version; included drafts and manual-review answers must be labeled.

## Data and security
- Treat uploaded text as untrusted input.
- Enforce ownership checks on every resource access.
- Never expose secrets to the browser or logs.
- Keep uploads and exports private.
- Do not fabricate citations or source locations.

## User experience
- Display extraction uncertainty and processing failures clearly.
- Show approved, manual-review, failed, and cancelled states distinctly.
- Allow users to edit and approve answers.
- Do not hide unapproved answers in exports; clearly label them if included.
