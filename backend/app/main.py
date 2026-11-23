import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .duplicates import find_duplicates
from .exports import generate_export
from .extraction import extract_document, validate_file_content
from .models import (
    AnswerVersion,
    Document,
    Export,
    HumanApproval,
    ModelCallAttempt,
    ProcessingJob,
    ProcessingRun,
    Project,
    Question,
    ReferenceExcerpt,
    Unit,
    User,
    VerificationReportRecord,
    utc_now,
)
from .pipeline import execute_job

try:
    from .tasks import execute_job_task
    _CELERY_AVAILABLE = True
except Exception:
    _CELERY_AVAILABLE = False
from .schemas import (
    AnswerCreate,
    DeleteProjectRequest,
    DocumentResponse,
    ExportCreate,
    HumanApprovalCreate,
    LoginRequest,
    ProcessingJobResponse,
    ProcessingRunCreate,
    ProcessingRunResponse,
    ProjectCreate,
    ProjectUpdate,
    QuestionCreate,
    QuestionItemResponse,
    QuestionReorderRequest,
    QuestionUpdate,
    ReferenceExcerptCreate,
    RegisterRequest,
    VerificationReport,
)
from .storage import storage_service

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 31457280))
MAX_DOCS_PER_USER = int(os.getenv("MAX_DOCS_PER_USER", 100))
MAX_EXPORTS_PER_USER = int(os.getenv("MAX_EXPORTS_PER_USER", 100))
MAX_ACTIVE_JOBS_PER_USER = int(os.getenv("MAX_ACTIVE_JOBS_PER_USER", 50))
USE_CELERY = os.getenv("USE_CELERY", "false").lower() in ("true", "1", "yes")

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["300/minute"],
    enabled=os.getenv("RATE_LIMIT_ENABLED", "false").lower() in ("true", "1", "yes"),
)

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(message)s")
logger = logging.getLogger("answerly")
APP_ENV = os.getenv("APP_ENV", "development")
AUTH_SECRET = os.getenv("AUTH_SECRET")
if APP_ENV == "production" and not AUTH_SECRET:
    raise RuntimeError("AUTH_SECRET must be set in production")
if APP_ENV == "production" and len(AUTH_SECRET) < 32:
    raise RuntimeError("AUTH_SECRET must contain at least 32 characters in production")
if not AUTH_SECRET:
    AUTH_SECRET = secrets.token_urlsafe(48)
    logger.warning(json.dumps({"event": "ephemeral_auth_secret", "message": "Set AUTH_SECRET to keep sessions valid across restarts."}))

bearer = HTTPBearer(auto_error=False)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Tables are managed by Alembic migrations.
    # In development, auto-create any missing tables for convenience.
    if APP_ENV != "production":
        Base.metadata.create_all(bind=engine)
    logger.info(json.dumps({"event": "application_started", "environment": APP_ENV}))
    yield


