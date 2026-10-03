from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from superai_review.api.app import create_app
from superai_review.api.dependencies import get_db
from superai_review.api.document_dependencies import get_document_service
from superai_review.auth.identity import Identity
from superai_review.auth.types import UserRole
from superai_review.db.models import ReviewSession, User
from superai_review.documents.extractor import DocumentExtractor
from superai_review.documents.isolation import InProcessExtractionRunner
from superai_review.documents.service import DocumentService


class StaticVerifier:
    def __init__(self, identity: Identity) -> None:
        self._identity = identity

    def verify(self, token: str) -> Identity:
        assert token
        return self._identity


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


def add_user_and_review(db: Session) -> tuple[User, ReviewSession]:
    user = User(
        issuer="https://issuer.example",
        subject="user",
        email="user@example.com",
        email_normalized="user@example.com",
        role=UserRole.USER.value,
    )
    db.add(user)
    db.flush()
    review = ReviewSession(user_id=user.id, objective="review")
    db.add(review)
    db.commit()
    db.refresh(user)
    db.refresh(review)
    return user, review


def build_client(db: Session, storage: MemoryStorage) -> TestClient:
    app = create_app(
        identity_verifier=StaticVerifier(
            Identity(
                issuer="https://issuer.example",
                subject="user",
                email="user@example.com",
            )
        )
    )

    def override_db() -> Generator[Session, None, None]:
        yield db

    def override_document_service() -> DocumentService:
        return DocumentService(
            db,
            storage,
            InProcessExtractionRunner(DocumentExtractor(NoopOCR())),
            max_upload_bytes=1024,
        )

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_document_service] = override_document_service
    return TestClient(app)


def test_owner_can_upload_and_list_text_document(db: Session) -> None:
    _, review = add_user_and_review(db)
    storage = MemoryStorage()
    client = build_client(db, storage)
    headers = {"Authorization": "Bearer token"}

    response = client.post(
        f"/api/reviews/{review.id}/documents",
        headers=headers,
        files={"file": ("note.txt", b"hello document", "text/plain")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["content_type"] == "text/plain"
    assert body["extraction_state"] == "COMPLETED"
    assert body["page_count"] == 1

    listed = client.get(f"/api/reviews/{review.id}/documents", headers=headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [body["id"]]
