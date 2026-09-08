import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid


class LogSource(str, enum.Enum):
    device_api = "device_api"  # poll the FortiGate's own REST API directly
    forticloud = "forticloud"  # logs are forwarded off-box; pull from FortiCloud instead


class FortiGateDevice(TimestampMixin, Base):
    """A FortiGate we read (never write) auth/VPN logs from."""

    __tablename__ = "fortigate_devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, default=443, nullable=False)
    vdom: Mapped[str] = mapped_column(String(64), default="root", nullable=False)

    # Read-only FortiGate API token, encrypted at rest (app.core.security.encrypt_secret).
    api_token_encrypted: Mapped[str] = mapped_column(String(2048), default="")
    verify_tls: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    site_tag: Mapped[str] = mapped_column(String(120), default="")
    poll_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    log_source: Mapped[LogSource] = mapped_column(Enum(LogSource), default=LogSource.device_api, nullable=False)

    # Only used when log_source == forticloud
    forticloud_credential_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("forticloud_credentials.id"), nullable=True
    )
    forticloud_serial: Mapped[str] = mapped_column(String(64), default="")

    last_polled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_poll_status: Mapped[str] = mapped_column(String(500), default="never polled")

    forticloud_credential: Mapped[Optional["ForticloudCredential"]] = relationship(
        back_populates="devices"
    )


class ForticloudCredential(TimestampMixin, Base):
    """OAuth2 client-credentials for the FortiCloud logging API, encrypted at rest."""

    __tablename__ = "forticloud_credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_id_encrypted: Mapped[str] = mapped_column(String(2048), default="")
    client_secret_encrypted: Mapped[str] = mapped_column(String(2048), default="")
    api_gateway: Mapped[str] = mapped_column(
        String(255), default="https://customerapiauth.fortinet.com"
    )

    devices: Mapped[list["FortiGateDevice"]] = relationship(back_populates="forticloud_credential")


class PollCursor(Base):
    """Tracks how far each device/log-type has been polled, to avoid re-ingesting events."""

    __tablename__ = "poll_cursors"
    __table_args__ = (UniqueConstraint("device_id", "log_type", name="uq_poll_cursor_device_logtype"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("fortigate_devices.id"), nullable=False)
    log_type: Mapped[str] = mapped_column(String(32), nullable=False)  # sslvpn | ike | admin
    last_event_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_event_key: Mapped[str] = mapped_column(String(255), default="")
