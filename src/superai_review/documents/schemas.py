from datetime import datetime

from pydantic import BaseModel

from superai_review.db.models import Document
from superai_review.documents.types import ExtractionState


class DocumentView(BaseModel):
    id: str
    original_name: str
    content_type: str
    size: int
    sha256: str
    extraction_state: ExtractionState
    page_count: int | None
    ocr_used: bool
    error_code: str | None
    created_at: datetime

    @classmethod
    def from_model(cls, document: Document) -> "DocumentView":
        return cls(
            id=document.id,
            original_name=document.original_name,
            content_type=document.content_type,
            size=document.size,
            sha256=document.sha256,
            extraction_state=ExtractionState(document.extraction_state),
            page_count=document.page_count,
            ocr_used=document.ocr_used,
            error_code=document.error_code,
            created_at=document.created_at,
        )
