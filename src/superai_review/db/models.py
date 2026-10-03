from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from superai_review.db.base import Base
from superai_review.domain.states import ReviewState


def _uuid() -> str:
    return str(uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ReviewSession(Base):
    __tablename__ = "review_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(240), nullable=True)
    objective: Mapped[str] = mapped_column(Text, default="")
    constraints: Mapped[dict] = mapped_column(JSON, default=dict)
    language: Mapped[str] = mapped_column(String(16), default="pl")
    mode: Mapped[str] = mapped_column(String(24), default="standard")
    sensitivity: Mapped[str] = mapped_column(String(32), default="NORMAL")
    state: Mapped[str] = mapped_column(String(32), default=ReviewState.CREATED.value, index=True)
    config_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    failure_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    participants: Mapped[list["Participant"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    provider_runs: Mapped[list["ProviderRun"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    events: Mapped[list["EventRecord"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("review_sessions.id", ondelete="CASCADE"), index=True
    )
    logical_role: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(120))
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    session: Mapped[ReviewSession] = relationship(back_populates="participants")


class ProviderRun(Base):
    __tablename__ = "provider_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("review_sessions.id", ondelete="CASCADE"), index=True
    )
    participant_id: Mapped[str | None] = mapped_column(
        ForeignKey("participants.id", ondelete="SET NULL"), nullable=True
    )
    stage: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(32), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("0"))
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_request_id: Mapped[str | None] = mapped_column(String(240), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)

    session: Mapped[ReviewSession] = relationship(back_populates="provider_runs")


class EventRecord(Base):
    __tablename__ = "events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    schema_version: Mapped[str] = mapped_column(String(16))
    session_id: Mapped[str] = mapped_column(
        ForeignKey("review_sessions.id", ondelete="CASCADE"), index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    type: Mapped[str] = mapped_column(String(120), index=True)
    actor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)

    session: Mapped[ReviewSession] = relationship(back_populates="events")
