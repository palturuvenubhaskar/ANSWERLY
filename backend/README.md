# Answerly API foundation

This is the first runnable API slice: account registration/login, owned projects and questions, user-supplied reference excerpts, answer-version storage, verifier-report validation, and version-specific human decisions.

The background model worker, PDF/DOCX upload and extraction, browser interface, and exports are not implemented yet. Processing-run tables establish the parent-run and child-job constraints for safe batch idempotency; no run endpoint is exposed until a worker can execute those jobs.

## Run locally

1. Create and activate a Python virtual environment.
2. Install the root `requirements.txt`.
3. Copy `.env.example` to `.env`, replace `AUTH_SECRET` with a unique secret, and start PostgreSQL with `docker compose up -d postgres`.
4. Run `uvicorn app.main:app --app-dir backend --reload`.
5. Open `/docs`; liveness and database readiness are available at `/health` and `/ready`.

For a quick local-only run without PostgreSQL, leave `DATABASE_URL` unset to use SQLite. The API generates a temporary auth secret if `AUTH_SECRET` is missing in development; sessions expire when that process restarts.
