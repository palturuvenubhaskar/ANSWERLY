# Development Setup

This guide describes the intended local setup. Exact commands may be adjusted to match the repository's pinned versions.

## Prerequisites
- Git
- Node.js LTS and package manager (pnpm recommended)
- Python 3.11+
- Docker and Docker Compose
- Tesseract OCR plus required language packs for OCR tests

## Suggested repository layout
```text
answerly/
  frontend/          # Next.js app
  backend/
    app/
      api/
      auth/
      projects/
      documents/
      extraction/
      questions/
      processing/
      ai_gateway/
      exports/
    tests/
  prompts/
  docs/              # project specification files
  docker-compose.yml
  .env.example
  AGENTS.md
```

## Services
Run PostgreSQL and Redis locally through Docker Compose. Use a private local directory for uploaded files during development. Production should use private object storage.

## Environment variables
Create `.env` from `.env.example`. Include database URL, Redis URL, auth secret, private storage configuration, model gateway API key, model names, request timeouts, concurrency limits, and upload size limit. Never commit `.env`.

Suggested configuration names:
- `DATABASE_URL`
- `REDIS_URL`
- `AUTH_SECRET`
- `STORAGE_BACKEND`
- `LOCAL_STORAGE_PATH`
- `OPENROUTER_API_KEY`
- `GENERATOR_MODEL`
- `VERIFIER_MODEL`
- `REFINER_MODEL`
- `MAX_UPLOAD_BYTES` (default 31457280)
- `MAX_WORKER_CONCURRENCY`
- `MODEL_TIMEOUT_SECONDS`

## Startup order
1. Start PostgreSQL and Redis.
2. Install backend dependencies and run Alembic migrations.
3. Start FastAPI.
4. Start Celery worker.
5. Install frontend dependencies and start Next.js.
6. Open the frontend and verify API/worker health.

## Local validation
Run backend unit/integration tests, frontend lint/type checks/tests, and a smoke test: create project → upload fixture → review extraction → process one question → inspect answer/report → export Markdown and PDF.

## OCR note
OCR is a fallback for pages with insufficient embedded text. Install Tesseract and language packs explicitly; do not assume they are bundled with PyMuPDF.
