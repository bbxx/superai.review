import json
from uuid import uuid4

from pydantic import ValidationError

from superai_review.prompts.loader import PromptName, load_prompt
from superai_review.providers.base import (
    ModelProvider,
    ProviderInvalidOutputError,
    ProviderRequest,
    ProviderResult,
    ProviderUsage,
    ValidatedProviderResult,
)
from superai_review.schemas.registry import UnknownOutputSchemaError, validate_output


def _as_mapping(result: ProviderResult) -> dict:
    if isinstance(result.output, dict):
        return result.output
    try:
        decoded = json.loads(result.output)
    except json.JSONDecodeError as exc:
        raise ProviderInvalidOutputError("provider returned invalid JSON") from exc
    if not isinstance(decoded, dict):
        raise ProviderInvalidOutputError("provider output must be a JSON object")
    return decoded


def _validate(request: ProviderRequest, result: ProviderResult) -> dict:
    try:
        parsed = validate_output(request.response_schema, _as_mapping(result))
    except (ValidationError, UnknownOutputSchemaError, ProviderInvalidOutputError) as exc:
        raise ProviderInvalidOutputError("provider output failed schema validation") from exc
    return parsed.model_dump(mode="json")


def _repair_text(output: str | dict) -> str:
    if isinstance(output, str):
        return output[:32768]
    return json.dumps(output, ensure_ascii=False, separators=(",", ":"))[:32768]


class ProviderRunner:
    async def execute(
        self,
        provider: ModelProvider,
        request: ProviderRequest,
    ) -> ValidatedProviderResult:
        first = await provider.run(request)
        self._check_identity(provider, first)
        try:
            structured = _validate(request, first)
        except ProviderInvalidOutputError:
            if provider.capabilities.supports_structured_output or request.repair_attempt:
                raise
            return await self._repair(provider, request, first)

        return ValidatedProviderResult(
            provider=first.provider,
            model=first.model,
            structured_output=structured,
            usage=first.usage,
            latency_ms=first.latency_ms,
            finish_reason=first.finish_reason,
            provider_request_ids=[first.provider_request_id],
            transport_retry_count=first.retry_count,
            warnings=first.warnings,
        )

    async def _repair(
        self,
        provider: ModelProvider,
        request: ProviderRequest,
        first: ProviderResult,
    ) -> ValidatedProviderResult:
        repair_contract = load_prompt(PromptName.REPAIR)
        repair_request = request.model_copy(
            update={
                "request_id": uuid4(),
                "system_contract": f"{request.system_contract}\n\n{repair_contract}",
                "repair_attempt": True,
                "untrusted_previous_output": _repair_text(first.output),
                "idempotency_key": (
                    f"{request.idempotency_key}:repair"
                    if request.idempotency_key
                    else f"{request.request_id}:repair"
                ),
            }
        )
        second = await provider.run(repair_request)
        self._check_identity(provider, second)
        structured = _validate(repair_request, second)
        return ValidatedProviderResult(
            provider=second.provider,
            model=second.model,
            structured_output=structured,
            usage=first.usage + second.usage,
            latency_ms=first.latency_ms + second.latency_ms,
            finish_reason=second.finish_reason,
            provider_request_ids=[first.provider_request_id, second.provider_request_id],
            transport_retry_count=first.retry_count + second.retry_count,
            repair_count=1,
            warnings=[*first.warnings, *second.warnings],
        )

    @staticmethod
    def _check_identity(provider: ModelProvider, result: ProviderResult) -> None:
        if result.provider != provider.provider_id or result.model != provider.model_id:
            raise ProviderInvalidOutputError("provider result identity mismatch")
