from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class AzurePublishConfig(TimestampMixin, Base):
    """Single-row settings for publishing the blacklist to Azure Blob Storage."""

    __tablename__ = "azure_publish_config"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    connection_string_encrypted: Mapped[str] = mapped_column(String(4096), default="")
    container_name: Mapped[str] = mapped_column(String(255), default="fortigate-blacklist")
    blob_prefix: Mapped[str] = mapped_column(String(255), default="blacklist/part-")
    chunk_size: Mapped[int] = mapped_column(Integer, default=2000, nullable=False)
    sas_expiry_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    publish_interval_minutes: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    generate_sas: Mapped[bool] = mapped_column(default=True)
    enabled: Mapped[bool] = mapped_column(default=False)


class PublishedFeedPart(TimestampMixin, Base):
    """Status of each chunk blob currently published — what to point FortiGate's
    External Resource objects at."""

    __tablename__ = "published_feed_parts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    part_index: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    blob_name: Mapped[str] = mapped_column(String(500), nullable=False)
    entry_count: Mapped[int] = mapped_column(Integer, default=0)
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    blob_url: Mapped[str] = mapped_column(String(2000), default="")
    sas_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
