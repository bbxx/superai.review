from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ProviderUsage(BaseModel):
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)


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


class ProviderResult(BaseModel):
    provider: str
    model: str
    output: dict[str, Any]
    usage: ProviderUsage = Field(default_factory=ProviderUsage)
    latency_ms: int = Field(ge=0)
    finish_reason: str
    provider_request_id: str
    retry_count: int = Field(default=0, ge=0)
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

    @abstractmethod
    async def run(self, request: ProviderRequest) -> ProviderResult:
        raise NotImplementedError

    @abstractmethod
    async def cancel(self, request_id: UUID) -> bool:
        raise NotImplementedError
