from datetime import datetime, timedelta, timezone
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Document, Export, utc_now
from .storage import storage_service

logger = logging.getLogger("answerly.retention")


def cleanup_expired_files(
    db: Session,
    upload_retention_days: int = 30,
    export_retention_days: int = 7,
) -> dict:
    """Purges expired source uploads and generated exports per security policy."""
    now = utc_now()
    upload_cutoff = now - timedelta(days=upload_retention_days)
    export_cutoff = now - timedelta(days=export_retention_days)

    purged_uploads = 0
    purged_exports = 0

    # Clean old exports
    expired_exports = db.scalars(
        select(Export).where(Export.created_at < export_cutoff, Export.storage_key.is_not(None))
    ).all()
    for exp in expired_exports:
        if exp.storage_key and storage_service.exists(exp.storage_key):
            storage_service.delete(exp.storage_key)
        exp.storage_key = None
        exp.status = "EXPIRED"
        purged_exports += 1

    # Clean old uploads (mark storage_key purged while retaining metadata)
    expired_docs = db.scalars(
        select(Document).where(Document.created_at < upload_cutoff, Document.storage_key != "")
    ).all()
    for doc in expired_docs:
        if doc.storage_key and storage_service.exists(doc.storage_key):
            storage_service.delete(doc.storage_key)
        doc.storage_key = "PURGED_BY_RETENTION"
        purged_uploads += 1

    db.commit()
    logger.info(f"Retention sweep: purged {purged_uploads} uploads, {purged_exports} exports")
    return {"purged_uploads": purged_uploads, "purged_exports": purged_exports}
