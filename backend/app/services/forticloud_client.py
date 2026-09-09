"""Read-only FortiCloud logging API client, for FortiGates that forward their
logs off-box to FortiCloud instead of retaining them locally.

IMPORTANT — validate against your subscription: FortiCloud's log-query API
surface differs depending on whether you're on FortiGate Cloud, FortiAnalyzer
Cloud, or the newer FortiCloud/Lacework-unified IAM — the OAuth token endpoint
below (`customerapiauth.fortinet.com`) is stable across products, but the log
query endpoint/path and its response shape are product-specific. Confirm the
correct `log_query_base_url` and adjust `fetch_events`'s request shape for
your subscription using the "Test Connection" action before relying on this.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class ForticloudAPIError(RuntimeError):
    pass


@dataclass
class _CachedToken:
    access_token: str
    expires_at: float


class ForticloudClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        api_gateway: str = "https://customerapiauth.fortinet.com",
        log_query_base_url: str = "https://fortigate.forticloud.com",
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_gateway = api_gateway.rstrip("/")
        self.log_query_base_url = log_query_base_url.rstrip("/")
        self._token: Optional[_CachedToken] = None

    def _get_token(self) -> str:
        if self._token and self._token.expires_at > time.time() + 30:
            return self._token.access_token
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(
                    f"{self.api_gateway}/api/v1/oauth/token/",
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "grant_type": "client_credentials",
                    },
                )
            resp.raise_for_status()
            data = resp.json()
            token = data["access_token"]
            ttl = int(data.get("expires_in", 3600))
            self._token = _CachedToken(access_token=token, expires_at=time.time() + ttl)
            return token
        except httpx.HTTPError as exc:
            raise ForticloudAPIError(f"FortiCloud auth failed: {exc}") from exc
        except (KeyError, ValueError) as exc:
            raise ForticloudAPIError(f"Unexpected FortiCloud auth response: {exc}") from exc

    def test_connection(self) -> tuple[bool, str]:
        try:
            self._get_token()
            return True, "FortiCloud OAuth token acquired successfully"
        except ForticloudAPIError as exc:
            return False, str(exc)

    def fetch_events(
        self,
        serial: str,
        log_subtype: str,
        since: Optional[datetime],
        rows: int = 500,
        page_size: int = 1000,
        max_pages: int = 50,
    ) -> list[dict[str, Any]]:
        """Fetch log entries for a device/subtype, paginating via rows/start.

        Mirrors the pagination convention FortiGateClient uses against the
        device's own Log Access API (`start`/`rows`, stopping on a short page)
        since Fortinet's log-search APIs commonly cap responses to a small
        page unless paginated explicitly. Param names are unverified for your
        specific subscription (see module docstring) — confirm via "Test
        Connection" and adjust if pagination doesn't behave as expected.
        """
        token = self._get_token()
        results: list[dict[str, Any]] = []
        page_size = min(page_size, rows) if rows else page_size
        try:
            with httpx.Client(
                base_url=self.log_query_base_url,
                timeout=30.0,
                headers={"Authorization": f"Bearer {token}"},
            ) as client:
                for page in range(max_pages):
                    params: dict[str, Any] = {
                        "serial": serial,
                        "subtype": log_subtype,
                        "rows": page_size,
                        "start": page * page_size,
                    }
                    if since is not None:
                        params["since"] = int(since.astimezone(timezone.utc).timestamp())
                    resp = client.get("/api/v1/logs/search", params=params)
                    resp.raise_for_status()
                    payload = resp.json()
                    page_results = payload.get("results", payload.get("data", [])) or []
                    results.extend(page_results)
                    if len(page_results) < page_size or (rows and len(results) >= rows):
                        break
                else:
                    logger.warning(
                        "Hit the %d-page safety cap (%d entries) fetching '%s' logs for device %s — "
                        "results may be incomplete.",
                        max_pages, len(results), log_subtype, serial,
                    )
        except httpx.HTTPError as exc:
            raise ForticloudAPIError(f"FortiCloud log query failed: {exc}") from exc
        return results[:rows] if rows else results
