from typing import Annotated

from fastapi import Depends

from superai_review.api.dependencies import DbDependency
from superai_review.config import get_settings
from superai_review.evidence.service import EvidenceService


def get_evidence_service(db: DbDependency) -> EvidenceService:
    settings = get_settings()
    return EvidenceService(
        db,
        chunk_chars=settings.evidence_chunk_chars,
        retrieval_max_items=settings.retrieval_max_items,
        retrieval_max_chars=settings.retrieval_max_chars,
    )


EvidenceServiceDependency = Annotated[EvidenceService, Depends(get_evidence_service)]
