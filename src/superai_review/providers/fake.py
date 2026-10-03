from collections import defaultdict
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from superai_review.providers.base import (
    ModelProvider,
    ProviderCapabilities,
    ProviderCostEstimate,
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
    """Deterministic provider used by unit/integration tests."""

    def __init__(
        self,
        scenario: FakeScenario = FakeScenario.SUCCESS,
        *,
        provider_id: str = "fake",
        model_id: str = "fake-v1",
        supports_structured_output: bool = True,
    ) -> None:
        self._scenario = scenario
        self._provider_id = provider_id
        self._model_id = model_id
        self._capabilities = ProviderCapabilities(
            max_context_tokens=32768,
            supports_images=True,
            supports_structured_output=supports_structured_output,
            supports_cancellation=True,
        )
        self._attempts: defaultdict[UUID, int] = defaultdict(int)
        self._cancelled: set[UUID] = set()

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def estimate_cost(self, request: ProviderRequest) -> ProviderCostEstimate:
        del request
        return ProviderCostEstimate(
            estimated_input=Decimal(0),
            estimated_output=Decimal(0),
            estimated_total=Decimal(0),
        )

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

        output = self._output(request)
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

    def _output(self, request: ProviderRequest) -> dict:
        contradictory = self._scenario is FakeScenario.CONTRADICTORY
        if request.response_schema == "proposal-output/v1":
            return {
                "schema_version": "proposal-output/v1",
                "proposal_id": f"fake-{request.role}",
                "role": request.role,
                "summary": "Deterministic fake response",
                "recommended_solution": "Alternative" if contradictory else "Default",
                "reasoning_summary": "Deterministic public rationale.",
                "key_claims": ["contradicts-default" if contradictory else "supports-default"],
                "evidence_refs": [],
                "assumptions": [],
                "risks": [],
                "uncertainties": [],
                "suggested_next_steps": [],
                "confidence": 0.5,
            }
        if request.response_schema == "cross-review/v1":
            return {
                "schema_version": "cross-review/v1",
                "review_id": "fake-review",
                "reviewer_role": request.role,
                "target_proposal_id": "proposal-a",
                "verdict": "APPROVE",
                "strengths": [],
                "issues": [],
                "unsupported_claims": [],
                "missing_points": [],
                "evidence_disagreements": [],
                "recommended_changes": [],
                "severity_summary": "INFO",
            }
        if request.response_schema == "debate-response/v1":
            return {
                "schema_version": "debate-response/v1",
                "topic_id": "topic-1",
                "participant_role": request.role,
                "position": "No material disagreement.",
                "reasoning_summary": "Deterministic public rationale.",
                "evidence_refs": [],
                "changed_position": False,
                "unresolved_points": [],
            }
        if request.response_schema == "final-synthesis/v1":
            return {
                "schema_version": "final-synthesis/v1",
                "final_answer": "Deterministic final answer.",
                "executive_summary": "Summary.",
                "why_this_answer": [],
                "key_evidence": [],
                "rejected_or_avoided_points": [],
                "remaining_uncertainties": [],
                "recommended_next_steps": [],
                "consensus_summary": "Deterministic consensus.",
                "quality_flags": [],
            }
        raise ProviderInvalidOutputError("unknown fake response schema")
