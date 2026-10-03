"""Foundation schema.

Revision ID: 0001_foundation
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "review_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=120), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=True),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("constraints", sa.JSON(), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("mode", sa.String(length=24), nullable=False),
        sa.Column("sensitivity", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("config_snapshot", sa.JSON(), nullable=False),
        sa.Column("failure_code", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_review_sessions_user_id", "review_sessions", ["user_id"])
    op.create_index("ix_review_sessions_state", "review_sessions", ["state"])

    op.create_table(
        "participants",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(length=36),
            sa.ForeignKey("review_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("logical_role", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_participants_session_id", "participants", ["session_id"])

    op.create_table(
        "provider_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(length=36),
            sa.ForeignKey("review_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "participant_id",
            sa.String(length=36),
            sa.ForeignKey("participants.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("estimated_cost", sa.Numeric(12, 6), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("provider_request_id", sa.String(length=240), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=120), nullable=True),
    )
    op.create_index("ix_provider_runs_session_id", "provider_runs", ["session_id"])
    op.create_index("ix_provider_runs_stage", "provider_runs", ["stage"])
    op.create_index("ix_provider_runs_status", "provider_runs", ["status"])

    op.create_table(
        "events",
        sa.Column("event_id", sa.String(length=36), primary_key=True),
        sa.Column("schema_version", sa.String(length=16), nullable=False),
        sa.Column(
            "session_id",
            sa.String(length=36),
            sa.ForeignKey("review_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("type", sa.String(length=120), nullable=False),
        sa.Column("actor", sa.String(length=120), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    op.create_index("ix_events_session_id", "events", ["session_id"])
    op.create_index("ix_events_timestamp", "events", ["timestamp"])
    op.create_index("ix_events_type", "events", ["type"])


def downgrade() -> None:
    op.drop_table("events")
    op.drop_table("provider_runs")
    op.drop_table("participants")
    op.drop_table("review_sessions")
