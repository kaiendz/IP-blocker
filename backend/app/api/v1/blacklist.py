from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip
from app.core.rbac import require_analyst, require_viewer
from app.db.session import get_db
from app.models.blacklist import BlacklistEntry, BlacklistReason, BlacklistStatus
from app.models.user import User
from app.schemas.blacklist import BlacklistBulkRemove, BlacklistBulkResult, BlacklistManualCreate, BlacklistOut
from app.schemas.common import Page
from app.services.audit import log_action
from app.services.ip_safety import is_valid_ip_or_cidr

router = APIRouter(prefix="/blacklist", tags=["blacklist"])

# Allow-listed sort columns — never interpolate a client-supplied column name directly.
_SORT_COLUMNS = {
    "ip_or_cidr": BlacklistEntry.ip_or_cidr,
    "reason_type": BlacklistEntry.reason_type,
    "created_at": BlacklistEntry.created_at,
    "expires_at": BlacklistEntry.expires_at,
    "status": BlacklistEntry.status,
}


@router.get("", response_model=Page[BlacklistOut], dependencies=[Depends(require_viewer)])
def list_blacklist(
    db: Session = Depends(get_db),
    status_filter: Optional[BlacklistStatus] = None,
    reason_type: Optional[BlacklistReason] = None,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
):
    query = db.query(BlacklistEntry)
    if status_filter:
        query = query.filter(BlacklistEntry.status == status_filter)
    else:
        query = query.filter(BlacklistEntry.status == BlacklistStatus.active)
    if reason_type:
        query = query.filter(BlacklistEntry.reason_type == reason_type)
    if q:
        query = query.filter(BlacklistEntry.ip_or_cidr.ilike(f"%{q}%"))

    column = _SORT_COLUMNS.get(sort_by, BlacklistEntry.created_at)
    order = asc(column) if sort_dir == "asc" else desc(column)

    total = query.count()
    items = query.order_by(order).offset((page - 1) * page_size).limit(page_size).all()
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=BlacklistOut, status_code=status.HTTP_201_CREATED)
def add_manual_entry(
    payload: BlacklistManualCreate,
    request: Request,
    db: Session = Depends(get_db),
    analyst: User = Depends(require_analyst),
):
    if not is_valid_ip_or_cidr(payload.ip_or_cidr):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Not a valid IP address or CIDR")
    expires_at = (
        datetime.now(timezone.utc) + timedelta(hours=payload.ttl_hours) if payload.ttl_hours else None
    )
    entry = BlacklistEntry(
        ip_or_cidr=payload.ip_or_cidr,
        reason_type=BlacklistReason.manual,
        reason_detail=payload.reason_detail,
        created_by=analyst.email,
        expires_at=expires_at,
        status=BlacklistStatus.active,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    log_action(db, "blacklist.add", "blacklist_entry", entry.id, {"ip": entry.ip_or_cidr}, analyst, get_client_ip(request))
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_entry(
    entry_id: str, request: Request, db: Session = Depends(get_db), analyst: User = Depends(require_analyst)
):
    entry = db.get(BlacklistEntry, entry_id)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entry not found")
    entry.status = BlacklistStatus.removed
    db.commit()
    log_action(db, "blacklist.remove", "blacklist_entry", entry_id, {"ip": entry.ip_or_cidr}, analyst, get_client_ip(request))


@router.post("/bulk-remove", response_model=BlacklistBulkResult)
def bulk_remove(
    payload: BlacklistBulkRemove,
    request: Request,
    db: Session = Depends(get_db),
    analyst: User = Depends(require_analyst),
):
    entries = (
        db.query(BlacklistEntry)
        .filter(BlacklistEntry.id.in_(payload.ids), BlacklistEntry.status == BlacklistStatus.active)
        .all()
    )
    ips = [e.ip_or_cidr for e in entries]
    for entry in entries:
        entry.status = BlacklistStatus.removed
    db.commit()
    log_action(
        db,
        "blacklist.bulk_remove",
        "blacklist_entry",
        ",".join(payload.ids),
        {"count": len(entries), "ips": ips},
        analyst,
        get_client_ip(request),
    )
    return BlacklistBulkResult(removed_count=len(entries))
