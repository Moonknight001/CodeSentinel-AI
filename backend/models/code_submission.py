"""
CodeSubmission ORM model.

Represents a raw-code analysis submission stored in PostgreSQL.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class CodeSubmission(Base):
    __tablename__ = "code_submissions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_new_uuid
    )

    # Optional FK – submissions may come from anonymous callers or authenticated users
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # The submitted source code
    language: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    raw_code: Mapped[str] = mapped_column(Text, nullable=False)

    # Processing state (pending → in_progress → completed / failed)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")

    # Timestamps
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<CodeSubmission id={self.id!r} language={self.language!r}"
            f" status={self.status!r}>"
        )
