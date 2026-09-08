from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.device import LogSource


class DeviceCreate(BaseModel):
    name: str
    host: str
    port: int = 443
    vdom: str = "root"
    api_token: str = ""  # plaintext in-transit only; encrypted before storage
    verify_tls: bool = True
    site_tag: str = ""
    poll_enabled: bool = True
    log_source: LogSource = LogSource.device_api
    forticloud_credential_id: Optional[str] = None
    forticloud_serial: str = ""


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    vdom: Optional[str] = None
    api_token: Optional[str] = None
    verify_tls: Optional[bool] = None
    site_tag: Optional[str] = None
    poll_enabled: Optional[bool] = None
    log_source: Optional[LogSource] = None
    forticloud_credential_id: Optional[str] = None
    forticloud_serial: Optional[str] = None


class DeviceOut(BaseModel):
    id: str
    name: str
    host: str
    port: int
    vdom: str
    verify_tls: bool
    site_tag: str
    poll_enabled: bool
    log_source: LogSource
    forticloud_credential_id: Optional[str] = None
    forticloud_serial: str
    last_polled_at: Optional[datetime] = None
    last_poll_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ForticloudCredentialCreate(BaseModel):
    name: str
    client_id: str
    client_secret: str
    api_gateway: str = "https://customerapiauth.fortinet.com"


class ForticloudCredentialOut(BaseModel):
    id: str
    name: str
    api_gateway: str
    created_at: datetime

    class Config:
        from_attributes = True


class TestConnectionResult(BaseModel):
    ok: bool
    message: str
