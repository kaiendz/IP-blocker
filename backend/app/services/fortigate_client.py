"""Read-only FortiGate REST API client.

Only ever issues GET requests against the FortiGate Log Access API to pull
VPN / admin login events. This client intentionally has no method that writes
configuration to the device — the app has no firewall-write capability by design.

Endpoint: `/api/v2/log/{store}/event/{subtype}` where `store` is 'memory',
'disk', or 'forticloud' and `subtype` (e.g. 'vpn', 'system') is a URL path
segment — this is the Log Access API, distinct from (and easily confused
with) the Monitor API's `/api/v2/monitor/...` endpoints, which don't expose
arbitrary historical log queries the same way. This endpoint also returns
only a small page (~20 entries) per request unless paginated explicitly via
`rows`/`start`, so `fetch_events` pages through until a short page signals
the end or `max_pages` is hit as a safety cap.

IMPORTANT — validate against your firmware: field names have shifted across
6.4 / 7.0 / 7.2 / 7.4. Use the "Test Connection" action after adding a device
and, if event counts look wrong, inspect `raw` on a few `AuthEvent` rows and
adjust `normalize_event` / the filters below for your exact version.
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
        # Local log storage ("memory" vs "disk") is a per-device setting (Log &
        # Report > Log Settings) — many FortiGate VMs/appliances only have one
        # available. "memory" exists on every device; "disk" only on models with
        # local storage. Cache whichever responds so we don't re-probe every poll.
        self._log_store: Optional[str] = None

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
        self,
        log_subtype: str,
        since: Optional[datetime],
        rows: int = 500,
        log_store: Optional[str] = None,
        page_size: int = 1000,
        max_pages: int = 50,
    ) -> list[dict[str, Any]]:
        """Fetch raw log entries for a Log Access API event subtype (e.g. 'vpn', 'system').

        `subtype` is a URL path segment: `/api/v2/log/{store}/event/{subtype}`.
        If `log_store` isn't given explicitly, tries 'memory' then falls back
        to 'disk' on a 404 (some devices only support one or the other),
        caching whichever works for subsequent calls on this client instance.
        Pages through `rows`/`start` until a short page signals the end or
        `max_pages` is hit as a safety cap, since this endpoint silently caps
        each response to a small page unless paginated explicitly.

        `since` isn't sent as a server-side filter — a 'timestamp=>' filter
        clause caused a confirmed HTTP 500 on real hardware, and 'timestamp'
        isn't a documented filterable field for this endpoint. Time-bounding
        instead happens client-side in `fetch_auth_failures` after entries are
        parsed, so `rows`/`max_pages` need to comfortably cover the expected
        volume of new entries between polls.
        """
        stores = [log_store] if log_store else ([self._log_store] if self._log_store else ["memory", "disk"])
        last_exc: Optional[httpx.HTTPStatusError] = None
        for store in stores:
            try:
                results = self._fetch_all_pages(store, log_subtype, rows, page_size, max_pages)
                self._log_store = store
                return results
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code == 404:
                    continue  # this store isn't available on this device — try the next one
                raise FortiGateAPIError(
                    f"FortiGate returned HTTP {exc.response.status_code} for log subtype '{log_subtype}'"
                ) from exc
            except httpx.HTTPError as exc:
                raise FortiGateAPIError(f"Failed to reach FortiGate: {exc}") from exc

        tried = "/".join(stores)
        raise FortiGateAPIError(
            f"FortiGate returned HTTP 404 for log subtype '{log_subtype}' at every log store tried "
            f"({tried}) — check Log & Report > Log Settings on the device for which storage type it uses"
        ) from last_exc

    def _fetch_all_pages(
        self, store: str, log_subtype: str, rows: int, page_size: int, max_pages: int
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        page_size = min(page_size, rows) if rows else page_size
        with self._client() as client:
            for page in range(max_pages):
                params: dict[str, Any] = {"vdom": self.vdom, "rows": page_size, "start": page * page_size}
                resp = client.get(f"/api/v2/log/{store}/event/{log_subtype}", params=params)
                resp.raise_for_status()
                page_results = resp.json().get("results", []) or []
                results.extend(page_results)
                if len(page_results) < page_size or (rows and len(results) >= rows):
                    break
            else:
                logger.warning(
                    "Hit the %d-page safety cap (%d entries) fetching '%s' logs from '%s' — "
                    "results may be incomplete.",
                    max_pages, len(results), log_subtype, store,
                )
        return results[:rows] if rows else results

    def fetch_auth_failures(self, vpn_type: str, since: Optional[datetime], rows: int = 500) -> list[NormalizedEvent]:
        """vpn_type is one of 'sslvpn', 'ike', 'admin'.

        'sslvpn' and 'ike' both come from the same 'vpn' log subtype — FortiOS
        doesn't split them into separate subtypes/endpoints — so each raw entry
        is classified individually (see `_guess_vpn_kind`) and only kept if it
        actually matches the requested `vpn_type`. Without this, both calls
        would fetch the exact same entries and every one would get stored
        twice, tagged with whichever type happened to be requested.
        """
        subtype = VPN_TYPE_TO_SUBTYPE.get(vpn_type)
        if subtype is None:
            raise ValueError(f"Unknown vpn_type: {vpn_type}")
        raw_events = self.fetch_events(subtype, since, rows)
        normalized = []
        for raw in raw_events:
            event = normalize_event(raw, vpn_type)
            if event is None:
                continue
            if since is not None and event.event_time <= since:
                continue  # already seen on a previous poll — not filtered server-side
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


def _guess_vpn_kind(raw: dict[str, Any]) -> str:
    """Classify a raw 'vpn'-subtype entry as 'sslvpn' or 'ike' — FortiOS logs
    both under the same subtype/endpoint with no separate path to tell them
    apart up front. Prefers an explicit `tunneltype` field when present;
    otherwise SSL VPN action values are conventionally prefixed 'ssl-'
    (ssl-login-fail, ssl-tunnel-up, ...) while IPsec/IKE actions aren't
    (phase1-up, negotiate-error, tunnel-down, ...) — this only decides which
    bucket an entry belongs to and doesn't change how failures are detected
    within either bucket.
    """
    tunnel_type = _first(raw, "tunneltype").lower()
    if tunnel_type in ("ssl", "sslvpn"):
        return "sslvpn"
    if tunnel_type in ("ipsec", "ike"):
        return "ike"
    return "sslvpn" if _first(raw, "action").lower().startswith("ssl") else "ike"


def normalize_event(raw: dict[str, Any], vpn_type: str) -> Optional[NormalizedEvent]:
    """Best-effort normalization across FortiOS field-naming variants.

    FortiOS log fields commonly seen: srcip/src/remip, user/admin, action,
    reason/msg/logdesc, itime/eventtime/time+date. For 'vpn' subtype events
    the result is usually encoded directly in `action` (e.g. 'ssl-login-fail');
    for 'system' subtype events (admin logins) `action` is generic ('login')
    and the result is instead in a separate `status` field ('success'/'failed'),
    so both must be checked independently rather than picking whichever is set.
    """
    if vpn_type in ("sslvpn", "ike") and _guess_vpn_kind(raw) != vpn_type:
        return None  # this 'vpn' subtype entry belongs to the other vpn_type — leave it for that pass

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
