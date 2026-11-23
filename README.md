# Answerly

Answerly helps students turn question banks into organized, exam-oriented answers.

Both the FastAPI modular monolith backend and the Next.js frontend are implemented and production-ready:
- **Backend API**: Tested across all 8 architectural milestones (M0–M7), including PBKDF2 authentication, project and question workspace management, PDF/DOCX ingestion with PyMuPDF, prompt generation and 7-criteria verification pipelines with batch idempotency, human approval review, and multi-format exports (PDF, DOCX, Markdown, JSON).
- **Frontend App**: Built with Next.js 16 (App Router), TypeScript, and Tailwind CSS following the specialized `frontend-design` aesthetic principles. Features an intentional academic workspace layout with document ingestion, reference excerpts manager, live SSE progress monitoring, an answer review canvas with a 7-criteria verifier inspector, and an export center.

## Running Locally

### 1. Backend (FastAPI)
```pwsh
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --app-dir backend --reload --port 8000
```

### 2. Frontend (Next.js)
```pwsh
cd frontend
npm run dev
```
Open `http://localhost:3000` to interact with Answerly.

See [`backend/README.md`](backend/README.md) for backend details, [`docs/api.md`](docs/api.md) for the API specification, and [`docs/task.md`](docs/task.md) for milestone tracking.
