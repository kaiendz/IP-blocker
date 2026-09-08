from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.rbac import require_viewer
from app.db.session import get_db
from app.models.auth_event import AuthEvent
from app.models.azure_publish import PublishedFeedPart
from app.models.blacklist import BlacklistEntry, BlacklistStatus
from app.models.device import FortiGateDevice
from app.models.threat_intel import ThreatIntelSource
from app.schemas.dashboard import DashboardStats, TopOffender

router = APIRouter(prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(require_viewer)])


@router.get("/stats", response_model=DashboardStats)
def get_stats(db: Session = Depends(get_db)):
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)

    active_q = db.query(BlacklistEntry).filter(BlacklistEntry.status == BlacklistStatus.active)
    active_count = active_q.count()
    by_reason = dict(
        db.query(BlacklistEntry.reason_type, func.count(BlacklistEntry.id))
        .filter(BlacklistEntry.status == BlacklistStatus.active)
        .group_by(BlacklistEntry.reason_type)
        .all()
    )
    by_reason = {k.value: v for k, v in by_reason.items()}

    devices = db.query(FortiGateDevice).all()
    healthy = sum(1 for d in devices if d.last_poll_status.startswith("ok"))

    events_24h = db.query(AuthEvent).filter(AuthEvent.event_time >= since_24h).count()

    top_rows = (
        db.query(AuthEvent.src_ip, func.count(AuthEvent.id).label("cnt"))
        .filter(AuthEvent.event_time >= since_24h, AuthEvent.action.in_(["failed", "locked"]))
        .group_by(AuthEvent.src_ip)
        .order_by(func.count(AuthEvent.id).desc())
        .limit(10)
        .all()
    )

    parts = db.query(PublishedFeedPart).all()
    ti_enabled = db.query(ThreatIntelSource).filter(ThreatIntelSource.enabled.is_(True)).count()

    return DashboardStats(
        active_blacklist_count=active_count,
        blacklist_by_reason=by_reason,
        devices_total=len(devices),
        devices_healthy=healthy,
        events_last_24h=events_24h,
        top_offenders_last_24h=[TopOffender(src_ip=ip, fail_count=cnt) for ip, cnt in top_rows],
        published_parts=len(parts),
        published_entries=sum(p.entry_count for p in parts),
        threat_intel_sources_enabled=ti_enabled,
    )
