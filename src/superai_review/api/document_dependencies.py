from typing import Annotated

from fastapi import Depends

from superai_review.api.dependencies import DbDependency
from superai_review.config import get_settings
from superai_review.documents.isolation import ProcessExtractionRunner
from superai_review.documents.service import DocumentService
from superai_review.documents.storage import LocalDocumentStorage


def get_document_service(db: DbDependency) -> DocumentService:
    settings = get_settings()
    return DocumentService(
        db,
        LocalDocumentStorage(settings.document_storage_root),
        ProcessExtractionRunner(
            timeout_seconds=settings.document_extraction_timeout_seconds,
            pdf_text_min_chars_per_page=settings.pdf_text_min_chars_per_page,
        ),
        max_upload_bytes=settings.max_upload_bytes,
    )


DocumentServiceDependency = Annotated[DocumentService, Depends(get_document_service)]
