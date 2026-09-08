from typing import List, Optional

from pydantic import BaseModel


class DetectionRuleCreate(BaseModel):
    name: str
    scope: str = "global"
    device_id: Optional[str] = None
    event_types: List[str] = ["sslvpn", "ike", "admin"]
    threshold_count: int = 5
    window_minutes: int = 10
    ttl_hours: int = 24
    enabled: bool = True


class DetectionRuleUpdate(BaseModel):
    name: Optional[str] = None
    event_types: Optional[List[str]] = None
    threshold_count: Optional[int] = None
    window_minutes: Optional[int] = None
    ttl_hours: Optional[int] = None
    enabled: Optional[bool] = None


class DetectionRuleOut(BaseModel):
    id: str
    name: str
    scope: str
    device_id: Optional[str] = None
    event_types: List[str]
    threshold_count: int
    window_minutes: int
    ttl_hours: int
    enabled: bool

    class Config:
        from_attributes = True
