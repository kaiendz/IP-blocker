import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class ThreatIntelFormat(str, enum.Enum):
    plain_ip_list = "plain_ip_list"  # one IP/CIDR per line, '#' comments allowed
    csv = "csv"  # IP in a configurable column
    json = "json"  # IP at a configurable JSON path


class ThreatIntelSource(TimestampMixin, Base):
    __tablename__ = "threat_intel_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    format: Mapped[ThreatIntelFormat] = mapped_column(
        Enum(ThreatIntelFormat), default=ThreatIntelFormat.plain_ip_list, nullable=False
    )
    api_key_encrypted: Mapped[str] = mapped_column(String(2048), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    refresh_interval_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    last_fetch_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_fetch_status: Mapped[str] = mapped_column(String(500), default="never fetched")
    indicator_count: Mapped[int] = mapped_column(Integer, default=0)
