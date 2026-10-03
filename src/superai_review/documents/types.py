from enum import StrEnum

from pydantic import BaseModel, Field


class DocumentMime(StrEnum):
    PDF = "application/pdf"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    TEXT = "text/plain"
    MARKDOWN = "text/markdown"
    PNG = "image/png"
    JPEG = "image/jpeg"


class ExtractionState(StrEnum):
    STORED = "STORED"
    EXTRACTING = "EXTRACTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ExtractedSegment(BaseModel):
    ordinal: int = Field(ge=0)
    page: int | None = Field(default=None, ge=1)
    kind: str = Field(min_length=1, max_length=40)
    text: str


class ExtractedDocument(BaseModel):
    content_type: DocumentMime
    page_count: int = Field(ge=1)
    segments: list[ExtractedSegment]
    ocr_used: bool = False
