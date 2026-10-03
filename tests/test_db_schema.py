from superai_review.db import models  # noqa: F401
from superai_review.db.base import Base


def test_foundation_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == {
        "review_sessions",
        "participants",
        "provider_runs",
        "events",
    }


def test_events_table_has_required_audit_columns() -> None:
    events = Base.metadata.tables["events"]
    assert "event_id" in events.c
    assert "schema_version" in events.c
    assert "session_id" in events.c
    assert "timestamp" in events.c
    assert "type" in events.c
    assert "payload" in events.c
