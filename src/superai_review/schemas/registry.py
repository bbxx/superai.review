from typing import Any

from pydantic import BaseModel, ValidationError

from superai_review.schemas.model_outputs import (
    CrossReviewOutput,
    DebateResponseOutput,
    FinalSynthesisOutput,
    ProposalOutput,
)

_SCHEMA_TYPES: dict[str, type[BaseModel]] = {
    "proposal-output/v1": ProposalOutput,
    "cross-review/v1": CrossReviewOutput,
    "debate-response/v1": DebateResponseOutput,
    "final-synthesis/v1": FinalSynthesisOutput,
}


class UnknownOutputSchemaError(ValueError):
    pass


def schema_names() -> frozenset[str]:
    return frozenset(_SCHEMA_TYPES)


def validate_output(schema_name: str, payload: dict[str, Any]) -> BaseModel:
    schema_type = _SCHEMA_TYPES.get(schema_name)
    if schema_type is None:
        raise UnknownOutputSchemaError(f"unknown structured output schema: {schema_name}")
    try:
        return schema_type.model_validate(payload)
    except ValidationError:
        raise
