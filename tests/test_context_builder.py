from hashlib import sha256

from sqlalchemy.orm import Session

from superai_review.auth.types import UserRole
from superai_review.db.models import Document, DocumentSegment, ReviewSession, User
from superai_review.documents.types import ExtractionState
from superai_review.evidence.context import ContextBuilder
from superai_review.evidence.service import EvidenceService


def setup_review(db: Session) -> tuple[User, ReviewSession]:
    user = User(
        issuer="https://issuer.example",
        subject="user",
        email="user@example.com",
        email_normalized="user@example.com",
        role=UserRole.USER.value,
    )
    db.add(user)
    db.flush()
    review = ReviewSession(
        user_id=user.id,
        objective="Przygotuj odpowiedź na odrzucenie reklamacji przez Dealera Auto",
        constraints={"tone": "firm"},
        language="pl",
    )
    db.add(review)
    db.commit()
    db.refresh(user)
    db.refresh(review)
    return user, review


def add_completed_document(
    db: Session,
    review: ReviewSession,
    text: str,
    *,
    name: str = "reklamacja.txt",
    ocr_used: bool = False,
) -> Document:
    document = Document(
        session_id=review.id,
        original_name=name,
        content_type="text/plain",
        size=len(text.encode()),
        sha256=sha256(text.encode()).hexdigest(),
        storage_key=f"storage-{name}-{len(text)}",
        extraction_state=ExtractionState.COMPLETED.value,
        page_count=1,
        ocr_used=ocr_used,
    )
    document.segments = [DocumentSegment(ordinal=0, page=1, kind="text", text=text)]
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def test_short_context_contains_all_source_and_detected_facts(db: Session) -> None:
    user, review = setup_review(db)
    add_completed_document(
        db,
        review,
        "Dealer Auto odpowiedział 03.10.2026. Kwota reklamacji to 12 500 PLN.",
    )
    evidence_service = EvidenceService(db, chunk_chars=4000)
    pack = ContextBuilder(db, evidence_service).build(
        user=user,
        session_id=review.id,
        max_source_chars=40000,
    )

    assert pack.detected_task_type == "complaint"
    assert pack.source_complete is True
    assert pack.retrieval_required is False
    assert pack.omitted_evidence_count == 0
    assert len(pack.evidence_index) == len(pack.selected_evidence) == 1
    assert "03.10.2026" in pack.important_dates
    assert pack.document_summaries[0].neutral_summary
    assert pack.constraints == {"tone": "firm"}


def test_large_context_keeps_full_index_and_marks_omissions(db: Session) -> None:
    user, review = setup_review(db)
    text = " ".join(
        f"Fragment {index} reklamacja argument odpowiedź szczegół {index}."
        for index in range(120)
    )
    add_completed_document(db, review, text)
    evidence_service = EvidenceService(
        db,
        chunk_chars=200,
        retrieval_max_items=12,
        retrieval_max_chars=16000,
    )
    pack = ContextBuilder(db, evidence_service).build(
        user=user,
        session_id=review.id,
        max_source_chars=1000,
    )

    assert pack.source_complete is False
    assert pack.retrieval_required is True
    assert pack.omitted_evidence_count > 0
    assert len(pack.evidence_index) > len(pack.selected_evidence)
    indexed_ids = {item.evidence_id for item in pack.evidence_index}
    assert all(item.evidence_id in indexed_ids for item in pack.selected_evidence)
    assert all(
        len(item.text)
        == next(index.char_count for index in pack.evidence_index if index.evidence_id == item.evidence_id)
        for item in pack.selected_evidence
    )

    omitted_id = next(
        item.evidence_id
        for item in pack.evidence_index
        if item.evidence_id not in {selected.evidence_id for selected in pack.selected_evidence}
    )
    retrieved = evidence_service.retrieve(
        user=user,
        session_id=review.id,
        evidence_ids=[omitted_id],
    )
    assert retrieved[0].evidence_id == omitted_id


def test_context_surfaces_ocr_and_failed_extraction_warnings(db: Session) -> None:
    user, review = setup_review(db)
    add_completed_document(db, review, "OCR source", name="scan.txt", ocr_used=True)
    failed = Document(
        session_id=review.id,
        original_name="failed.pdf",
        content_type="application/pdf",
        size=10,
        sha256="0" * 64,
        storage_key="failed-storage",
        extraction_state=ExtractionState.FAILED.value,
        error_code="extraction_failed",
    )
    db.add(failed)
    db.commit()

    pack = ContextBuilder(db, EvidenceService(db)).build(
        user=user,
        session_id=review.id,
        max_source_chars=40000,
    )

    assert any(warning.endswith(":ocr_used") for warning in pack.extraction_warnings)
    assert any("extraction_failed" in warning for warning in pack.extraction_warnings)
