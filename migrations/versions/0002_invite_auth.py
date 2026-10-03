"""Invite-only OIDC users.

Revision ID: 0002_invite_auth
Revises: 0001_foundation
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_invite_auth"
down_revision: str | None = "0001_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("issuer", sa.String(length=500), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("email_normalized", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=240), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("issuer", "subject", name="uq_users_issuer_subject"),
        sa.UniqueConstraint("email_normalized", name="uq_users_email_normalized"),
    )
    op.create_index("ix_users_email_normalized", "users", ["email_normalized"])

    op.create_table(
        "invites",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email_normalized", sa.String(length=320), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column(
            "invited_by_user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "used_by_user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_invites_email_normalized", "invites", ["email_normalized"])
    op.create_index("ix_invites_invited_by_user_id", "invites", ["invited_by_user_id"])

    with op.batch_alter_table("review_sessions") as batch:
        batch.alter_column(
            "user_id",
            existing_type=sa.String(length=120),
            type_=sa.String(length=36),
            nullable=False,
        )
        batch.create_foreign_key(
            "fk_review_sessions_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table("review_sessions") as batch:
        batch.drop_constraint("fk_review_sessions_user_id_users", type_="foreignkey")
        batch.alter_column(
            "user_id",
            existing_type=sa.String(length=36),
            type_=sa.String(length=120),
            nullable=True,
        )

    op.drop_table("invites")
    op.drop_table("users")
