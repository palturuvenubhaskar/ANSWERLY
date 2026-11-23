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

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import AnswerVersion, HumanApproval, Project, Question, ReferenceExcerpt, User
from .schemas import (
    AnswerCreate,
    DeleteProjectRequest,
    HumanApprovalCreate,
    LoginRequest,
    ProjectCreate,
    ProjectUpdate,
    QuestionCreate,
    ReferenceExcerptCreate,
    RegisterRequest,
    VerificationReport,
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
    Base.metadata.create_all(bind=engine)
    logger.info(json.dumps({"event": "application_started", "environment": APP_ENV}))
    yield


app = FastAPI(title="Answerly API", version="0.1.0", lifespan=lifespan)


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
def register(body: RegisterRequest, db: Session = Depends(get_db)):
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
def login(body: LoginRequest, db: Session = Depends(get_db)):
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


@app.post("/api/v1/projects/{project_id}/questions", status_code=status.HTTP_201_CREATED)
def create_question(
    project_id: str,
    body: QuestionCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    project = _owned_project(db, project_id, user.id)
    last_position = db.scalar(select(func.max(Question.position)).where(Question.project_id == project.id)) or 0
    question = Question(project_id=project.id, question_text=body.question_text, marks=body.marks, position=last_position + 1)
    db.add(question)
    db.commit()
    db.refresh(question)
    return {"id": question.id, "question_text": question.question_text, "marks": question.marks, "position": question.position}


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
