from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models.blacklist import BlacklistReason, BlacklistStatus


class BlacklistManualCreate(BaseModel):
    ip_or_cidr: str
    reason_detail: str = "manually added"
    ttl_hours: Optional[int] = None  # None = permanent until manually removed


class BlacklistBulkRemove(BaseModel):
    ids: List[str]


class BlacklistBulkResult(BaseModel):
    removed_count: int


class BlacklistOut(BaseModel):
    id: str
    ip_or_cidr: str
    reason_type: BlacklistReason
    reason_detail: str
    source_name: str
    device_id: Optional[str] = None
    created_by: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    status: BlacklistStatus
    hit_count: int

    class Config:
        from_attributes = True
