from pydantic import BaseModel, Field

from superai_review.db.models import Document, EvidenceRecord


class EvidenceView(BaseModel):
    evidence_id: str
    document_id: str
    page: int | None
    section: str
    ordinal: int
    content_hash: str
    text: str

    @classmethod
    def from_record(cls, record: EvidenceRecord) -> "EvidenceView":
        return cls(
            evidence_id=record.id,
            document_id=record.document_id,
            page=record.page,
            section=record.section,
            ordinal=record.ordinal,
            content_hash=record.content_hash,
            text=record.text,
        )


class EvidenceIndexItem(BaseModel):
    evidence_id: str
    document_id: str
    page: int | None
    section: str
    ordinal: int
    content_hash: str
    char_count: int


class DocumentContextSummary(BaseModel):
    document_id: str
    original_name: str
    content_type: str
    page_count: int | None
    ocr_used: bool
    neutral_summary: str

    @classmethod
    def build(cls, document: Document, evidence: list[EvidenceView]) -> "DocumentContextSummary":
        preview = " ".join(item.text.strip() for item in evidence[:2] if item.text.strip())
        if len(preview) > 500:
            preview = preview[:497].rstrip() + "..."
        return cls(
            document_id=document.id,
            original_name=document.original_name,
            content_type=document.content_type,
            page_count=document.page_count,
            ocr_used=document.ocr_used,
            neutral_summary=preview,
        )


class ContextPack(BaseModel):
    session_id: str
    objective: str
    constraints: dict
    language: str
    detected_task_type: str
    document_summaries: list[DocumentContextSummary]
    evidence_index: list[EvidenceIndexItem]
    selected_evidence: list[EvidenceView]
    important_dates: list[str] = Field(default_factory=list)
    important_numbers: list[str] = Field(default_factory=list)
    important_names: list[str] = Field(default_factory=list)
    extraction_warnings: list[str] = Field(default_factory=list)
    source_char_count: int
    selection_budget_chars: int
    source_complete: bool
    omitted_evidence_count: int
    retrieval_required: bool
