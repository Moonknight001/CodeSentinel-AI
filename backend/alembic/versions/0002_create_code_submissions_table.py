"""create code_submissions table

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-17
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "code_submissions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
        ),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("language", sa.String(length=50), nullable=False),
        sa.Column("raw_code", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_code_submissions_user_id", "code_submissions", ["user_id"])
    op.create_index("ix_code_submissions_language", "code_submissions", ["language"])


def downgrade() -> None:
    op.drop_index("ix_code_submissions_language", table_name="code_submissions")
    op.drop_index("ix_code_submissions_user_id", table_name="code_submissions")
    op.drop_table("code_submissions")
