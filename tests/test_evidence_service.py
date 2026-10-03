from hashlib import sha256

import pytest
from sqlalchemy.orm import Session

from superai_review.auth.types import UserRole
from superai_review.db.models import Document, DocumentSegment, ReviewSession, User
from superai_review.documents.types import ExtractionState
from superai_review.evidence.errors import (
    EvidenceIntegrityError,
    InvalidEvidenceReferenceError,
    RetrievalLimitError,
)
from superai_review.evidence.service import EvidenceService


def add_user(db: Session, subject: str, email: str) -> User:
    user = User(
        issuer="https://issuer.example",
        subject=subject,
        email=email,
        email_normalized=email,
        role=UserRole.USER.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def add_document(db: Session, user: User, text: str) -> tuple[ReviewSession, Document]:
    review = ReviewSession(user_id=user.id, objective="Prepare an answer")
    db.add(review)
    db.flush()
    document = Document(
        session_id=review.id,
        original_name="source.txt",
        content_type="text/plain",
        size=len(text.encode()),
        sha256=sha256(text.encode()).hexdigest(),
        storage_key=f"storage-{review.id}",
        extraction_state=ExtractionState.COMPLETED.value,
        page_count=1,
    )
    document.segments = [
        DocumentSegment(ordinal=0, page=1, kind="text", text=text),
    ]
    db.add(document)
    db.commit()
    db.refresh(review)
    db.refresh(document)
    return review, document


def test_materialization_is_stable_chunked_and_idempotent(db: Session) -> None:
    user = add_user(db, "u1", "u1@example.com")
    review, document = add_document(db, user, "A" * 9000)
    service = EvidenceService(db, chunk_chars=4000)

    first = service.list_for_document(user=user, session_id=review.id, document_id=document.id)
    second = service.list_for_document(user=user, session_id=review.id, document_id=document.id)

    assert [len(item.text) for item in first] == [4000, 4000, 1000]
    assert [item.evidence_id for item in first] == [item.evidence_id for item in second]
    assert first[0].evidence_id.endswith(":p0001:e00000")
    assert first[0].content_hash == sha256(first[0].text.encode()).hexdigest()


def test_existing_evidence_hash_is_verified(db: Session) -> None:
    user = add_user(db, "u1", "u1@example.com")
    review, document = add_document(db, user, "immutable source")
    service = EvidenceService(db, chunk_chars=4000)
    service.list_for_document(user=user, session_id=review.id, document_id=document.id)

    document.segments[0].text = "tampered source"
    db.commit()

    with pytest.raises(EvidenceIntegrityError):
        service.list_for_document(user=user, session_id=review.id, document_id=document.id)


def test_refs_must_exist_in_the_same_owned_session(db: Session) -> None:
    user = add_user(db, "u1", "u1@example.com")
    review, document = add_document(db, user, "source one")
    service = EvidenceService(db)
    evidence = service.list_for_document(user=user, session_id=review.id, document_id=document.id)

    with pytest.raises(InvalidEvidenceReferenceError) as exc_info:
        service.validate_refs(
            user=user,
            session_id=review.id,
            evidence_ids=[evidence[0].evidence_id, "missing:evidence"],
        )

    assert exc_info.value.missing_ids == ["missing:evidence"]


def test_retrieval_limits_fail_instead_of_silently_truncating(db: Session) -> None:
    user = add_user(db, "u1", "u1@example.com")
    review, document = add_document(db, user, "alpha beta gamma delta")
    service = EvidenceService(
        db,
        chunk_chars=6,
        retrieval_max_items=1,
        retrieval_max_chars=5,
    )
    evidence = service.list_for_document(user=user, session_id=review.id, document_id=document.id)

    with pytest.raises(RetrievalLimitError):
        service.retrieve(
            user=user,
            session_id=review.id,
            evidence_ids=[item.evidence_id for item in evidence[:2]],
        )

    with pytest.raises(RetrievalLimitError):
        service.retrieve(
            user=user,
            session_id=review.id,
            evidence_ids=[evidence[0].evidence_id],
        )
