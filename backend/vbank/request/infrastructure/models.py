from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from vbank.shared.database import Base


class Request(Base):
    __tablename__ = "request"
    __table_args__ = (
        CheckConstraint(
            "request_type in ('UserRegistration','AccountOpening','Deposit','Withdraw','Transfer')",
            name="ck_request_request_type",
        ),
        CheckConstraint(
            "status in ('PendingApproval','Approved','Rejected')",
            name="ck_request_status",
        ),
        CheckConstraint(
            "result_entity_type is null or result_entity_type in ('User','Account','Transaction')",
            name="ck_request_result_entity_type",
        ),
        CheckConstraint(
            "(result_entity_type is null) = (result_entity_id is null)",
            name="ck_request_result_entity_pair",
        ),
        CheckConstraint(
            "(status = 'PendingApproval') = (decided_at is null)",
            name="ck_request_pending_decided_at",
        ),
        CheckConstraint(
            "status <> 'PendingApproval' "
            "or (operator_user_id is null and reason_code is null and result_entity_type is null)",
            name="ck_request_pending_has_no_decision",
        ),
        CheckConstraint(
            "status = 'PendingApproval' "
            "or (operator_user_id is not null and reason_code is not null)",
            name="ck_request_decided_has_operator_reason",
        ),
        CheckConstraint(
            "status <> 'Approved' or result_entity_type is not null",
            name="ck_request_approved_has_result",
        ),
        CheckConstraint(
            "status <> 'Rejected' or result_entity_type is null",
            name="ck_request_rejected_has_no_result",
        ),
        Index("ix_request_initiator_user_id", "initiator_user_id"),
        Index("ix_request_operator_user_id", "operator_user_id"),
        Index("ix_request_status_created_at", "status", "created_at"),
        Index("ix_request_request_type", "request_type"),
        Index("ix_request_result_entity", "result_entity_type", "result_entity_id"),
    )

    request_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    request_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    initiator_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_account.user_id", name="fk_request_initiator_user_id_user_account"),
        nullable=False,
    )
    operator_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_account.user_id", name="fk_request_operator_user_id_user_account"),
    )
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    reason_code: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("reason_code.reason_code", name="fk_request_reason_code_reason_code"),
    )
    result_entity_type: Mapped[str | None] = mapped_column(String(32))
    result_entity_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
