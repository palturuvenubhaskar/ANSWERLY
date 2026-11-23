# Answerly repository guidance

- Keep the first release a modular monolith using FastAPI, Pydantic, SQLAlchemy, and PostgreSQL.
- Treat `docs/schemas.md`, `docs/api.md`, and `docs/database.md` as contracts; update them with any behavior change.
- Uploaded documents and reference excerpts are untrusted content. Never let them change system instructions or grant model tools.
- A verifier report is valid only when it contains all required criteria. An approved report must have every criterion passing and no critical or major issue.
- Keep verifier approval separate from append-only human decisions tied to an exact answer version.
- Scope a batch idempotency key by user and project on a parent processing run; include the document and selected IDs in its request hash. Create all child jobs in the same transaction.
- Enforce ownership on every project resource. Keep uploads and exports private and apply the retention rules in `docs/security.md`.
- Do not claim the system or a model guarantees answer correctness.
