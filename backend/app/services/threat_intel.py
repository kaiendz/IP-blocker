"""Fetches and parses configured threat-intel feeds, upserting matches into
`blacklist_entries` with reason_type=threat_intel."""
from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.security import decrypt_secret
from app.models.allowlist import AllowlistEntry
from app.models.blacklist import BlacklistEntry, BlacklistReason, BlacklistStatus
from app.models.threat_intel import ThreatIntelFormat, ThreatIntelSource
from app.services.ip_safety import is_allowlisted, is_always_safe, is_valid_ip_or_cidr

logger = logging.getLogger(__name__)

# Reputable, free, no-API-key-required plaintext IP blocklists, seeded on first run.
DEFAULT_SOURCES = [
    {
        "name": "Spamhaus DROP",
        "url": "https://www.spamhaus.org/drop/drop.txt",
        "format": ThreatIntelFormat.plain_ip_list,
        "refresh_interval_minutes": 720,
    },
    {
        "name": "Spamhaus EDROP",
        "url": "https://www.spamhaus.org/drop/edrop.txt",
        "format": ThreatIntelFormat.plain_ip_list,
        "refresh_interval_minutes": 720,
    },
    {
        "name": "Blocklist.de (all)",
        "url": "https://lists.blocklist.de/lists/all.txt",
        "format": ThreatIntelFormat.plain_ip_list,
        "refresh_interval_minutes": 180,
    },
    {
        "name": "abuse.ch Feodo Tracker (C2 IPs)",
        "url": "https://feodotracker.abuse.ch/downloads/ipblocklist.txt",
        "format": ThreatIntelFormat.plain_ip_list,
        "refresh_interval_minutes": 180,
    },
]


def _parse_plain_ip_list(text: str) -> list[str]:
    ips = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        token = line.split()[0].split(",")[0].split(";")[0]
        if is_valid_ip_or_cidr(token):
            ips.append(token)
    return ips


def _parse_csv(text: str) -> list[str]:
    ips = []
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        if not row:
            continue
        candidate = row[0].strip()
        if candidate and is_valid_ip_or_cidr(candidate):
            ips.append(candidate)
    return ips


def _parse_json(text: str) -> list[str]:
    data = json.loads(text)
    ips = []
    items = data if isinstance(data, list) else data.get("data", data.get("results", []))
    for item in items:
        candidate = item if isinstance(item, str) else (item.get("ip") or item.get("indicator") or "")
        if candidate and is_valid_ip_or_cidr(candidate):
            ips.append(candidate)
    return ips


def parse_feed(text: str, fmt: ThreatIntelFormat) -> list[str]:
    if fmt == ThreatIntelFormat.plain_ip_list:
        return _parse_plain_ip_list(text)
    if fmt == ThreatIntelFormat.csv:
        return _parse_csv(text)
    if fmt == ThreatIntelFormat.json:
        return _parse_json(text)
    raise ValueError(f"Unsupported feed format: {fmt}")


def fetch_source(db: Session, source: ThreatIntelSource) -> tuple[bool, str, int]:
    headers = {}
    if source.api_key_encrypted:
        headers["Authorization"] = f"Bearer {decrypt_secret(source.api_key_encrypted)}"
    try:
        with httpx.Client(timeout=30.0, headers=headers, follow_redirects=True) as client:
            resp = client.get(source.url)
        resp.raise_for_status()
        ips = parse_feed(resp.text, source.format)
    except httpx.HTTPError as exc:
        return False, f"Fetch failed: {exc}", 0
    except (ValueError, json.JSONDecodeError) as exc:
        return False, f"Parse failed: {exc}", 0

    allowlist = [a.ip_or_cidr for a in db.query(AllowlistEntry).all()]
    upserted = 0
    for ip in ips:
        if is_always_safe(ip) or is_allowlisted(ip, allowlist):
            continue
        existing = (
            db.query(BlacklistEntry)
            .filter(
                BlacklistEntry.ip_or_cidr == ip,
                BlacklistEntry.reason_type == BlacklistReason.threat_intel,
                BlacklistEntry.source_name == source.name,
                BlacklistEntry.status == BlacklistStatus.active,
            )
            .one_or_none()
        )
        if existing:
            existing.hit_count += 1
        else:
            db.add(
                BlacklistEntry(
                    ip_or_cidr=ip,
                    reason_type=BlacklistReason.threat_intel,
                    reason_detail=f"Listed on {source.name}",
                    source_name=source.name,
                    created_by=f"system:threat_intel:{source.name}",
                    expires_at=None,  # persists while still present on the feed's next refresh cycle
                    status=BlacklistStatus.active,
                )
            )
        upserted += 1

    source.last_fetch_at = datetime.now(timezone.utc)
    source.last_fetch_status = f"ok — {upserted} indicator(s)"
    source.indicator_count = upserted
    db.commit()
    return True, source.last_fetch_status, upserted


def refresh_due_sources(db: Session) -> None:
    now = datetime.now(timezone.utc)
    sources = db.query(ThreatIntelSource).filter(ThreatIntelSource.enabled.is_(True)).all()
    for source in sources:
        if source.last_fetch_at is not None:
            elapsed_minutes = (now - source.last_fetch_at).total_seconds() / 60
            if elapsed_minutes < source.refresh_interval_minutes:
                continue
        try:
            fetch_source(db, source)
        except Exception:  # noqa: BLE001 — one bad feed must not block the others
            db.rollback()
            logger.exception("Threat intel fetch failed for source %s", source.name)
