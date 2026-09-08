from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class AllowlistEntry(TimestampMixin, Base):
    """IPs/CIDRs that must never be blacklisted or published, regardless of source."""

    __tablename__ = "allowlist_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    ip_or_cidr: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    note: Mapped[str] = mapped_column(String(500), default="")
    created_by: Mapped[str] = mapped_column(String(255), default="system")
