import asyncio
from uuid import uuid4

import pytest

from superai_review.providers.base import (
    ProviderInvalidOutputError,
    ProviderRateLimitError,
    ProviderRequest,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from superai_review.providers.fake import FakeProvider, FakeScenario


def request() -> ProviderRequest:
    return ProviderRequest(
        session_id=uuid4(),
        stage="PROPOSING",
        role="Analyst",
        system_contract="Return structured output.",
        trusted_objective="Review the material.",
        untrusted_source_material="Untrusted source text.",
        response_schema="proposal-output/v1",
        trace_id="trace-1",
    )


def test_success_is_deterministic() -> None:
    provider = FakeProvider(FakeScenario.SUCCESS)
    result = asyncio.run(provider.run(request()))

    assert result.provider == "fake"
    assert result.model == "fake-v1"
    assert result.output["position"] == "supports-default"
    assert result.latency_ms == 7


@pytest.mark.parametrize(
    ("scenario", "error"),
    [
        (FakeScenario.TIMEOUT, ProviderTimeoutError),
        (FakeScenario.MALFORMED, ProviderInvalidOutputError),
        (FakeScenario.RATE_LIMIT, ProviderRateLimitError),
        (FakeScenario.UNAVAILABLE, ProviderUnavailableError),
    ],
)
def test_failure_scenarios(scenario: FakeScenario, error: type[Exception]) -> None:
    provider = FakeProvider(scenario)
    with pytest.raises(error):
        asyncio.run(provider.run(request()))


def test_retry_then_success_uses_same_logical_request() -> None:
    provider = FakeProvider(FakeScenario.RETRY_THEN_SUCCESS)
    model_request = request()

    with pytest.raises(ProviderRateLimitError):
        asyncio.run(provider.run(model_request))

    result = asyncio.run(provider.run(model_request))
    assert result.retry_count == 1
    assert result.provider_request_id == f"fake:{model_request.request_id}"


def test_contradictory_scenario_is_explicit() -> None:
    provider = FakeProvider(FakeScenario.CONTRADICTORY)
    result = asyncio.run(provider.run(request()))
    assert result.output["position"] == "contradicts-default"


def test_cancelled_request_does_not_complete() -> None:
    provider = FakeProvider()
    model_request = request()
    assert asyncio.run(provider.cancel(model_request.request_id)) is True
    with pytest.raises(ProviderUnavailableError):
        asyncio.run(provider.run(model_request))
