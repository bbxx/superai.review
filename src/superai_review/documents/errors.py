class DocumentError(RuntimeError):
    code = "document_error"


class InvalidFilenameError(DocumentError):
    code = "invalid_filename"


class UnsupportedDocumentError(DocumentError):
    code = "unsupported_document"


class DeclaredTypeMismatchError(DocumentError):
    code = "declared_type_mismatch"


class DocumentTooLargeError(DocumentError):
    code = "document_too_large"


class UnsafeDocumentError(DocumentError):
    code = "unsafe_document"


class PasswordRequiredError(DocumentError):
    code = "password_required"


class InvalidPasswordError(DocumentError):
    code = "invalid_password"


class OCRUnavailableError(DocumentError):
    code = "ocr_unavailable"


class ExtractionTimeoutError(DocumentError):
    code = "extraction_timeout"


class ExtractionFailedError(DocumentError):
    code = "extraction_failed"