app = FastAPI(title="Answerly API", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _issue_token(user_id: str) -> str:
    expires = int(time.time()) + 8 * 60 * 60
    payload = _b64(f"{user_id}:{expires}".encode("utf-8"))
    signature = _b64(hmac.new(AUTH_SECRET.encode("utf-8"), payload.encode("ascii"), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def _decode_token(token: str) -> str:
    try:
        payload, signature = token.split(".", 1)
        expected = _b64(hmac.new(AUTH_SECRET.encode("utf-8"), payload.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")
        raw = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)).decode("utf-8")
        user_id, expires = raw.rsplit(":", 1)
        if int(expires) <= int(time.time()):
            raise ValueError("expired token")
        return user_id
    except (ValueError, UnicodeDecodeError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired bearer token", headers={"WWW-Authenticate": "Bearer"}) from exc


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 310_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_b64(salt)}${_b64(digest)}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_text, digest_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text + "=" * (-len(salt_text) % 4))
        expected = base64.urlsafe_b64decode(digest_text + "=" * (-len(digest_text) % 4))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer token required", headers={"WWW-Authenticate": "Bearer"})
    user_id = _decode_token(credentials.credentials)
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired bearer token", headers={"WWW-Authenticate": "Bearer"})
    return user


def _owned_project(db: Session, project_id: str, user_id: str) -> Project:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.user_id == user_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _owned_question(db: Session, question_id: str, user_id: str) -> Question:
    question = db.scalar(
        select(Question)
        .join(Project, Question.project_id == Project.id)
        .where(Question.id == question_id, Project.user_id == user_id)
    )
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


def _owned_document(db: Session, document_id: str, user_id: str) -> Document:
    doc = db.scalar(
        select(Document)
        .join(Project, Document.project_id == Project.id)
        .where(Document.id == document_id, Project.user_id == user_id)
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


def _owned_job(db: Session, job_id: str, user_id: str) -> ProcessingJob:
    job = db.scalar(
        select(ProcessingJob)
        .join(ProcessingRun, ProcessingJob.processing_run_id == ProcessingRun.id)
        .where(ProcessingJob.id == job_id, ProcessingRun.user_id == user_id)
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Processing job not found")
    return job


def _owned_export(db: Session, export_id: str, user_id: str) -> Export:
    export = db.scalar(select(Export).where(Export.id == export_id, Export.user_id == user_id))
    if export is None:
        raise HTTPException(status_code=404, detail="Export not found")
    return export


def _valid_email(value: str) -> str:
    email = value.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+", email):
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    return email


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error(json.dumps({"event": "readiness_failed", "error_type": type(exc).__name__}))
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc
    return {"status": "ready"}


@app.post("/api/v1/auth/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    email = _valid_email(body.email)
    if db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(email=email, password_hash=_hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists") from exc
    db.refresh(user)
    return {"user_id": user.id, "access_token": _issue_token(user.id), "token_type": "bearer", "expires_in": 28800}


@app.post("/api/v1/auth/login")
@limiter.limit("20/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    email = _valid_email(body.email)
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if user is None or not _verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    return {"user_id": user.id, "access_token": _issue_token(user.id), "token_type": "bearer", "expires_in": 28800}


@app.post("/api/v1/projects", status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = Project(user_id=user.id, name=body.name, description=body.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return {"id": project.id, "name": project.name, "description": project.description}


@app.get("/api/v1/projects")
def list_projects(user: User = Depends(current_user), db: Session = Depends(get_db)):
    projects = db.scalars(select(Project).where(Project.user_id == user.id).order_by(Project.created_at.desc())).all()
    return [{"id": project.id, "name": project.name, "description": project.description} for project in projects]


@app.get("/api/v1/projects/{project_id}")
def get_project(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = _owned_project(db, project_id, user.id)
    question_count = db.scalar(select(func.count(Question.id)).where(Question.project_id == project.id)) or 0
    reference_count = db.scalar(select(func.count(ReferenceExcerpt.id)).where(ReferenceExcerpt.project_id == project.id)) or 0
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "created_at": project.created_at,
        "question_count": question_count,
        "reference_count": reference_count,
    }


@app.patch("/api/v1/projects/{project_id}")
def update_project(
    project_id: str,
    body: ProjectUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    project = _owned_project(db, project_id, user.id)
    if body.name is not None:
        project.name = body.name
    if body.description is not None:
        project.description = body.description
    db.commit()
    db.refresh(project)
    return {"id": project.id, "name": project.name, "description": project.description}


@app.delete("/api/v1/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    body: DeleteProjectRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not body.confirm:
        raise HTTPException(status_code=400, detail="Set confirm to true to delete this project")
    project = _owned_project(db, project_id, user.id)
    db.delete(project)
    db.commit()


@app.post("/api/v1/projects/{project_id}/documents", status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def upload_document(
    project_id: str,
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    project = _owned_project(db, project_id, user.id)

    # Enforce per-user upload quota
    user_doc_count = db.scalar(
        select(func.count(Document.id))
        .join(Project, Document.project_id == Project.id)
        .where(Project.user_id == user.id)
    ) or 0
    if user_doc_count >= MAX_DOCS_PER_USER:
        raise HTTPException(status_code=400, detail=f"User document quota exceeded (maximum {MAX_DOCS_PER_USER} documents)")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds maximum upload size of {MAX_UPLOAD_BYTES} bytes")

    try:
        ext, mime_type = validate_file_content(content, file.filename or "")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    stored = storage_service.save(content, extension=ext)

    last_version = db.scalar(select(func.max(Document.version_number)).where(Document.project_id == project.id)) or 0
    doc = Document(
        project_id=project.id,
        version_number=last_version + 1,
        title=file.filename or f"Document {last_version + 1}",
        original_filename=file.filename or f"document{ext}",
        storage_key=stored.storage_key,
        mime_type=mime_type,
        file_size_bytes=stored.size_bytes,
        sha256=stored.sha256,
        status="EXTRACTING",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        ext_res = extract_document(content, file.filename or "")
        unit_map = {}
        for u_idx, u_name in enumerate(ext_res.units):
            unit = Unit(document_id=doc.id, name=u_name, position=u_idx + 1)
            db.add(unit)
            db.flush()
            unit_map[u_name] = unit.id

        last_pos = db.scalar(select(func.max(Question.position)).where(Question.project_id == project.id)) or 0
        for q_idx, q in enumerate(ext_res.questions):
            u_id = unit_map.get(q.unit_name) if q.unit_name else None
            question = Question(
                project_id=project.id,
                document_id=doc.id,
                unit_id=u_id,
                question_number=q.question_number,
                section=q.section,
                question_text=q.question_text,
                original_text=q.original_text,
                marks=q.marks,
                bl=q.bl,
                co=q.co,
                source_page_start=q.source_page_start,
                source_page_end=q.source_page_end,
                source_excerpt=q.source_excerpt,
                extraction_confidence=q.confidence,
                position=last_pos + q_idx + 1,
                status="PENDING",
            )
            db.add(question)
        doc.extraction_warnings = ext_res.warnings
        doc.status = "REVIEW_REQUIRED" if ext_res.warnings or ext_res.questions else "READY"
    except Exception as exc:
        doc.status = "FAILED"
        doc.extraction_warnings = [f"Extraction failed: {exc}"]

    db.commit()
    db.refresh(doc)
    return {
        "id": doc.id,
        "project_id": doc.project_id,
        "title": doc.title,
        "original_filename": doc.original_filename,
        "file_size_bytes": doc.file_size_bytes,
        "mime_type": doc.mime_type,
        "sha256": doc.sha256,
        "status": doc.status,
        "extraction_warnings": doc.extraction_warnings,
    }


@app.get("/api/v1/documents/{document_id}")
def get_document(document_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc = _owned_document(db, document_id, user.id)
    return {
        "id": doc.id,
        "project_id": doc.project_id,
        "title": doc.title,
        "original_filename": doc.original_filename,
        "file_size_bytes": doc.file_size_bytes,
        "mime_type": doc.mime_type,
        "sha256": doc.sha256,
        "status": doc.status,
        "extraction_warnings": doc.extraction_warnings,
    }


@app.post("/api/v1/documents/{document_id}/extract")
def retry_extraction(document_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc = _owned_document(db, document_id, user.id)
    content = storage_service.get(doc.storage_key)

    # Clean previous units and questions for this document
    db.query(Question).filter(Question.document_id == doc.id).delete(synchronize_session=False)
    db.query(Unit).filter(Unit.document_id == doc.id).delete(synchronize_session=False)

    try:
        ext_res = extract_document(content, doc.original_filename)
        unit_map = {}
        for u_idx, u_name in enumerate(ext_res.units):
            unit = Unit(document_id=doc.id, name=u_name, position=u_idx + 1)
            db.add(unit)
            db.flush()
            unit_map[u_name] = unit.id

        last_pos = db.scalar(select(func.max(Question.position)).where(Question.project_id == doc.project_id)) or 0
        for q_idx, q in enumerate(ext_res.questions):
            u_id = unit_map.get(q.unit_name) if q.unit_name else None
            question = Question(
                project_id=doc.project_id,
                document_id=doc.id,
                unit_id=u_id,
                question_number=q.question_number,
                section=q.section,
                question_text=q.question_text,
                original_text=q.original_text,
                marks=q.marks,
                bl=q.bl,
                co=q.co,
                source_page_start=q.source_page_start,
                source_page_end=q.source_page_end,
                source_excerpt=q.source_excerpt,
                extraction_confidence=q.confidence,
                position=last_pos + q_idx + 1,
                status="PENDING",
            )
            db.add(question)
        doc.extraction_warnings = ext_res.warnings
        doc.status = "REVIEW_REQUIRED" if ext_res.warnings or ext_res.questions else "READY"
    except Exception as exc:
        doc.status = "FAILED"
        doc.extraction_warnings = [f"Extraction failed: {exc}"]

    db.commit()
    db.refresh(doc)
    return {
        "id": doc.id,
        "status": doc.status,
        "extraction_warnings": doc.extraction_warnings,
    }


@app.get("/api/v1/documents/{document_id}/questions")
def list_document_questions(document_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc = _owned_document(db, document_id, user.id)
    questions = db.scalars(
        select(Question).where(Question.document_id == doc.id).order_by(Question.position.asc())
    ).all()
    return [
        {
            "id": q.id,
            "position": q.position,
            "question_number": q.question_number,
            "section": q.section,
            "question_text": q.question_text,
            "original_text": q.original_text,
            "marks": q.marks,
            "bl": q.bl,
            "co": q.co,
            "source_page_start": q.source_page_start,
            "source_page_end": q.source_page_end,
            "extraction_confidence": q.extraction_confidence,
            "status": q.status,
        }
        for q in questions
    ]


@app.post("/api/v1/documents/{document_id}/confirm-extraction")
def confirm_extraction(document_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc = _owned_document(db, document_id, user.id)
    doc.status = "READY"
    db.commit()
    return {"id": doc.id, "status": doc.status}


@app.post("/api/v1/documents/{document_id}/process", status_code=status.HTTP_201_CREATED)
def start_processing(
    document_id: str,
    body: ProcessingRunCreate,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")

    doc = _owned_document(db, document_id, user.id)
    if doc.status != "READY":
        raise HTTPException(
            status_code=400,
            detail="Document extraction must be confirmed before processing can start",
        )

    # Determine question IDs
    if body.question_ids:
        q_count = db.scalar(
            select(func.count(Question.id)).where(
                Question.id.in_(body.question_ids), Question.document_id == doc.id
            )
        )
        if q_count != len(body.question_ids):
            raise HTTPException(status_code=400, detail="All question_ids must belong to the specified document")
        q_ids = body.question_ids
    else:
        q_ids = db.scalars(
            select(Question.id).where(Question.document_id == doc.id).order_by(Question.position.asc())
        ).all()
        if not q_ids:
            raise HTTPException(status_code=400, detail="No questions found in this document to process")

    # Determine reference IDs
    if body.reference_ids:
        r_count = db.scalar(
            select(func.count(ReferenceExcerpt.id)).where(
                ReferenceExcerpt.id.in_(body.reference_ids), ReferenceExcerpt.project_id == doc.project_id
            )
        )
        if r_count != len(body.reference_ids):
            raise HTTPException(status_code=400, detail="All reference_ids must belong to the same project")
        ref_ids = body.reference_ids
    else:
        ref_ids = []

    # Calculate request hash
    req_hash = hashlib.sha256(f"{doc.id}:{sorted(q_ids)}:{sorted(ref_ids)}".encode("utf-8")).hexdigest()

    # Scope idempotency key by user and project
    existing_run = db.scalar(
        select(ProcessingRun).where(
            ProcessingRun.user_id == user.id,
            ProcessingRun.project_id == doc.project_id,
            ProcessingRun.idempotency_key == idempotency_key,
        )
    )

    if existing_run:
        if existing_run.request_hash == req_hash:
            # Idempotent response
            jobs = db.scalars(select(ProcessingJob).where(ProcessingJob.processing_run_id == existing_run.id)).all()
            return {
                "id": existing_run.id,
                "project_id": existing_run.project_id,
                "idempotency_key": existing_run.idempotency_key,
                "jobs": [
                    {
                        "id": j.id,
                        "question_id": j.question_id,
                        "status": j.status,
                        "revision_count": j.revision_count,
                        "retry_count": j.retry_count,
                    }
                    for j in jobs
                ],
            }
        else:
            raise HTTPException(
                status_code=409,
                detail="Idempotency key conflict: reused with different questions/references",
            )

    # Check concurrency quota
    active_jobs = db.scalar(
        select(func.count(ProcessingJob.id))
        .join(ProcessingRun, ProcessingJob.processing_run_id == ProcessingRun.id)
        .where(
            ProcessingRun.user_id == user.id,
            ProcessingJob.status.in_(["QUEUED", "GENERATING", "VERIFYING", "REVISING"]),
        )
    ) or 0
    if active_jobs + len(q_ids) > MAX_ACTIVE_JOBS_PER_USER:
        raise HTTPException(
            status_code=429,
            detail=f"Concurrency quota exceeded: active jobs ({active_jobs}) + requested ({len(q_ids)}) exceeds limit of {MAX_ACTIVE_JOBS_PER_USER}",
        )

    # Create run and child jobs in a single transaction
    new_run = ProcessingRun(
        user_id=user.id,
        project_id=doc.project_id,
        idempotency_key=idempotency_key,
        request_hash=req_hash,
        reference_ids=ref_ids,
    )
    db.add(new_run)
    db.flush()

    jobs_out = []
    for q_id in q_ids:
        job = ProcessingJob(
            processing_run_id=new_run.id,
            question_id=q_id,
            status="QUEUED",
        )
        db.add(job)
        db.flush()
        jobs_out.append(
            {
                "id": job.id,
                "question_id": job.question_id,
                "status": job.status,
                "revision_count": job.revision_count,
                "retry_count": job.retry_count,
            }
        )
        q_obj = db.get(Question, q_id)
        if q_obj:
            q_obj.status = "QUEUED"

    db.commit()
    db.refresh(new_run)

    # Dispatch jobs to Celery workers if enabled
    if _CELERY_AVAILABLE and USE_CELERY:
        for j_info in jobs_out:
            try:
                execute_job_task.delay(j_info["id"])
            except Exception as e:
                logger.warning(f"Could not enqueue job {j_info['id']} to Celery: {e}")

    return {
        "id": new_run.id,
        "project_id": new_run.project_id,
        "idempotency_key": new_run.idempotency_key,
        "jobs": jobs_out,
    }


@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    job = _owned_job(db, job_id, user.id)
    return {
        "id": job.id,
        "processing_run_id": job.processing_run_id,
        "question_id": job.question_id,
        "status": job.status,
        "revision_count": job.revision_count,
        "retry_count": job.retry_count,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "cancel_requested_at": job.cancel_requested_at,
        "last_error_code": job.last_error_code,
        "last_error_message": job.last_error_message,
    }


@app.post("/api/v1/jobs/{job_id}/cancel")
def cancel_job_endpoint(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    job = _owned_job(db, job_id, user.id)
    job.cancel_requested_at = utc_now()
    if job.status in ("QUEUED", "PENDING"):
        job.status = "CANCELLED"
        q = db.get(Question, job.question_id)
        if q:
            q.status = "CANCELLED"
    db.commit()
    return {"id": job.id, "status": job.status, "cancel_requested": True}


@app.post("/api/v1/jobs/{job_id}/execute")
def execute_job_endpoint(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _owned_job(db, job_id, user.id)
    updated_job = execute_job(job_id, db)
    return {
        "id": updated_job.id,
        "status": updated_job.status,
        "revision_count": updated_job.revision_count,
        "finished_at": updated_job.finished_at,
    }


@app.post("/api/v1/questions/{question_id}/regenerate", status_code=status.HTTP_201_CREATED)
def regenerate_question(
    question_id: str,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    question = _owned_question(db, question_id, user.id)
    key = idempotency_key or f"regen-{secrets.token_hex(16)}"
    req_hash = hashlib.sha256(f"regen:{question.id}".encode("utf-8")).hexdigest()

    run = ProcessingRun(
        user_id=user.id,
        project_id=question.project_id,
        idempotency_key=key,
        request_hash=req_hash,
        reference_ids=[],
    )
    db.add(run)
    db.flush()

    job = ProcessingJob(
        processing_run_id=run.id,
        question_id=question.id,
        status="QUEUED",
    )
    db.add(job)
    question.status = "QUEUED"
    db.commit()
    db.refresh(job)

    # Dispatch to Celery if available and enabled
    if _CELERY_AVAILABLE and USE_CELERY:
        try:
            execute_job_task.delay(job.id)
        except Exception as e:
            logger.warning(f"Could not enqueue regen job {job.id} to Celery: {e}")

    return {"run_id": run.id, "job_id": job.id, "status": job.status}


@app.post("/api/v1/projects/{project_id}/questions", status_code=status.HTTP_201_CREATED)
def create_question(
    project_id: str,
    body: QuestionCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    project = _owned_project(db, project_id, user.id)
    last_position = db.scalar(select(func.max(Question.position)).where(Question.project_id == project.id)) or 0
    question = Question(
        project_id=project.id,
        question_text=body.question_text,
        original_text=body.question_text,
        marks=body.marks,
        position=last_position + 1,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return {"id": question.id, "question_text": question.question_text, "marks": question.marks, "position": question.position}


@app.get("/api/v1/questions/{question_id}")
def get_question(question_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = _owned_question(db, question_id, user.id)
    return {
        "id": q.id,
        "project_id": q.project_id,
        "document_id": q.document_id,
        "unit_id": q.unit_id,
        "question_number": q.question_number,
        "section": q.section,
        "question_text": q.question_text,
        "original_text": q.original_text,
        "marks": q.marks,
        "bl": q.bl,
        "co": q.co,
        "source_page_start": q.source_page_start,
        "source_page_end": q.source_page_end,
        "source_excerpt": q.source_excerpt,
        "extraction_confidence": q.extraction_confidence,
        "position": q.position,
        "status": q.status,
    }


@app.patch("/api/v1/questions/{question_id}")
def update_question(
    question_id: str,
    body: QuestionUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    q = _owned_question(db, question_id, user.id)
    if body.question_text is not None:
        q.question_text = body.question_text
    if body.marks is not None:
        q.marks = body.marks
    if body.bl is not None:
        q.bl = body.bl
    if body.co is not None:
        q.co = body.co
    if body.position is not None:
        q.position = body.position
    # Note: q.original_text is intentionally preserved and NOT overwritten!
    db.commit()
    db.refresh(q)
    return {
        "id": q.id,
        "question_text": q.question_text,
        "original_text": q.original_text,
        "marks": q.marks,
        "bl": q.bl,
        "co": q.co,
        "position": q.position,
        "status": q.status,
    }


@app.delete("/api/v1/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(question_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = _owned_question(db, question_id, user.id)
    db.delete(q)
    db.commit()


@app.post("/api/v1/documents/{document_id}/questions/reorder")
def reorder_document_questions(
    document_id: str,
    body: QuestionReorderRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    _owned_document(db, document_id, user.id)
    questions = db.scalars(select(Question).where(Question.document_id == document_id)).all()
    q_map = {q.id: q for q in questions}

    if set(body.ordered_question_ids) != set(q_map.keys()):
        raise HTTPException(status_code=400, detail="Reorder list must contain all document question IDs exactly once")

    for idx, q_id in enumerate(body.ordered_question_ids):
        q_map[q_id].position = idx + 1

    db.commit()
    return {"status": "reordered", "count": len(body.ordered_question_ids)}


@app.get("/api/v1/documents/{document_id}/duplicates")
def get_document_duplicates(document_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _owned_document(db, document_id, user.id)
    questions = db.scalars(
        select(Question).where(Question.document_id == document_id).order_by(Question.position.asc())
    ).all()
    q_dicts = [{"id": q.id, "question_text": q.question_text} for q in questions]
    duplicates = find_duplicates(q_dicts)
    return [
        {
            "question_id_1": d.question_id_1,
            "question_id_2": d.question_id_2,
            "text_1": d.text_1,
            "text_2": d.text_2,
            "similarity": d.similarity,
            "reason": d.reason,
        }
        for d in duplicates
    ]


@app.post("/api/v1/projects/{project_id}/references", status_code=status.HTTP_201_CREATED)
def create_reference(
    project_id: str,
    body: ReferenceExcerptCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    project = _owned_project(db, project_id, user.id)
    excerpt = ReferenceExcerpt(
        project_id=project.id,
        title=body.title,
        text=body.text,
        source_label=body.source_label,
        page=body.page,
    )
    db.add(excerpt)
    db.commit()
    db.refresh(excerpt)
    return {"id": excerpt.id, "title": excerpt.title, "source_label": excerpt.source_label, "page": excerpt.page}


@app.get("/api/v1/projects/{project_id}/references")
def list_references(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _owned_project(db, project_id, user.id)
    excerpts = db.scalars(select(ReferenceExcerpt).where(ReferenceExcerpt.project_id == project_id).order_by(ReferenceExcerpt.created_at)).all()
    return [
        {"id": item.id, "title": item.title, "text": item.text, "source_label": item.source_label, "page": item.page}
        for item in excerpts
    ]


@app.delete("/api/v1/references/{reference_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reference(reference_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    excerpt = db.scalar(
        select(ReferenceExcerpt)
        .join(Project, ReferenceExcerpt.project_id == Project.id)
        .where(ReferenceExcerpt.id == reference_id, Project.user_id == user.id)
    )
    if excerpt is None:
        raise HTTPException(status_code=404, detail="Reference excerpt not found")
    db.delete(excerpt)
    db.commit()


@app.post("/api/v1/verification-reports/validate")
def validate_verification_report(report: VerificationReport, _: User = Depends(current_user)):
    return report.model_dump(mode="json")


@app.post("/api/v1/questions/{question_id}/answers", status_code=status.HTTP_201_CREATED)
def create_answer_version(
    question_id: str,
    body: AnswerCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    question = _owned_question(db, question_id, user.id)
    last_version = db.scalar(select(func.max(AnswerVersion.version_number)).where(AnswerVersion.question_id == question.id)) or 0
    answer = AnswerVersion(
        question_id=question.id,
        version_number=last_version + 1,
        answer_json=body.answer.model_dump(mode="json"),
        created_by_user_id=user.id,
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)
    return {"id": answer.id, "version_number": answer.version_number, "answer": answer.answer_json}


@app.get("/api/v1/documents/{document_id}/progress")
def get_document_progress(document_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _owned_document(db, document_id, user.id)
    questions = db.scalars(select(Question).where(Question.document_id == document_id)).all()
    counts = {
        "PENDING": 0,
        "QUEUED": 0,
        "GENERATING": 0,
        "VERIFYING": 0,
        "REVISING": 0,
        "VERIFIER_APPROVED": 0,
        "MANUAL_REVIEW": 0,
        "FAILED": 0,
        "CANCELLED": 0,
    }
    for q in questions:
        counts[q.status] = counts.get(q.status, 0) + 1
    total = len(questions)
    completed = counts["VERIFIER_APPROVED"] + counts["MANUAL_REVIEW"]
    percent = round((completed / total) * 100, 1) if total > 0 else 0.0
    return {
        "document_id": document_id,
        "total": total,
        "completed": completed,
        "percent": percent,
        "counts": counts,
    }


@app.get("/api/v1/documents/{document_id}/events")
def stream_document_events(
    document_id: str,
    token: str | None = Query(None),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    last_event_id: str | None = Header(None, alias="Last-Event-ID"),
    db: Session = Depends(get_db),
):
    # SSE cannot send Authorization header; support query-param token fallback
    user = None
    if credentials and credentials.scheme.lower() == "bearer":
        try:
            user = current_user(credentials, db)
        except HTTPException:
            pass
    if user is None and token:
        user_id = _decode_token(token)
        user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Bearer token required")
    _owned_document(db, document_id, user.id)
    progress = get_document_progress(document_id, user, db)

    def event_generator():
        event_id = str(int(time.time()))
        data = json.dumps(progress)
        yield f"id: {event_id}\nevent: progress\ndata: {data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/v1/questions/{question_id}/answer")
def get_latest_question_answer(question_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _owned_question(db, question_id, user.id)
    version = db.scalar(
        select(AnswerVersion)
        .where(AnswerVersion.question_id == question_id)
        .order_by(AnswerVersion.version_number.desc())
    )
    if not version:
        raise HTTPException(status_code=404, detail="No answer found for this question")

    report_record = db.scalar(
        select(VerificationReportRecord).where(VerificationReportRecord.answer_version_id == version.id)
    )
    human_decision = db.scalar(
        select(HumanApproval)
        .where(HumanApproval.answer_version_id == version.id)
        .order_by(HumanApproval.created_at.desc())
    )
    return {
        "question_id": question_id,
        "answer_version_id": version.id,
        "version_number": version.version_number,
        "answer": version.answer_json,
        "provider": version.provider,
        "model": version.model,
        "created_at": version.created_at,
        "verifier_report": report_record.report_json if report_record else None,
        "latest_human_decision": human_decision.decision if human_decision else None,
    }


@app.get("/api/v1/questions/{question_id}/versions")
def get_question_versions(question_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _owned_question(db, question_id, user.id)
    versions = db.scalars(
        select(AnswerVersion)
        .where(AnswerVersion.question_id == question_id)
        .order_by(AnswerVersion.version_number.asc())
    ).all()

    out = []
    for v in versions:
        report = db.scalar(select(VerificationReportRecord).where(VerificationReportRecord.answer_version_id == v.id))
        approvals = db.scalars(
            select(HumanApproval)
            .where(HumanApproval.answer_version_id == v.id)
            .order_by(HumanApproval.created_at)
        ).all()
        out.append(
            {
                "id": v.id,
                "version_number": v.version_number,
                "answer": v.answer_json,
                "provider": v.provider,
                "model": v.model,
                "created_at": v.created_at,
                "verifier_report": report.report_json if report else None,
                "human_approvals": [
                    {"decision": a.decision, "reviewer_id": a.user_id, "created_at": a.created_at}
                    for a in approvals
                ],
            }
        )
    return out


@app.patch("/api/v1/questions/{question_id}/answer", status_code=status.HTTP_201_CREATED)
def update_question_answer_as_new_version(
    question_id: str,
    body: AnswerCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    question = _owned_question(db, question_id, user.id)
    last_version = db.scalar(select(func.max(AnswerVersion.version_number)).where(AnswerVersion.question_id == question.id)) or 0
    new_version = AnswerVersion(
        question_id=question.id,
        version_number=last_version + 1,
        answer_json=body.answer.model_dump(mode="json"),
        provider="manual-user-edit",
        model="human",
        prompt_version=None,
        created_by_user_id=user.id,
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    return {
        "id": new_version.id,
        "version_number": new_version.version_number,
        "answer": new_version.answer_json,
        "created_at": new_version.created_at,
    }


@app.post("/api/v1/questions/{question_id}/approve", status_code=status.HTTP_201_CREATED)
def record_human_decision(
    question_id: str,
    body: HumanApprovalCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    _owned_question(db, question_id, user.id)
    version = db.scalar(select(AnswerVersion).where(AnswerVersion.id == body.answer_version_id, AnswerVersion.question_id == question_id))
    if version is None:
        raise HTTPException(status_code=404, detail="Answer version not found")
    decision = HumanApproval(
        question_id=question_id,
        answer_version_id=version.id,
        user_id=user.id,
        decision=body.decision,
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return {"id": decision.id, "answer_version_id": version.id, "decision": decision.decision, "created_at": decision.created_at}


@app.get("/api/v1/questions/{question_id}/approvals")
def list_human_decisions(question_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _owned_question(db, question_id, user.id)
    decisions = db.scalars(
        select(HumanApproval).where(HumanApproval.question_id == question_id).order_by(HumanApproval.created_at)
    ).all()
    return [
        {
            "id": decision.id,
            "answer_version_id": decision.answer_version_id,
            "decision": decision.decision,
            "reviewer_id": decision.user_id,
            "created_at": decision.created_at,
        }
        for decision in decisions
    ]


@app.post("/api/v1/documents/{document_id}/exports", status_code=status.HTTP_201_CREATED)
def create_document_export(
    document_id: str,
    body: ExportCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    # Enforce export quota
    user_export_count = db.scalar(
        select(func.count(Export.id)).where(Export.user_id == user.id)
    ) or 0
    if user_export_count >= MAX_EXPORTS_PER_USER:
        raise HTTPException(status_code=400, detail=f"User export quota exceeded (maximum {MAX_EXPORTS_PER_USER} exports)")

    doc = _owned_document(db, document_id, user.id)
    query = select(Question).where(Question.document_id == document_id)
    if body.question_ids:
        query = query.where(Question.id.in_(body.question_ids))
    questions = db.scalars(query.order_by(Question.position.asc())).all()

    export_items = []
    included_ids = []

    for q in questions:
        latest_version = db.scalar(
            select(AnswerVersion)
            .where(AnswerVersion.question_id == q.id)
            .order_by(AnswerVersion.version_number.desc())
        )

        is_approved = False
        if latest_version:
            latest_human = db.scalar(
                select(HumanApproval)
                .where(HumanApproval.answer_version_id == latest_version.id)
                .order_by(HumanApproval.created_at.desc())
            )
            if latest_human:
                if latest_human.decision == "APPROVED":
                    is_approved = True
                elif latest_human.decision == "REJECTED":
                    is_approved = False
            else:
                rep = db.scalar(
                    select(VerificationReportRecord).where(
                        VerificationReportRecord.answer_version_id == latest_version.id
                    )
                )
                if rep and rep.verdict == "approved":
                    is_approved = True

        if not is_approved:
            if not body.include_unapproved:
                continue
            is_unapproved = True
        else:
            is_unapproved = False

        unit_name = None
        if q.unit_id:
            unit = db.get(Unit, q.unit_id)
            if unit:
                unit_name = unit.name

        included_ids.append(q.id)
        export_items.append(
            {
                "id": q.id,
                "unit_name": unit_name,
                "question_number": q.question_number,
                "section": q.section,
                "question_text": q.question_text,
                "marks": q.marks,
                "is_unapproved": is_unapproved,
                "answer": latest_version.answer_json if latest_version else None,
            }
        )

    content_bytes, ext, mime_type = generate_export(doc.title, export_items, body.format)
    stored = storage_service.save(content_bytes, extension=ext)

    export = Export(
        project_id=doc.project_id,
        document_id=doc.id,
        user_id=user.id,
        format=body.format.upper(),
        storage_key=stored.storage_key,
        status="COMPLETED",
        options_json={"include_unapproved": body.include_unapproved},
        included_question_ids=included_ids,
        finished_at=utc_now(),
    )
    db.add(export)
    db.commit()
    db.refresh(export)

    return {
        "id": export.id,
        "format": export.format,
        "status": export.status,
        "included_question_count": len(included_ids),
        "download_url": f"/api/v1/exports/{export.id}/download",
    }


@app.get("/api/v1/exports/{export_id}")
def get_export_metadata(export_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    export = _owned_export(db, export_id, user.id)
    return {
        "id": export.id,
        "project_id": export.project_id,
        "document_id": export.document_id,
        "format": export.format,
        "status": export.status,
        "included_question_ids": export.included_question_ids,
        "created_at": export.created_at,
        "finished_at": export.finished_at,
        "download_url": f"/api/v1/exports/{export.id}/download",
    }


@app.get("/api/v1/exports/{export_id}/download")
def download_export(export_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    export = _owned_export(db, export_id, user.id)
    if not export.storage_key:
        raise HTTPException(status_code=404, detail="Export file content not found")
    data = storage_service.get(export.storage_key)

    mime_types = {
        "MD": "text/markdown",
        "JSON": "application/json",
        "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "PDF": "application/pdf",
    }
    media_type = mime_types.get(export.format, "application/octet-stream")
    ext = export.format.lower()
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="export_{export.id}.{ext}"'},
    )


@app.post("/api/v1/system/retention-sweep")
def trigger_retention_sweep(
    upload_days: int = 30,
    export_days: int = 7,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from .retention import cleanup_expired_files
    result = cleanup_expired_files(db, upload_retention_days=upload_days, export_retention_days=export_days)
    return {"status": "success", **result}
