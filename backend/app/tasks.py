"""Celery tasks for Answerly background job processing."""

import logging

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from .celery_app import celery_app
from .db import SessionLocal
from .models import ProcessingJob, Question, utc_now
from .pipeline import execute_job

logger = logging.getLogger("answerly.tasks")


@celery_app.task(
    bind=True,
    name="answerly.execute_job",
    max_retries=3,
    default_retry_delay=10,
    acks_late=True,
)
def execute_job_task(self, job_id: str) -> dict:
    """Execute a single processing job (generate → verify → revise loop).

    Retries on transient failures without incrementing the job's revision count.
    """
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, job_id)
        if not job:
            logger.error(f"Job {job_id} not found, skipping")
            return {"status": "NOT_FOUND", "job_id": job_id}

        # Stale-lease recovery: skip if already finished
        if job.status in ("COMPLETED", "CANCELLED", "MANUAL_REVIEW", "FAILED"):
            logger.info(f"Job {job_id} already in terminal state {job.status}")
            return {"status": job.status, "job_id": job_id}

        try:
            updated_job = execute_job(job_id, db)
            return {
                "status": updated_job.status,
                "job_id": updated_job.id,
                "revision_count": updated_job.revision_count,
            }
        except SoftTimeLimitExceeded:
            logger.warning(f"Job {job_id} hit soft time limit")
            job = db.get(ProcessingJob, job_id)
            if job and job.status not in ("COMPLETED", "CANCELLED", "MANUAL_REVIEW"):
                job.status = "FAILED"
                job.last_error_code = "TIMEOUT"
                job.last_error_message = "Job exceeded the maximum processing time"
                job.finished_at = utc_now()
                q = db.get(Question, job.question_id)
                if q:
                    q.status = "FAILED"
                db.commit()
            return {"status": "FAILED", "job_id": job_id, "error": "TIMEOUT"}
        except Exception as exc:
            logger.exception(f"Job {job_id} failed: {exc}")
            job = db.get(ProcessingJob, job_id)
            if job:
                job.retry_count += 1
                if job.retry_count >= 3:
                    job.status = "FAILED"
                    job.last_error_code = type(exc).__name__
                    job.last_error_message = str(exc)[:500]
                    job.finished_at = utc_now()
                    q = db.get(Question, job.question_id)
                    if q:
                        q.status = "FAILED"
                    db.commit()
                    return {"status": "FAILED", "job_id": job_id, "error": str(exc)[:200]}
                db.commit()
            raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(name="answerly.retention_sweep")
def retention_sweep_task(upload_days: int = 30, export_days: int = 7) -> dict:
    """Periodic retention sweep for expired uploads and exports."""
    from .retention import cleanup_expired_files

    db = SessionLocal()
    try:
        return cleanup_expired_files(db, upload_days, export_days)
    finally:
        db.close()
