"""add result and score to code_submissions

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-18

Adds two columns to ``code_submissions`` that were required by the
Prompt-15 database-design specification:

* ``result``  – JSONB, nullable.  Stores the full scan result payload
  (issues array + scoreResult object) produced by the scanner so that
  results are persisted and queryable without re-running the scan.

* ``score``   – INTEGER, nullable.  The numeric security score (0–100)
  extracted from the scan result for quick filtering / sorting without
  having to parse the JSONB blob.

Both columns are nullable so that existing rows created before this
migration are unaffected.

An index on ``score`` is added to support efficient range queries such
as ``WHERE score < 50`` (critical-risk submissions).
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "code_submissions",
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "code_submissions",
        sa.Column("score", sa.Integer(), nullable=True),
    )
    op.create_index("ix_code_submissions_score", "code_submissions", ["score"])


def downgrade() -> None:
    op.drop_index("ix_code_submissions_score", table_name="code_submissions")
    op.drop_column("code_submissions", "score")
    op.drop_column("code_submissions", "result")
