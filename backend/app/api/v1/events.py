from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.core.rbac import require_viewer
from app.db.session import get_db
from app.models.auth_event import AuthEvent
from app.schemas.auth_event import AuthEventOut
from app.schemas.common import Page

router = APIRouter(prefix="/events", tags=["events"], dependencies=[Depends(require_viewer)])

_SORT_COLUMNS = {
    "event_time": AuthEvent.event_time,
    "src_ip": AuthEvent.src_ip,
    "username": AuthEvent.username,
    "vpn_type": AuthEvent.vpn_type,
    "action": AuthEvent.action,
}


@router.get("", response_model=Page[AuthEventOut])
def list_events(
    db: Session = Depends(get_db),
    device_id: Optional[str] = None,
    src_ip: Optional[str] = None,
    vpn_type: Optional[str] = None,
    action: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "event_time",
    sort_dir: str = "desc",
):
    query = db.query(AuthEvent)
    if device_id:
        query = query.filter(AuthEvent.device_id == device_id)
    if src_ip:
        query = query.filter(AuthEvent.src_ip == src_ip)
    if vpn_type:
        query = query.filter(AuthEvent.vpn_type == vpn_type)
    if action:
        query = query.filter(AuthEvent.action == action)

    column = _SORT_COLUMNS.get(sort_by, AuthEvent.event_time)
    order = asc(column) if sort_dir == "asc" else desc(column)

    total = query.count()
    items = query.order_by(order).offset((page - 1) * page_size).limit(page_size).all()
    return Page(items=items, total=total, page=page, page_size=page_size)
