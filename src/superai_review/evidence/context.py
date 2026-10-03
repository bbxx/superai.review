import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from superai_review.auth.ownership import require_owned_session
from superai_review.db.models import Document, User
from superai_review.documents.types import ExtractionState
from superai_review.evidence.schemas import (
    ContextPack,
    DocumentContextSummary,
    EvidenceIndexItem,
    EvidenceView,
)
from superai_review.evidence.service import EvidenceService

_WORD_RE = re.compile(r"[\wąćęłńóśźż]{3,}", re.IGNORECASE)
_DATE_RE = re.compile(r"\b(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}-\d{2}-\d{2})\b")
_NUMBER_RE = re.compile(r"\b\d+(?:[\s.,]\d+)*(?:\s?%)?\b")
_NAME_RE = re.compile(
    r"\b[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,}"
    r"(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,}){1,3}\b"
)

_TASK_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("complaint", ("reklamac", "odrzucen", "complaint", "warranty", "dealer")),
    ("contract", ("umow", "contract", "agreement", "clause")),
    ("offer", ("ofert", "proposal", "quotation", "quote")),
    ("recruitment", ("cv", "resume", "rekrut", "job application")),
    ("technical", ("specyfik", "documentation", "technical", "log", "api")),
)


def _unique_matches(pattern: re.Pattern[str], texts: list[str], limit: int = 30) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for text in texts:
        for match in pattern.findall(text):
            value = match.strip()
            key = value.casefold()
            if key not in seen:
                seen.add(key)
                result.append(value)
                if len(result) >= limit:
                    return result
    return result


def _task_type(objective: str) -> str:
    normalized = objective.casefold()
    for task_type, keywords in _TASK_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return task_type
    return "general"


def _relevance_score(item: EvidenceView, objective_terms: set[str]) -> int:
    text = item.text.casefold()
    return sum(text.count(term) for term in objective_terms)


def _select_evidence(
    evidence: list[EvidenceView],
    objective: str,
    max_chars: int,
) -> list[EvidenceView]:
    if sum(len(item.text) for item in evidence) <= max_chars:
        return evidence
    if not evidence:
        return []

    objective_terms = set(_WORD_RE.findall(objective.casefold()))
    coverage = [0, len(evidence) // 2, len(evidence) - 1]
    ranked = sorted(
        range(len(evidence)),
        key=lambda index: (-_relevance_score(evidence[index], objective_terms), index),
    )

    selected_indices: list[int] = []
    used_chars = 0
    for index in dict.fromkeys([*coverage, *ranked]):
        item_chars = len(evidence[index].text)
        if used_chars + item_chars > max_chars:
            continue
        selected_indices.append(index)
        used_chars += item_chars

    return [evidence[index] for index in sorted(selected_indices)]


class ContextBuilder:
    def __init__(self, db: Session, evidence_service: EvidenceService) -> None:
        self._db = db
        self._evidence = evidence_service

    def build(
        self,
        *,
        user: User,
        session_id: str,
        max_source_chars: int,
    ) -> ContextPack:
        review = require_owned_session(self._db, user, session_id)
        documents = list(
            self._db.scalars(
                select(Document)
                .where(Document.session_id == session_id)
                .order_by(Document.created_at, Document.id)
            )
        )
        evidence = self._evidence.list_for_session(user=user, session_id=session_id)
        by_document: dict[str, list[EvidenceView]] = {}
        for item in evidence:
            by_document.setdefault(item.document_id, []).append(item)

        warnings: list[str] = []
        for document in documents:
            if document.extraction_state != ExtractionState.COMPLETED.value:
                warnings.append(
                    f"document:{document.id}:extraction_{document.extraction_state.casefold()}"
                )
            elif not by_document.get(document.id):
                warnings.append(f"document:{document.id}:no_evidence")
            if document.ocr_used:
                warnings.append(f"document:{document.id}:ocr_used")

        selected = _select_evidence(evidence, review.objective, max_source_chars)
        source_chars = sum(len(item.text) for item in evidence)
        all_text = [item.text for item in evidence]

        return ContextPack(
            session_id=review.id,
            objective=review.objective,
            constraints=review.constraints,
            language=review.language,
            detected_task_type=_task_type(review.objective),
            document_summaries=[
                DocumentContextSummary.build(document, by_document.get(document.id, []))
                for document in documents
            ],
            evidence_index=[
                EvidenceIndexItem(
                    evidence_id=item.evidence_id,
                    document_id=item.document_id,
                    page=item.page,
                    section=item.section,
                    ordinal=item.ordinal,
                    content_hash=item.content_hash,
                    char_count=len(item.text),
                )
                for item in evidence
            ],
            selected_evidence=selected,
            important_dates=_unique_matches(_DATE_RE, all_text),
            important_numbers=_unique_matches(_NUMBER_RE, all_text),
            important_names=_unique_matches(_NAME_RE, all_text),
            extraction_warnings=warnings,
            source_char_count=source_chars,
            selection_budget_chars=max_source_chars,
            source_complete=len(selected) == len(evidence),
            omitted_evidence_count=len(evidence) - len(selected),
            retrieval_required=len(selected) != len(evidence),
        )
