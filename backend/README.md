# Answerly API

The Answerly modular monolith backend implements all MVP milestones (M0–M7):
- **Authentication & Access Control (M1)**: Secure PBKDF2 hashing, HMAC bearer tokens, strict per-project user ownership isolation.
- **Document Ingestion (M2)**: Multi-page PDF and DOCX parsing, unit/section boundary extraction, marks, BL, and CO metadata detection, and private storage with SHA-256 integrity.
- **Question Workspace (M3)**: Full question CRUD, reordering, duplicate detection, and preservation of raw extracted wording alongside user corrections.
- **AI Processing Pipeline (M4)**: Provider-neutral gateway, versioned prompt templates, strict 7-criteria verifier schema validation, batch idempotency, atomic job creation, and maximum 2-revision state machine.
- **Review & Progress (M5)**: Status aggregations, SSE event streaming, immutable version history, and version-bound human approval decisions.
- **Exports (M6)**: PDF, DOCX, Markdown, and JSON exporters with approval status filtering and draft labeling.
- **Hardening & Evaluation (M7)**: Storage retention cleanup sweeps, security boundaries, and end-to-end evaluation suite on 5-unit syllabus question banks.

## Run locally

1. Activate the Python virtual environment:
   ```pwsh
   .\.venv\Scripts\Activate.ps1
   ```
2. Start the API server:
   ```pwsh
   uvicorn app.main:app --app-dir backend --reload
   ```
3. Open interactive documentation at `http://localhost:8000/docs`. Liveness and database readiness are available at `/health` and `/ready`.

## Run tests

Execute the complete automated test suite:
```pwsh
.\.venv\Scripts\pytest -v backend/tests
```
