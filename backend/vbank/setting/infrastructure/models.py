from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from vbank.shared.database import Base


class SystemSetting(Base):
    __tablename__ = "system_setting"
    __table_args__ = (
        UniqueConstraint("key", name="uq_system_setting_key"),
        CheckConstraint(
            "key in ("
            "'bank_name',"
            "'registration_mode',"
            "'account_opening_mode',"
            "'internal_transfer_mode',"
            "'cash_in_out_mode'"
            ")",
            name="ck_system_setting_key",
        ),
        CheckConstraint("value_type in ('string','mode')", name="ck_system_setting_value_type"),
        CheckConstraint(
            "("
            "key <> 'bank_name' "
            "or (value_type = 'string' and value <> '')"
            ")",
            name="ck_system_setting_bank_name",
        ),
        CheckConstraint(
            "("
            "key <> 'registration_mode' "
            "or (value_type = 'mode' and value in ('auto','manual'))"
            ")",
            name="ck_system_setting_registration_mode",
        ),
        CheckConstraint(
            "("
            "key <> 'account_opening_mode' "
            "or (value_type = 'mode' and value in ('auto','manual'))"
            ")",
            name="ck_system_setting_account_opening_mode",
        ),
        CheckConstraint(
            "("
            "key <> 'internal_transfer_mode' "
            "or (value_type = 'mode' and value in ('enabled','manual','disabled'))"
            ")",
            name="ck_system_setting_internal_transfer_mode",
        ),
        CheckConstraint(
            "("
            "key <> 'cash_in_out_mode' "
            "or (value_type = 'mode' and value in ('manual','disabled'))"
            ")",
            name="ck_system_setting_cash_in_out_mode",
        ),
    )

    setting_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    value_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
