from datetime import datetime

from pydantic import BaseModel


class AuthEventOut(BaseModel):
    id: str
    device_id: str
    event_time: datetime
    src_ip: str
    username: str
    vpn_type: str
    action: str
    reason_text: str

    class Config:
        from_attributes = True
