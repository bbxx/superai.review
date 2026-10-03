from sqlalchemy import select
from sqlalchemy.orm import Session

from superai_review.db.models import EventRecord
from superai_review.domain.events import EventEnvelope


class AppendOnlyEventRepository:
    """Append/query event storage.

    Mutation methods are intentionally absent: events are an append-only audit stream.
    """

    def append(self, db: Session, event: EventEnvelope) -> EventRecord:
        record = EventRecord(
            event_id=str(event.event_id),
            schema_version=event.schema_version,
            session_id=str(event.session_id),
            timestamp=event.timestamp,
            type=event.type,
            actor=event.actor,
            payload=event.payload,
        )
        db.add(record)
        return record

    def list_for_session(self, db: Session, session_id: str) -> list[EventRecord]:
        statement = (
            select(EventRecord)
            .where(EventRecord.session_id == session_id)
            .order_by(EventRecord.timestamp, EventRecord.event_id)
        )
        return list(db.scalars(statement))
