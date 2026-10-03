from superai_review.db import models  # noqa: F401
from superai_review.db.base import Base


def test_registered_tables_include_auth_foundation() -> None:
    assert set(Base.metadata.tables) == {
        "users",
        "invites",
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


def test_review_session_requires_owner_foreign_key() -> None:
    sessions = Base.metadata.tables["review_sessions"]
    assert sessions.c.user_id.nullable is False
    foreign_keys = {fk.target_fullname for fk in sessions.c.user_id.foreign_keys}
    assert foreign_keys == {"users.id"}
