from fastapi import APIRouter, Depends
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.core.rbac import require_admin
from app.db.session import get_db
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogOut
from app.schemas.common import Page

router = APIRouter(prefix="/audit", tags=["audit"], dependencies=[Depends(require_admin)])

_SORT_COLUMNS = {
    "created_at": AuditLog.created_at,
    "actor_label": AuditLog.actor_label,
    "action": AuditLog.action,
    "target_type": AuditLog.target_type,
}


@router.get("", response_model=Page[AuditLogOut])
def list_audit_log(
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
):
    column = _SORT_COLUMNS.get(sort_by, AuditLog.created_at)
    order = asc(column) if sort_dir == "asc" else desc(column)
    query = db.query(AuditLog).order_by(order)
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return Page(items=items, total=total, page=page, page_size=page_size)
