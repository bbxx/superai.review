from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ProviderCapabilities(BaseModel):
    max_context_tokens: int = Field(gt=0)
    supports_images: bool = False
    supports_structured_output: bool = False
    supports_cancellation: bool = False


class ProviderCostEstimate(BaseModel):
    currency: str = "USD"
    estimated_input: Decimal = Field(default=Decimal(0), ge=0)
    estimated_output: Decimal = Field(default=Decimal(0), ge=0)
    estimated_total: Decimal = Field(default=Decimal(0), ge=0)


class ProviderUsage(BaseModel):
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)

    def __add__(self, other: "ProviderUsage") -> "ProviderUsage":
        return ProviderUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
        )


class ProviderRequest(BaseModel):
    request_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    stage: str
    role: str
    system_contract: str
    trusted_objective: str
    untrusted_source_material: str
    response_schema: str
    token_budget: int = Field(default=4096, gt=0)
    timeout_seconds: float = Field(default=60.0, gt=0)
    trace_id: str
    idempotency_key: str | None = None
    repair_attempt: bool = False
    untrusted_previous_output: str | None = Field(default=None, max_length=32768)


class ProviderResult(BaseModel):
    provider: str
    model: str
    output: str | dict[str, Any]
    usage: ProviderUsage = Field(default_factory=ProviderUsage)
    latency_ms: int = Field(ge=0)
    finish_reason: str
    provider_request_id: str
    retry_count: int = Field(default=0, ge=0)
    warnings: list[str] = Field(default_factory=list)


class ValidatedProviderResult(BaseModel):
    provider: str
    model: str
    structured_output: dict[str, Any]
    usage: ProviderUsage
    latency_ms: int = Field(ge=0)
    finish_reason: str
    provider_request_ids: list[str]
    transport_retry_count: int = Field(default=0, ge=0)
    repair_count: int = Field(default=0, ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)


class ProviderError(RuntimeError):
    code = "provider_error"


class ProviderTimeoutError(ProviderError):
    code = "timeout"


class ProviderRateLimitError(ProviderError):
    code = "rate_limit"


class ProviderUnavailableError(ProviderError):
    code = "unavailable"


class ProviderInvalidOutputError(ProviderError):
    code = "invalid_output"


class ModelProvider(ABC):
    @property
    @abstractmethod
    def provider_id(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def model_id(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        raise NotImplementedError

    @abstractmethod
    def estimate_cost(self, request: ProviderRequest) -> ProviderCostEstimate:
        raise NotImplementedError

    @abstractmethod
    async def run(self, request: ProviderRequest) -> ProviderResult:
        raise NotImplementedError

    @abstractmethod
    async def cancel(self, request_id: UUID) -> bool:
        raise NotImplementedError
