from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from vbank.shared.database import Base


class IdempotencyEntry(Base):
    __tablename__ = "idempotency_entry"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_scope",
            "endpoint",
            "idempotency_key",
            name="uq_idempotency_entry_scope_endpoint_key",
        ),
        CheckConstraint("idempotency_scope <> ''", name="ck_idempotency_entry_scope_not_empty"),
        Index("ix_idempotency_entry_created_at", "created_at"),
    )

    idempotency_entry_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    idempotency_scope: Mapped[str] = mapped_column(String(128), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_key: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
