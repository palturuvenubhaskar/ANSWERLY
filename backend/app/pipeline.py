import json
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session

from .gateway import ModelGateway, default_gateway
from .models import (
    AnswerVersion,
    ModelCallAttempt,
    ProcessingJob,
    ProcessingRun,
    Question,
    ReferenceExcerpt,
    VerificationReportRecord,
    utc_now,
)
from .prompts import (
    GENERATOR_SYSTEM_PROMPT,
    PROMPT_VERSION,
    REFINER_SYSTEM_PROMPT,
    VERIFIER_SYSTEM_PROMPT,
    format_generator_prompt,
    format_refiner_prompt,
    format_verifier_prompt,
)
from .schemas import AnswerContent, VerificationReport

logger = logging.getLogger("answerly.pipeline")


def _log_attempt(
    db: Session,
    job_id: str,
    role: str,
    response,
    outcome: str = "SUCCESS",
    error_code: str | None = None,
):
    attempt = ModelCallAttempt(
        processing_job_id=job_id,
        role=role,
        provider=response.provider,
        model=response.model,
        prompt_version=PROMPT_VERSION,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        latency_ms=response.latency_ms,
        estimated_cost=response.cost,
        outcome=outcome,
        error_code=error_code,
    )
    db.add(attempt)
    db.commit()


def execute_job(job_id: str, db: Session, gateway: ModelGateway | None = None) -> ProcessingJob:
    gw = gateway or default_gateway
    job = db.get(ProcessingJob, job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    run = db.get(ProcessingRun, job.processing_run_id)
    question = db.get(Question, job.question_id)
    if not run or not question:
        raise ValueError("Job run or question missing")

    # Check cancellation
    if job.cancel_requested_at:
        job.status = "CANCELLED"
        question.status = "CANCELLED"
        job.finished_at = utc_now()
        db.commit()
        return job

    job.started_at = utc_now()

    # Load references
    ref_dicts = []
    if run.reference_ids:
        refs = db.scalars(select(ReferenceExcerpt).where(ReferenceExcerpt.id.in_(run.reference_ids))).all()
        ref_dicts = [
            {"title": r.title, "text": r.text, "source_label": r.source_label, "page": r.page}
            for r in refs
        ]

    # --- Step 1: Initial Generation ---
    job.status = "GENERATING"
    question.status = "GENERATING"
    db.commit()

    if job.cancel_requested_at:
        job.status = "CANCELLED"
        question.status = "CANCELLED"
        job.finished_at = utc_now()
        db.commit()
        return job

    gen_prompt = format_generator_prompt(question.question_text, question.marks, ref_dicts)
    gen_resp = gw.generate(GENERATOR_SYSTEM_PROMPT, gen_prompt, role="GENERATOR")
    _log_attempt(db, job.id, "GENERATOR", gen_resp)

    answer_content = AnswerContent.model_validate_json(gen_resp.content)
    version_num = 1
    answer_version = AnswerVersion(
        question_id=question.id,
        version_number=version_num,
        answer_json=answer_content.model_dump(mode="json"),
        provider=gen_resp.provider,
        model=gen_resp.model,
        prompt_version=PROMPT_VERSION,
        created_by_user_id=run.user_id,
    )
    db.add(answer_version)
    db.commit()
    db.refresh(answer_version)

    # --- Step 2: Verification ---
    job.status = "VERIFYING"
    question.status = "VERIFYING"
    db.commit()

    if job.cancel_requested_at:
        job.status = "CANCELLED"
        question.status = "CANCELLED"
        job.finished_at = utc_now()
        db.commit()
        return job

    ver_prompt = format_verifier_prompt(
        question.question_text,
        question.marks,
        answer_version.answer_json,
        ref_dicts,
    )
    ver_resp = gw.generate(VERIFIER_SYSTEM_PROMPT, ver_prompt, role="VERIFIER")
    _log_attempt(db, job.id, "VERIFIER", ver_resp)

    report = VerificationReport.model_validate_json(ver_resp.content)
    v_record = VerificationReportRecord(
        question_id=question.id,
        answer_version_id=answer_version.id,
        verifier_provider=ver_resp.provider,
        verifier_model=ver_resp.model,
        verdict=report.verdict,
        report_json=report.model_dump(mode="json"),
    )
    db.add(v_record)
    db.commit()

    if report.verdict == "approved":
        job.status = "COMPLETED"
        question.status = "VERIFIER_APPROVED"
        job.finished_at = utc_now()
        db.commit()
        return job

    # --- Step 3: Revision loop (max 2 revisions) ---
    current_version = answer_version
    current_report = report

    while job.revision_count < 2 and current_report.verdict == "needs_revision":
        if job.cancel_requested_at:
            job.status = "CANCELLED"
            question.status = "CANCELLED"
            job.finished_at = utc_now()
            db.commit()
            return job

        job.revision_count += 1
        job.status = "REVISING"
        question.status = "REVISING"
        db.commit()

        ref_prompt = format_refiner_prompt(
            question.question_text,
            question.marks,
            current_version.answer_json,
            [i.model_dump(mode="json") for i in current_report.issues],
        )
        ref_resp = gw.generate(REFINER_SYSTEM_PROMPT, ref_prompt, role="REFINER")
        _log_attempt(db, job.id, "REFINER", ref_resp)

        refined_content = AnswerContent.model_validate_json(ref_resp.content)
        version_num += 1
        current_version = AnswerVersion(
            question_id=question.id,
            version_number=version_num,
            answer_json=refined_content.model_dump(mode="json"),
            provider=ref_resp.provider,
            model=ref_resp.model,
            prompt_version=PROMPT_VERSION,
            created_by_user_id=run.user_id,
        )
        db.add(current_version)
        db.commit()
        db.refresh(current_version)

        # Re-verify
        job.status = "VERIFYING"
        question.status = "VERIFYING"
        db.commit()

        ver_prompt = format_verifier_prompt(
            question.question_text,
            question.marks,
            current_version.answer_json,
            ref_dicts,
        )
        ver_resp = gw.generate(VERIFIER_SYSTEM_PROMPT, ver_prompt, role="VERIFIER")
        _log_attempt(db, job.id, "VERIFIER", ver_resp)

        current_report = VerificationReport.model_validate_json(ver_resp.content)
        v_record = VerificationReportRecord(
            question_id=question.id,
            answer_version_id=current_version.id,
            verifier_provider=ver_resp.provider,
            verifier_model=ver_resp.model,
            verdict=current_report.verdict,
            report_json=current_report.model_dump(mode="json"),
        )
        db.add(v_record)
        db.commit()

        if current_report.verdict == "approved":
            job.status = "COMPLETED"
            question.status = "VERIFIER_APPROVED"
            job.finished_at = utc_now()
            db.commit()
            return job

    # If revisions exhausted and still not approved
    job.status = "MANUAL_REVIEW"
    question.status = "MANUAL_REVIEW"
    job.finished_at = utc_now()
    db.commit()
    return job
