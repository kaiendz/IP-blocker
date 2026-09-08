"""Publishes the active blacklist to Azure Blob Storage as chunked plaintext
files, which each FortiGate's own External Resource (Threat Feed) object polls
over HTTPS. This is the *only* enforcement path — the app never writes to a
firewall directly.

`build_chunks` and `compute_hash` are pure functions so the chunking behavior
(including shrink handling) can be unit tested without a real storage account
— see backend/tests/test_azure_chunking.py.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import decrypt_secret
from app.models.allowlist import AllowlistEntry
from app.models.azure_publish import AzurePublishConfig, PublishedFeedPart
from app.models.blacklist import BlacklistEntry, BlacklistStatus
from app.services.ip_safety import is_allowlisted, is_always_safe

logger = logging.getLogger(__name__)


def build_chunks(ips: list[str], chunk_size: int) -> list[list[str]]:
    """Split a sorted, de-duplicated IP/CIDR list into fixed-size chunks."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be >= 1")
    unique_sorted = sorted(set(ips))
    return [unique_sorted[i : i + chunk_size] for i in range(0, len(unique_sorted), chunk_size)]


def compute_hash(lines: list[str]) -> str:
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def _parse_connection_string(conn_str: str) -> dict[str, str]:
    parts = {}
    for segment in conn_str.split(";"):
        if "=" in segment:
            k, _, v = segment.partition("=")
            parts[k.strip()] = v.strip()
    return parts


def get_active_blacklist_ips(db: Session) -> list[str]:
    allowlist = [a.ip_or_cidr for a in db.query(AllowlistEntry).all()]
    rows = (
        db.query(BlacklistEntry.ip_or_cidr)
        .filter(BlacklistEntry.status == BlacklistStatus.active)
        .distinct()
        .all()
    )
    ips = []
    for (ip,) in rows:
        if is_always_safe(ip) or is_allowlisted(ip, allowlist):
            continue
        ips.append(ip)
    return ips


def publish(db: Session) -> tuple[bool, str, list[PublishedFeedPart]]:
    config = db.query(AzurePublishConfig).first()
    if config is None or not config.enabled:
        return False, "Azure publishing is not configured/enabled", []
    if not config.connection_string_encrypted:
        return False, "No Azure Storage connection string configured", []

    try:
        from azure.core.exceptions import ResourceExistsError
        from azure.storage.blob import BlobServiceClient, ContentSettings, generate_blob_sas, BlobSasPermissions
    except ImportError:
        return False, "azure-storage-blob package is not installed", []

    conn_str = decrypt_secret(config.connection_string_encrypted)
    try:
        service_client = BlobServiceClient.from_connection_string(conn_str)
        container_client = service_client.get_container_client(config.container_name)
        try:
            container_client.create_container()
        except ResourceExistsError:
            pass

        ips = get_active_blacklist_ips(db)
        chunks = build_chunks(ips, config.chunk_size)
        if not chunks:
            chunks = [[]]  # publish one empty part so FortiGate's feed doesn't 404

        cs_parts = _parse_connection_string(conn_str)
        account_name = cs_parts.get("AccountName")
        account_key = cs_parts.get("AccountKey")

        existing_parts = {p.part_index: p for p in db.query(PublishedFeedPart).all()}
        result_parts: list[PublishedFeedPart] = []
        sas_expiry = datetime.now(timezone.utc) + timedelta(days=config.sas_expiry_days)

        for idx, chunk in enumerate(chunks, start=1):
            blob_name = f"{config.blob_prefix}{idx}.txt"
            content = "\n".join(chunk) + ("\n" if chunk else "")
            new_hash = compute_hash(chunk)

            part = existing_parts.get(idx)
            if part is None:
                part = PublishedFeedPart(part_index=idx, blob_name=blob_name)
                db.add(part)

            blob_client = container_client.get_blob_client(blob_name)
            if part.content_hash != new_hash:
                blob_client.upload_blob(
                    content,
                    overwrite=True,
                    content_settings=ContentSettings(content_type="text/plain"),
                )
                part.content_hash = new_hash

            blob_url = blob_client.url
            if config.generate_sas and account_name and account_key:
                sas_token = generate_blob_sas(
                    account_name=account_name,
                    container_name=config.container_name,
                    blob_name=blob_name,
                    account_key=account_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=sas_expiry,
                )
                blob_url = f"{blob_client.url}?{sas_token}"
                part.sas_expires_at = sas_expiry

            part.blob_name = blob_name
            part.entry_count = len(chunk)
            part.blob_url = blob_url
            result_parts.append(part)

        # Shrink handling: empty out any previously-published parts that are no
        # longer needed, rather than leaving stale IPs live on an orphaned blob.
        for idx, stale_part in existing_parts.items():
            if idx > len(chunks):
                blob_client = container_client.get_blob_client(stale_part.blob_name)
                if stale_part.content_hash != compute_hash([]):
                    blob_client.upload_blob(
                        "", overwrite=True, content_settings=ContentSettings(content_type="text/plain")
                    )
                    stale_part.content_hash = compute_hash([])
                stale_part.entry_count = 0

        db.commit()
        total = sum(p.entry_count for p in result_parts)
        return True, f"Published {total} entries across {len(result_parts)} part(s)", result_parts

    except Exception as exc:  # noqa: BLE001 — surface any Azure SDK error to the caller/UI
        db.rollback()
        logger.exception("Azure publish failed")
        return False, f"Publish failed: {exc}", []
