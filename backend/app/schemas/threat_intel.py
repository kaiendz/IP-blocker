from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.threat_intel import ThreatIntelFormat


class ThreatIntelSourceCreate(BaseModel):
    name: str
    url: str
    format: ThreatIntelFormat = ThreatIntelFormat.plain_ip_list
    api_key: str = ""
    enabled: bool = True
    refresh_interval_minutes: int = 60


class ThreatIntelSourceUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    format: Optional[ThreatIntelFormat] = None
    api_key: Optional[str] = None
    enabled: Optional[bool] = None
    refresh_interval_minutes: Optional[int] = None


class ThreatIntelSourceOut(BaseModel):
    id: str
    name: str
    url: str
    format: ThreatIntelFormat
    enabled: bool
    refresh_interval_minutes: int
    last_fetch_at: Optional[datetime] = None
    last_fetch_status: str
    indicator_count: int

    class Config:
        from_attributes = True
