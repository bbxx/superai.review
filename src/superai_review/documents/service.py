from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from superai_review.auth.ownership import require_owned_session
from superai_review.db.models import Document, DocumentSegment, User
from superai_review.documents.errors import DocumentError, DocumentTooLargeError
from superai_review.documents.isolation import ExtractionRunner
from superai_review.documents.mime import detect_mime
from superai_review.documents.storage import DocumentStorage
from superai_review.documents.types import ExtractionState


class DocumentService:
    def __init__(
        self,
        db: Session,
        storage: DocumentStorage,
        extraction_runner: ExtractionRunner,
        *,
        max_upload_bytes: int,
    ) -> None:
        self._db = db
        self._storage = storage
        self._runner = extraction_runner
        self._max_upload_bytes = max_upload_bytes

    def ingest(
        self,
        *,
        user: User,
        session_id: str,
        filename: str,
        declared_content_type: str | None,
        data: bytes,
        password: str | None = None,
    ) -> Document:
        require_owned_session(self._db, user, session_id)
        if len(data) > self._max_upload_bytes:
            raise DocumentTooLargeError("upload exceeds configured size limit")
        content_type = detect_mime(data, filename, declared_content_type)

        document_id = str(uuid4())
        storage_key = document_id
        self._storage.put(storage_key, data)
        document = Document(
            id=document_id,
            session_id=session_id,
            original_name=filename,
            content_type=content_type.value,
            size=len(data),
            sha256=sha256(data).hexdigest(),
            storage_key=storage_key,
            extraction_state=ExtractionState.EXTRACTING.value,
        )
        self._db.add(document)
        self._db.commit()

        try:
            extracted = self._runner.run(data, content_type, password)
        except DocumentError as exc:
            document.extraction_state = ExtractionState.FAILED.value
            document.error_code = exc.code
            self._db.commit()
            raise

        document.page_count = extracted.page_count
        document.ocr_used = extracted.ocr_used
        document.extraction_state = ExtractionState.COMPLETED.value
        document.segments = [
            DocumentSegment(
                ordinal=segment.ordinal,
                page=segment.page,
                kind=segment.kind,
                text=segment.text,
            )
            for segment in extracted.segments
        ]
        self._db.commit()
        self._db.refresh(document)
        return document

    def list_for_session(self, *, user: User, session_id: str) -> list[Document]:
        require_owned_session(self._db, user, session_id)
        return list(
            self._db.scalars(
                select(Document)
                .where(Document.session_id == session_id)
                .order_by(Document.created_at, Document.id)
            )
        )
