"""Stable evidence records.

Revision ID: 0004_evidence
Revises: 0003_document_ingestion
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_evidence"
down_revision: str | None = "0003_document_ingestion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(length=36),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "segment_id",
            sa.String(length=36),
            sa.ForeignKey("document_segments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("section", sa.String(length=80), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("document_id", "ordinal", name="uq_evidence_document_ordinal"),
        sa.UniqueConstraint("segment_id", "chunk_index", name="uq_evidence_segment_chunk"),
    )
    op.create_index("ix_evidence_document_id", "evidence", ["document_id"])
    op.create_index("ix_evidence_segment_id", "evidence", ["segment_id"])


def downgrade() -> None:
    op.drop_table("evidence")
