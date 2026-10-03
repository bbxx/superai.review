from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from superai_review.api.dependencies import CurrentUserDependency
from superai_review.api.document_dependencies import DocumentServiceDependency
from superai_review.api.evidence_dependencies import EvidenceServiceDependency
from superai_review.auth.ownership import ResourceNotFoundError
from superai_review.config import get_settings
from superai_review.documents.errors import (
    DeclaredTypeMismatchError,
    DocumentTooLargeError,
    ExtractionFailedError,
    ExtractionTimeoutError,
    InvalidFilenameError,
    InvalidPasswordError,
    OCRUnavailableError,
    PasswordRequiredError,
    UnsafeDocumentError,
    UnsupportedDocumentError,
)
from superai_review.documents.schemas import DocumentView
from superai_review.evidence.errors import EvidenceUnavailableError
from superai_review.evidence.schemas import EvidenceView

router = APIRouter(prefix="/api/reviews/{session_id}/documents", tags=["documents"])


async def _read_limited(upload: UploadFile, limit: int) -> bytes:
    data = bytearray()
    while chunk := await upload.read(1024 * 1024):
        data.extend(chunk)
        if len(data) > limit:
            raise DocumentTooLargeError("upload exceeds configured size limit")
    return bytes(data)


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, DocumentTooLargeError):
        return HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=exc.code)
    if isinstance(exc, (UnsupportedDocumentError, DeclaredTypeMismatchError)):
        return HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=exc.code)
    if isinstance(exc, (InvalidFilenameError, UnsafeDocumentError)):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.code)
    if isinstance(exc, (PasswordRequiredError, InvalidPasswordError, ExtractionFailedError)):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.code)
    if isinstance(exc, OCRUnavailableError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.code)
    if isinstance(exc, ExtractionTimeoutError):
        return HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=exc.code)
    if isinstance(exc, ResourceNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="document_error")


@router.post("", response_model=DocumentView, status_code=status.HTTP_201_CREATED)
async def upload_document(
    session_id: str,
    user: CurrentUserDependency,
    service: DocumentServiceDependency,
    file: Annotated[UploadFile, File()],
    password: Annotated[str | None, Form()] = None,
) -> DocumentView:
    try:
        data = await _read_limited(file, get_settings().max_upload_bytes)
        document = await run_in_threadpool(
            service.ingest,
            user=user,
            session_id=session_id,
            filename=file.filename or "",
            declared_content_type=file.content_type,
            data=data,
            password=password,
        )
    except (
        DeclaredTypeMismatchError,
        DocumentTooLargeError,
        ExtractionFailedError,
        ExtractionTimeoutError,
        InvalidFilenameError,
        InvalidPasswordError,
        OCRUnavailableError,
        PasswordRequiredError,
        ResourceNotFoundError,
        UnsafeDocumentError,
        UnsupportedDocumentError,
    ) as exc:
        raise _http_error(exc) from exc
    finally:
        await file.close()
    return DocumentView.from_model(document)


@router.get("", response_model=list[DocumentView])
def list_documents(
    session_id: str,
    user: CurrentUserDependency,
    service: DocumentServiceDependency,
) -> list[DocumentView]:
    try:
        documents = service.list_for_session(user=user, session_id=session_id)
    except ResourceNotFoundError as exc:
        raise _http_error(exc) from exc
    return [DocumentView.from_model(document) for document in documents]


@router.get("/{document_id}/evidence", response_model=list[EvidenceView])
def document_evidence(
    session_id: str,
    document_id: str,
    user: CurrentUserDependency,
    evidence_service: EvidenceServiceDependency,
) -> list[EvidenceView]:
    try:
        return evidence_service.list_for_document(
            user=user,
            session_id=session_id,
            document_id=document_id,
        )
    except ResourceNotFoundError as exc:
        raise _http_error(exc) from exc
    except EvidenceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="evidence_unavailable",
        ) from exc
