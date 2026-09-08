from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class AzurePublishConfigUpdate(BaseModel):
    connection_string: Optional[str] = None  # plaintext in-transit; encrypted before storage
    container_name: Optional[str] = None
    blob_prefix: Optional[str] = None
    chunk_size: Optional[int] = None
    sas_expiry_days: Optional[int] = None
    publish_interval_minutes: Optional[int] = None
    generate_sas: Optional[bool] = None
    enabled: Optional[bool] = None


class AzurePublishConfigOut(BaseModel):
    container_name: str
    blob_prefix: str
    chunk_size: int
    sas_expiry_days: int
    publish_interval_minutes: int
    generate_sas: bool
    enabled: bool
    has_connection_string: bool


class PublishedFeedPartOut(BaseModel):
    part_index: int
    blob_name: str
    entry_count: int
    blob_url: str
    sas_expires_at: Optional[datetime] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class PublishNowResult(BaseModel):
    ok: bool
    message: str
    parts: List[PublishedFeedPartOut] = []
