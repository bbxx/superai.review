class EvidenceError(RuntimeError):
    pass


class EvidenceUnavailableError(EvidenceError):
    pass


class EvidenceIntegrityError(EvidenceError):
    pass


class InvalidEvidenceReferenceError(EvidenceError):
    def __init__(self, missing_ids: list[str]) -> None:
        self.missing_ids = missing_ids
        super().__init__("invalid evidence reference")


class RetrievalLimitError(EvidenceError):
    pass
