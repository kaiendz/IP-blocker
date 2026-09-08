from typing import List

from pydantic import BaseModel


class TopOffender(BaseModel):
    src_ip: str
    fail_count: int


class DashboardStats(BaseModel):
    active_blacklist_count: int
    blacklist_by_reason: dict
    devices_total: int
    devices_healthy: int
    events_last_24h: int
    top_offenders_last_24h: List[TopOffender]
    published_parts: int
    published_entries: int
    threat_intel_sources_enabled: int
