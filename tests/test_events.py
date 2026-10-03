from datetime import timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from superai_review.domain.events import EventEnvelope


def test_event_has_version_id_session_and_utc_timestamp() -> None:
    session_id = uuid4()
    event = EventEnvelope(session_id=session_id, type="review.created", payload={"mode": "standard"})

    assert event.schema_version == "1"
    assert event.event_id
    assert event.session_id == session_id
    assert event.timestamp.utcoffset() == timezone.utc.utcoffset(event.timestamp)


@pytest.mark.parametrize(
    "payload",
    [
        {"api_key": "nope"},
        {"nested": {"auth_token": "nope"}},
        {"full_prompt": "nope"},
        {"document_content": "nope"},
    ],
)
def test_event_rejects_sensitive_or_full_content_keys(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        EventEnvelope(session_id=uuid4(), type="provider.completed", payload=payload)


def test_event_rejects_document_sized_strings() -> None:
    with pytest.raises(ValidationError):
        EventEnvelope(
            session_id=uuid4(),
            type="provider.completed",
            payload={"summary": "x" * 5000},
        )
