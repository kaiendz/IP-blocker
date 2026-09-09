"""Read-only FortiGate REST API client.

Only ever issues GET requests against the FortiGate "monitor" log API to pull
VPN / admin login events. This client intentionally has no method that writes
configuration to the device — the app has no firewall-write capability by design.

IMPORTANT — validate against your firmware: FortiOS's monitor log API field
names have shifted across 6.4 / 7.0 / 7.2 / 7.4. This client targets the
FortiOS 7.2.x/7.4.x "event" log endpoint `/api/v2/monitor/log/disk/event`,
where the log subtype (`vpn`, `system`, `user`, ...) is a query parameter —
not a URL path segment — and normalizes several historically-seen field name
variants. Use the "Test Connection" action after adding a device and, if
event counts look wrong, inspect `raw` on a few `AuthEvent` rows and adjust
`normalize_event` / the filters below for your exact version.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# Subtype mapping per the FortiOS 7.2.x/7.4.x Log Reference: SSL VPN and
# IPsec/IKE events are both logged under the 'vpn' event subtype; admin
# GUI/SSH login attempts are logged under 'system' (not 'user' — that
# subtype covers end-user firewall authentication, e.g. FSSO/RADIUS).
VPN_TYPE_TO_SUBTYPE = {"sslvpn": "vpn", "ike": "vpn", "admin": "system"}


@dataclass
class NormalizedEvent:
    event_time: datetime
    src_ip: str
    username: str
    vpn_type: str  # sslvpn | ike | admin
    action: str  # failed | success | locked
    reason_text: str
    raw: dict[str, Any]


class FortiGateAPIError(RuntimeError):
    pass


class FortiGateClient:
    def __init__(self, host: str, port: int, api_token: str, verify_tls: bool = True, vdom: str = "root"):
        self.base_url = f"https://{host}:{port}"
        self.api_token = api_token
        self.verify_tls = verify_tls
        self.vdom = vdom
        # Local log storage ("disk" vs "memory") is a per-device setting (Log &
        # Report > Log Settings) — many FortiGate VMs/appliances only have one
        # available. Cache whichever location responds successfully so we don't
        # re-probe both on every poll.
        self._log_location: Optional[str] = None

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url,
            verify=self.verify_tls,
            timeout=20.0,
            headers={"Authorization": f"Bearer {self.api_token}"},
        )

    def test_connection(self) -> tuple[bool, str]:
        try:
            with self._client() as client:
                resp = client.get("/api/v2/monitor/system/status", params={"vdom": self.vdom})
            if resp.status_code == 200:
                data = resp.json()
                version = data.get("version") or data.get("results", {}).get("version", "unknown")
                return True, f"Connected — FortiOS {version}"
            if resp.status_code == 401:
                return False, "Authentication failed — check the API token"
            return False, f"Unexpected response: HTTP {resp.status_code}"
        except httpx.ConnectError as exc:
            return False, f"Connection failed: {exc}"
        except httpx.TimeoutException:
            return False, "Connection timed out"
        except Exception as exc:  # noqa: BLE001 — surface any client error to the caller
            return False, f"Error: {exc}"

    def fetch_events(
        self, log_subtype: str, since: Optional[datetime], rows: int = 500, log_location: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """Fetch raw log entries for an event-log subtype (e.g. 'vpn', 'user', 'system').

        On FortiOS 7.2.x/7.4.x, `subtype` is a query parameter on the
        `/api/v2/monitor/log/{location}/event` endpoint, not a path segment.
        If `log_location` isn't given explicitly, tries 'disk' then falls back
        to 'memory' on a 404 (some devices only support one or the other),
        caching whichever works for subsequent calls on this client instance.
        """
        params: dict[str, Any] = {"vdom": self.vdom, "rows": rows, "subtype": log_subtype}
        if since is not None:
            # FortiOS accepts a unix-epoch "since" filter on most monitor/log endpoints.
            params["since"] = int(since.astimezone(timezone.utc).timestamp())

        locations = [log_location] if log_location else ([self._log_location] if self._log_location else ["disk", "memory"])
        last_exc: Optional[httpx.HTTPStatusError] = None
        for location in locations:
            try:
                with self._client() as client:
                    resp = client.get(f"/api/v2/monitor/log/{location}/event", params=params)
                resp.raise_for_status()
                payload = resp.json()
                self._log_location = location
                return payload.get("results", []) or []
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code == 404:
                    continue  # this location isn't available on this device — try the next one
                raise FortiGateAPIError(
                    f"FortiGate returned HTTP {exc.response.status_code} for log subtype '{log_subtype}'"
                ) from exc
            except httpx.HTTPError as exc:
                raise FortiGateAPIError(f"Failed to reach FortiGate: {exc}") from exc

        tried = "/".join(locations)
        raise FortiGateAPIError(
            f"FortiGate returned HTTP 404 for log subtype '{log_subtype}' at every log location tried "
            f"({tried}) — check Log & Report > Log Settings on the device for which storage type it uses"
        ) from last_exc

    def fetch_auth_failures(self, vpn_type: str, since: Optional[datetime], rows: int = 500) -> list[NormalizedEvent]:
        """vpn_type is one of 'sslvpn', 'ike', 'admin'."""
        subtype = VPN_TYPE_TO_SUBTYPE.get(vpn_type)
        if subtype is None:
            raise ValueError(f"Unknown vpn_type: {vpn_type}")
        raw_events = self.fetch_events(subtype, since, rows)
        normalized = []
        for raw in raw_events:
            event = normalize_event(raw, vpn_type)
            if event is not None:
                normalized.append(event)
        return normalized


_FAIL_ACTIONS = {
    "ssl-login-fail",
    "login-fail",
    "tunnel-down",
    "negotiate-error",
    "phase1-error",
    "phase2-error",
}
_FAIL_STATUSES = {"failed", "failure", "deny", "denied"}
_FAIL_KEYWORDS = ("fail", "denied", "invalid", "error", "reject")


def _first(raw: dict[str, Any], *keys: str, default: str = "") -> str:
    for k in keys:
        if raw.get(k) not in (None, ""):
            return str(raw[k])
    return default


def normalize_event(raw: dict[str, Any], vpn_type: str) -> Optional[NormalizedEvent]:
    """Best-effort normalization across FortiOS field-naming variants.

    FortiOS log fields commonly seen: srcip/src/remip, user/admin, action,
    reason/msg/logdesc, itime/eventtime/time+date. For 'vpn' subtype events
    the result is usually encoded directly in `action` (e.g. 'ssl-login-fail');
    for 'system' subtype events (admin logins) `action` is generic ('login')
    and the result is instead in a separate `status` field ('success'/'failed'),
    so both must be checked independently rather than picking whichever is set.
    """
    src_ip = _first(raw, "srcip", "src", "remip", "raddr")
    if not src_ip:
        return None

    username = _first(raw, "user", "admin", "xauthuser")
    action_raw = _first(raw, "action").lower()
    status_raw = _first(raw, "status").lower()
    logdesc = _first(raw, "logdesc", "msg", "reason").lower()

    is_failure = (
        action_raw in _FAIL_ACTIONS
        or status_raw in _FAIL_STATUSES
        or any(k in action_raw for k in _FAIL_KEYWORDS)
        or any(k in status_raw for k in _FAIL_KEYWORDS)
        or any(k in logdesc for k in _FAIL_KEYWORDS)
    )
    is_locked = "locked" in logdesc or "lockout" in logdesc
    action = "locked" if is_locked else ("failed" if is_failure else "success")

    event_time = _parse_event_time(raw)

    return NormalizedEvent(
        event_time=event_time,
        src_ip=src_ip,
        username=username,
        vpn_type=vpn_type,
        action=action,
        reason_text=_first(raw, "logdesc", "msg", "reason"),
        raw=raw,
    )


def _parse_event_time(raw: dict[str, Any]) -> datetime:
    for key in ("eventtime", "itime"):
        val = raw.get(key)
        if val:
            try:
                # eventtime is often nanoseconds-since-epoch; itime seconds-since-epoch.
                num = float(val)
                if num > 1e15:
                    num /= 1e9
                return datetime.fromtimestamp(num, tz=timezone.utc)
            except (TypeError, ValueError):
                pass
    date_str, time_str = raw.get("date"), raw.get("time")
    if date_str and time_str:
        try:
            return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            pass
    return datetime.now(timezone.utc)
