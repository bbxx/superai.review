import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

_FORBIDDEN_EVENT_KEYS = frozenset(
    {
        "api_key",
        "provider_api_key",
        "auth_token",
        "access_token",
        "refresh_token",
        "password",
        "secret",
        "full_prompt",
        "document_content",
        "raw_document",
        "source_text",
    }
)
_MAX_EVENT_STRING_LENGTH = 4096
_MAX_EVENT_PAYLOAD_BYTES = 16 * 1024


def _validate_payload_node(value: Any, path: str = "payload") -> None:
    if isinstance(value, dict):
        for raw_key, child in value.items():
            key = str(raw_key).casefold()
            if key in _FORBIDDEN_EVENT_KEYS:
                raise ValueError(f"forbidden event payload key at {path}.{raw_key}")
            _validate_payload_node(child, f"{path}.{raw_key}")
        return

    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _validate_payload_node(child, f"{path}[{index}]")
        return

    if isinstance(value, str) and len(value) > _MAX_EVENT_STRING_LENGTH:
        raise ValueError(f"event payload string too large at {path}")


class EventEnvelope(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    schema_version: str = "1"
    session_id: UUID
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    type: str = Field(min_length=1, max_length=120)
    actor: str | None = Field(default=None, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("event timestamp must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("payload")
    @classmethod
    def payload_must_be_safe(cls, value: dict[str, Any]) -> dict[str, Any]:
        _validate_payload_node(value)
        serialized = json.dumps(value, default=str, separators=(",", ":")).encode()
        if len(serialized) > _MAX_EVENT_PAYLOAD_BYTES:
            raise ValueError("event payload exceeds safe size limit")
        return value
