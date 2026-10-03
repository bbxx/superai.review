from superai_review.db import models  # noqa: F401
from superai_review.db.base import Base


def test_registered_tables_include_auth_documents_and_evidence() -> None:
    assert set(Base.metadata.tables) == {
        "users",
        "invites",
        "review_sessions",
        "documents",
        "document_segments",
        "evidence",
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


def test_document_schema_never_persists_pdf_password() -> None:
    documents = Base.metadata.tables["documents"]
    assert "password" not in documents.c
    assert "pdf_password" not in documents.c
    assert documents.c.storage_key.unique is True


def test_evidence_references_source_segments_instead_of_duplicating_text() -> None:
    evidence = Base.metadata.tables["evidence"]
    assert "text" not in evidence.c
    assert "segment_id" in evidence.c
    assert "content_hash" in evidence.c
    assert "start_offset" in evidence.c
    assert "end_offset" in evidence.c
