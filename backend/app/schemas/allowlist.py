from datetime import datetime

from pydantic import BaseModel


class AllowlistCreate(BaseModel):
    ip_or_cidr: str
    note: str = ""


class AllowlistOut(BaseModel):
    id: str
    ip_or_cidr: str
    note: str
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True
