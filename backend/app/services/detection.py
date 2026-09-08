"""Brute-force correlation engine: 'N failures within M minutes' -> blacklist entry.

`find_offenders` is a pure function (no DB, no I/O) so the threshold/window
logic can be unit tested directly — see backend/tests/test_detection.py.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy.orm import Session

from app.models.allowlist import AllowlistEntry
from app.models.auth_event import AuthEvent
from app.models.blacklist import BlacklistEntry, BlacklistReason, BlacklistStatus
from app.models.rules import DetectionRule
from app.services.ip_safety import is_always_safe, is_allowlisted


def find_offenders(
    events: Iterable[tuple[str, datetime]],
    threshold_count: int,
    window_minutes: int,
    now: datetime,
) -> dict[str, int]:
    """events: iterable of (src_ip, event_time). Returns {ip: count} for IPs whose
    failure count within the trailing window meets/exceeds the threshold."""
    cutoff = now - timedelta(minutes=window_minutes)
    counts: Counter[str] = Counter(ip for ip, t in events if t >= cutoff)
    return {ip: c for ip, c in counts.items() if c >= threshold_count}


def _upsert_blacklist_entry(
    db: Session, ip: str, rule: DetectionRule, hit_count: int, device_id: str | None
) -> None:
    existing = (
        db.query(BlacklistEntry)
        .filter(
            BlacklistEntry.ip_or_cidr == ip,
            BlacklistEntry.reason_type == BlacklistReason.brute_force,
            BlacklistEntry.status == BlacklistStatus.active,
        )
        .one_or_none()
    )
    now = datetime.now(timezone.utc)
    new_expiry = now + timedelta(hours=rule.ttl_hours)
    if existing:
        existing.expires_at = new_expiry  # repeat offender: extend the TTL
        existing.hit_count = hit_count
        existing.reason_detail = f"{hit_count} failed logins in {rule.window_minutes}m (rule: {rule.name})"
    else:
        db.add(
            BlacklistEntry(
                ip_or_cidr=ip,
                reason_type=BlacklistReason.brute_force,
                reason_detail=f"{hit_count} failed logins in {rule.window_minutes}m (rule: {rule.name})",
                source_name=rule.name,
                device_id=device_id,
                created_by="system:detection",
                expires_at=new_expiry,
                status=BlacklistStatus.active,
                hit_count=hit_count,
            )
        )


def run_detection(db: Session) -> int:
    """Evaluates every enabled DetectionRule and returns the number of IPs
    newly blacklisted or extended."""
    now = datetime.now(timezone.utc)
    allowlist = [a.ip_or_cidr for a in db.query(AllowlistEntry).all()]
    total_actioned = 0

    rules = db.query(DetectionRule).filter(DetectionRule.enabled.is_(True)).all()
    for rule in rules:
        window_start = now - timedelta(minutes=rule.window_minutes)
        query = db.query(AuthEvent.src_ip, AuthEvent.event_time, AuthEvent.device_id).filter(
            AuthEvent.action.in_(["failed", "locked"]),
            AuthEvent.vpn_type.in_(rule.event_types),
            AuthEvent.event_time >= window_start,
        )
        if rule.scope == "device" and rule.device_id:
            query = query.filter(AuthEvent.device_id == rule.device_id)

        rows = query.all()
        events = [(src_ip, event_time) for src_ip, event_time, _device_id in rows]
        device_by_ip: dict[str, str] = {}
        for src_ip, _event_time, device_id in rows:
            device_by_ip.setdefault(src_ip, device_id)

        offenders = find_offenders(events, rule.threshold_count, rule.window_minutes, now)
        for ip, count in offenders.items():
            if is_always_safe(ip) or is_allowlisted(ip, allowlist):
                continue
            _upsert_blacklist_entry(db, ip, rule, count, device_by_ip.get(ip))
            total_actioned += 1

    db.commit()
    return total_actioned
