"""Polls each enabled FortiGate device (directly, or via FortiCloud) for auth
events and stores normalized rows in `auth_events`, tracking a per-device,
per-log-type cursor so nothing is re-ingested."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.security import decrypt_secret
from app.models.auth_event import AuthEvent
from app.models.device import ForticloudCredential, FortiGateDevice, LogSource, PollCursor
from app.services.fortigate_client import VPN_TYPE_TO_SUBTYPE, FortiGateClient, normalize_event
from app.services.forticloud_client import ForticloudClient

logger = logging.getLogger(__name__)

_VPN_TYPES = ["sslvpn", "ike", "admin"]
_LOOKBACK_ON_FIRST_POLL = timedelta(hours=6)


def _get_cursor(db: Session, device_id: str, log_type: str) -> PollCursor:
    cursor = (
        db.query(PollCursor)
        .filter(PollCursor.device_id == device_id, PollCursor.log_type == log_type)
        .one_or_none()
    )
    if cursor is None:
        cursor = PollCursor(device_id=device_id, log_type=log_type, last_event_time=None)
        db.add(cursor)
        db.flush()
    return cursor


def poll_device(db: Session, device: FortiGateDevice) -> tuple[bool, str, int]:
    """Returns (ok, status_message, events_ingested)."""
    total_ingested = 0
    try:
        if device.log_source == LogSource.device_api:
            token = decrypt_secret(device.api_token_encrypted)
            client = FortiGateClient(device.host, device.port, token, device.verify_tls, device.vdom)
            for vpn_type in _VPN_TYPES:
                cursor = _get_cursor(db, device.id, vpn_type)
                since = cursor.last_event_time or (datetime.now(timezone.utc) - _LOOKBACK_ON_FIRST_POLL)
                events = client.fetch_auth_failures(vpn_type, since)
                total_ingested += _store_events(db, device.id, events)
                if events:
                    cursor.last_event_time = max(e.event_time for e in events)

        elif device.log_source == LogSource.forticloud:
            if not device.forticloud_credential_id:
                return False, "No FortiCloud credential linked to this device", 0
            cred: ForticloudCredential | None = db.get(ForticloudCredential, device.forticloud_credential_id)
            if cred is None:
                return False, "Linked FortiCloud credential not found", 0
            client = ForticloudClient(
                decrypt_secret(cred.client_id_encrypted),
                decrypt_secret(cred.client_secret_encrypted),
                cred.api_gateway,
            )
            for vpn_type in _VPN_TYPES:
                subtype = VPN_TYPE_TO_SUBTYPE[vpn_type]
                cursor = _get_cursor(db, device.id, vpn_type)
                since = cursor.last_event_time or (datetime.now(timezone.utc) - _LOOKBACK_ON_FIRST_POLL)
                raw_events = client.fetch_events(device.forticloud_serial, subtype, since)
                events = [e for e in (normalize_event(r, vpn_type) for r in raw_events) if e is not None]
                total_ingested += _store_events(db, device.id, events)
                if events:
                    cursor.last_event_time = max(e.event_time for e in events)
        else:
            return False, f"Unknown log source: {device.log_source}", 0

        device.last_polled_at = datetime.now(timezone.utc)
        device.last_poll_status = f"ok — {total_ingested} new event(s)"
        db.commit()
        return True, device.last_poll_status, total_ingested

    except Exception as exc:  # noqa: BLE001 — a single device's failure must not break the sweep
        db.rollback()
        logger.exception("Poll failed for device %s", device.id)
        device.last_polled_at = datetime.now(timezone.utc)
        device.last_poll_status = f"error: {exc}"
        db.commit()
        return False, str(exc), 0


def _store_events(db: Session, device_id: str, events: list) -> int:
    count = 0
    for e in events:
        if e.action not in ("failed", "locked"):
            continue  # only interested in failures for detection; successes aren't stored
        db.add(
            AuthEvent(
                device_id=device_id,
                event_time=e.event_time,
                src_ip=e.src_ip,
                username=e.username,
                vpn_type=e.vpn_type,
                action=e.action,
                reason_text=e.reason_text,
                raw=e.raw,
            )
        )
        count += 1
    return count


def poll_all_devices(db: Session) -> None:
    devices = db.query(FortiGateDevice).filter(FortiGateDevice.poll_enabled.is_(True)).all()
    for device in devices:
        poll_device(db, device)
