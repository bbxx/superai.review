from collections import defaultdict
from enum import StrEnum
from uuid import UUID

from superai_review.providers.base import (
    ModelProvider,
    ProviderInvalidOutputError,
    ProviderRateLimitError,
    ProviderRequest,
    ProviderResult,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUsage,
)


class FakeScenario(StrEnum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    MALFORMED = "malformed"
    RATE_LIMIT = "rate-limit"
    UNAVAILABLE = "unavailable"
    RETRY_THEN_SUCCESS = "retry-then-success"
    CONTRADICTORY = "contradictory"


class FakeProvider(ModelProvider):
    """Deterministic provider used by unit/integration tests.

    It never performs network I/O and deliberately shares the real provider contract.
    """

    def __init__(
        self,
        scenario: FakeScenario = FakeScenario.SUCCESS,
        *,
        provider_id: str = "fake",
        model_id: str = "fake-v1",
    ) -> None:
        self._scenario = scenario
        self._provider_id = provider_id
        self._model_id = model_id
        self._attempts: defaultdict[UUID, int] = defaultdict(int)
        self._cancelled: set[UUID] = set()

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def model_id(self) -> str:
        return self._model_id

    async def run(self, request: ProviderRequest) -> ProviderResult:
        self._attempts[request.request_id] += 1
        attempt = self._attempts[request.request_id]

        if request.request_id in self._cancelled:
            raise ProviderUnavailableError("request was cancelled")

        if self._scenario is FakeScenario.TIMEOUT:
            raise ProviderTimeoutError("deterministic timeout")
        if self._scenario is FakeScenario.MALFORMED:
            raise ProviderInvalidOutputError("deterministic malformed output")
        if self._scenario is FakeScenario.RATE_LIMIT:
            raise ProviderRateLimitError("deterministic rate limit")
        if self._scenario is FakeScenario.UNAVAILABLE:
            raise ProviderUnavailableError("deterministic provider outage")
        if self._scenario is FakeScenario.RETRY_THEN_SUCCESS and attempt == 1:
            raise ProviderRateLimitError("deterministic first-attempt rate limit")

        output = {
            "scenario": self._scenario.value,
            "role": request.role,
            "stage": request.stage,
            "summary": "Deterministic fake response",
            "position": (
                "contradicts-default"
                if self._scenario is FakeScenario.CONTRADICTORY
                else "supports-default"
            ),
        }
        return ProviderResult(
            provider=self.provider_id,
            model=self.model_id,
            output=output,
            usage=ProviderUsage(
                input_tokens=max(1, len(request.untrusted_source_material.split())),
                output_tokens=12,
            ),
            latency_ms=7,
            finish_reason="stop",
            provider_request_id=f"fake:{request.request_id}",
            retry_count=max(0, attempt - 1),
        )

    async def cancel(self, request_id: UUID) -> bool:
        self._cancelled.add(request_id)
        return True
