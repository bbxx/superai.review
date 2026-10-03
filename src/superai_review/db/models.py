from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from superai_review.db.base import Base
from superai_review.documents.types import ExtractionState
from superai_review.domain.states import ReviewState


def _uuid() -> str:
    return str(uuid4())


def _utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("issuer", "subject", name="uq_users_issuer_subject"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    issuer: Mapped[str] = mapped_column(String(500))
    subject: Mapped[str] = mapped_column(String(500))
    email: Mapped[str] = mapped_column(String(320))
    email_normalized: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    role: Mapped[str] = mapped_column(String(32), default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sessions: Mapped[list["ReviewSession"]] = relationship(back_populates="owner")


class Invite(Base):
    __tablename__ = "invites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email_normalized: Mapped[str] = mapped_column(String(320), index=True)
    role: Mapped[str] = mapped_column(String(32), default="user")
    invited_by_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReviewSession(Base):
    __tablename__ = "review_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
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

    owner: Mapped[User] = relationship(back_populates="sessions")
    documents: Mapped[list["Document"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    participants: Mapped[list["Participant"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    provider_runs: Mapped[list["ProviderRun"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    events: Mapped[list["EventRecord"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("review_sessions.id", ondelete="CASCADE"), index=True
    )
    original_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    storage_key: Mapped[str] = mapped_column(String(80), unique=True)
    extraction_state: Mapped[str] = mapped_column(
        String(32), default=ExtractionState.STORED.value, index=True
    )
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ocr_used: Mapped[bool] = mapped_column(Boolean, default=False)
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    session: Mapped[ReviewSession] = relationship(back_populates="documents")
    segments: Mapped[list["DocumentSegment"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentSegment.ordinal",
    )


class DocumentSegment(Base):
    __tablename__ = "document_segments"
    __table_args__ = (
        UniqueConstraint("document_id", "ordinal", name="uq_document_segments_document_ordinal"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kind: Mapped[str] = mapped_column(String(40))
    text: Mapped[str] = mapped_column(Text)

    document: Mapped[Document] = relationship(back_populates="segments")


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
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal(0))
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
