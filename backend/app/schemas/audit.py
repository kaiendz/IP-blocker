from datetime import datetime

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: str
    actor_label: str
    action: str
    target_type: str
    target_id: str
    detail: dict
    ip_address: str
    created_at: datetime

    class Config:
        from_attributes = True
