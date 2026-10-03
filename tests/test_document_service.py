from hashlib import sha256

import pytest
from sqlalchemy.orm import Session

from superai_review.auth.ownership import ResourceNotFoundError
from superai_review.auth.types import UserRole
from superai_review.db.models import ReviewSession, User
from superai_review.documents.errors import DocumentTooLargeError
from superai_review.documents.extractor import DocumentExtractor
from superai_review.documents.isolation import InProcessExtractionRunner
from superai_review.documents.service import DocumentService
from superai_review.documents.types import ExtractionState


class MemoryStorage:
    def __init__(self) -> None:
        self.data: dict[str, bytes] = {}

    def put(self, key: str, data: bytes) -> None:
        self.data[key] = data

    def get(self, key: str) -> bytes:
        return self.data[key]

    def delete(self, key: str) -> None:
        self.data.pop(key, None)


class NoopOCR:
    def image_to_text(self, data: bytes) -> str:
        raise AssertionError("OCR should not be called")

    def pdf_page_to_text(
        self,
        data: bytes,
        page_index: int,
        password: str | None = None,
    ) -> str:
        raise AssertionError("OCR should not be called")


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


def add_review(db: Session, user: User) -> ReviewSession:
    review = ReviewSession(user_id=user.id, objective="review")
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def service(db: Session, storage: MemoryStorage, max_bytes: int = 1024) -> DocumentService:
    return DocumentService(
        db,
        storage,
        InProcessExtractionRunner(DocumentExtractor(NoopOCR())),
        max_upload_bytes=max_bytes,
    )


def test_ingest_stores_internal_key_metadata_and_segments(db: Session) -> None:
    user = add_user(db, "u1", "u1@example.com")
    review = add_review(db, user)
    storage = MemoryStorage()
    data = b"hello from a safe text file"

    document = service(db, storage).ingest(
        user=user,
        session_id=review.id,
        filename="note.txt",
        declared_content_type="text/plain",
        data=data,
        password="never-persist-this",
    )

    assert document.extraction_state == ExtractionState.COMPLETED.value
    assert document.sha256 == sha256(data).hexdigest()
    assert document.storage_key != document.original_name
    assert storage.data[document.storage_key] == data
    assert document.segments[0].text == data.decode()
    assert document.page_count == 1
    assert document.ocr_used is False


def test_oversized_upload_is_rejected_before_storage(db: Session) -> None:
    user = add_user(db, "u1", "u1@example.com")
    review = add_review(db, user)
    storage = MemoryStorage()

    with pytest.raises(DocumentTooLargeError):
        service(db, storage, max_bytes=3).ingest(
            user=user,
            session_id=review.id,
            filename="note.txt",
            declared_content_type="text/plain",
            data=b"1234",
        )

    assert storage.data == {}


def test_foreign_session_is_not_discoverable(db: Session) -> None:
    owner = add_user(db, "owner", "owner@example.com")
    stranger = add_user(db, "stranger", "stranger@example.com")
    review = add_review(db, owner)

    with pytest.raises(ResourceNotFoundError):
        service(db, MemoryStorage()).ingest(
            user=stranger,
            session_id=review.id,
            filename="note.txt",
            declared_content_type="text/plain",
            data=b"content",
        )
