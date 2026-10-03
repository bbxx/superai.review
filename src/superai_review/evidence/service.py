from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from superai_review.auth.ownership import ResourceNotFoundError, require_owned_session
from superai_review.db.models import Document, EvidenceRecord, User
from superai_review.documents.types import ExtractionState
from superai_review.evidence.errors import (
    EvidenceIntegrityError,
    EvidenceUnavailableError,
    InvalidEvidenceReferenceError,
    RetrievalLimitError,
)
from superai_review.evidence.schemas import EvidenceView


def _chunk_ranges(text: str, max_chars: int) -> list[tuple[int, int]]:
    if not text:
        return []
    ranges: list[tuple[int, int]] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + max_chars, length)
        if end < length:
            floor = start + max_chars // 2
            newline = text.rfind("\n", floor, end)
            space = text.rfind(" ", floor, end)
            boundary = max(newline, space)
            if boundary > start:
                end = boundary + 1
        ranges.append((start, end))
        start = end
    return ranges


class EvidenceService:
    def __init__(
        self,
        db: Session,
        *,
        chunk_chars: int = 4000,
        retrieval_max_items: int = 12,
        retrieval_max_chars: int = 16000,
    ) -> None:
        self._db = db
        self._chunk_chars = chunk_chars
        self._retrieval_max_items = retrieval_max_items
        self._retrieval_max_chars = retrieval_max_chars

    def materialize_document(self, document: Document) -> list[EvidenceRecord]:
        if document.extraction_state != ExtractionState.COMPLETED.value:
            raise EvidenceUnavailableError("document extraction is not complete")

        existing = self._records_for_document(document.id)
        if existing:
            self._verify_records(existing)
            return existing

        records: list[EvidenceRecord] = []
        ordinal = 0
        for segment in sorted(document.segments, key=lambda item: item.ordinal):
            for chunk_index, (start, end) in enumerate(
                _chunk_ranges(segment.text, self._chunk_chars)
            ):
                text = segment.text[start:end]
                page_number = segment.page or 0
                evidence_id = f"{document.id}:p{page_number:04d}:e{ordinal:05d}"
                records.append(
                    EvidenceRecord(
                        id=evidence_id,
                        document_id=document.id,
                        segment_id=segment.id,
                        ordinal=ordinal,
                        chunk_index=chunk_index,
                        start_offset=start,
                        end_offset=end,
                        page=segment.page,
                        section=segment.kind,
                        content_hash=sha256(text.encode("utf-8")).hexdigest(),
                        metadata_json={},
                    )
                )
                ordinal += 1

        self._db.add_all(records)
        self._db.commit()
        return self._records_for_document(document.id)

    def list_for_document(
        self,
        *,
        user: User,
        session_id: str,
        document_id: str,
    ) -> list[EvidenceView]:
        require_owned_session(self._db, user, session_id)
        document = self._db.get(Document, document_id)
        if document is None or document.session_id != session_id:
            raise ResourceNotFoundError("document not found")
        records = self.materialize_document(document)
        return [EvidenceView.from_record(record) for record in records]

    def list_for_session(self, *, user: User, session_id: str) -> list[EvidenceView]:
        require_owned_session(self._db, user, session_id)
        documents = list(
            self._db.scalars(
                select(Document)
                .where(Document.session_id == session_id)
                .order_by(Document.created_at, Document.id)
            )
        )
        for document in documents:
            if document.extraction_state == ExtractionState.COMPLETED.value:
                self.materialize_document(document)

        statement = (
            select(EvidenceRecord)
            .join(Document, EvidenceRecord.document_id == Document.id)
            .where(Document.session_id == session_id)
            .options(selectinload(EvidenceRecord.segment))
            .order_by(Document.created_at, Document.id, EvidenceRecord.ordinal)
        )
        return [EvidenceView.from_record(record) for record in self._db.scalars(statement)]

    def validate_refs(
        self,
        *,
        user: User,
        session_id: str,
        evidence_ids: list[str],
    ) -> list[EvidenceView]:
        require_owned_session(self._db, user, session_id)
        ordered_ids = list(dict.fromkeys(evidence_ids))
        if not ordered_ids:
            return []

        statement = (
            select(EvidenceRecord)
            .join(Document, EvidenceRecord.document_id == Document.id)
            .where(Document.session_id == session_id, EvidenceRecord.id.in_(ordered_ids))
            .options(selectinload(EvidenceRecord.segment))
        )
        by_id = {record.id: record for record in self._db.scalars(statement)}
        missing = [evidence_id for evidence_id in ordered_ids if evidence_id not in by_id]
        if missing:
            raise InvalidEvidenceReferenceError(missing)
        return [EvidenceView.from_record(by_id[evidence_id]) for evidence_id in ordered_ids]

    def retrieve(
        self,
        *,
        user: User,
        session_id: str,
        evidence_ids: list[str],
    ) -> list[EvidenceView]:
        if len(evidence_ids) > self._retrieval_max_items:
            raise RetrievalLimitError("retrieval item limit exceeded")
        evidence = self.validate_refs(
            user=user,
            session_id=session_id,
            evidence_ids=evidence_ids,
        )
        if sum(len(item.text) for item in evidence) > self._retrieval_max_chars:
            raise RetrievalLimitError("retrieval character limit exceeded")
        return evidence

    def _records_for_document(self, document_id: str) -> list[EvidenceRecord]:
        statement = (
            select(EvidenceRecord)
            .where(EvidenceRecord.document_id == document_id)
            .options(selectinload(EvidenceRecord.segment))
            .order_by(EvidenceRecord.ordinal)
        )
        return list(self._db.scalars(statement))

    @staticmethod
    def _verify_records(records: list[EvidenceRecord]) -> None:
        for expected_ordinal, record in enumerate(records):
            if record.ordinal != expected_ordinal:
                raise EvidenceIntegrityError("evidence ordinal sequence is corrupted")
            actual_hash = sha256(record.text.encode("utf-8")).hexdigest()
            if actual_hash != record.content_hash:
                raise EvidenceIntegrityError("evidence content hash mismatch")
