from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip
from app.core.rbac import require_analyst, require_viewer
from app.db.session import get_db
from app.models.allowlist import AllowlistEntry
from app.models.user import User
from app.schemas.allowlist import AllowlistCreate, AllowlistOut
from app.services.audit import log_action
from app.services.ip_safety import is_valid_ip_or_cidr

router = APIRouter(prefix="/allowlist", tags=["allowlist"])


@router.get("", response_model=list[AllowlistOut], dependencies=[Depends(require_viewer)])
def list_allowlist(db: Session = Depends(get_db)):
    return db.query(AllowlistEntry).order_by(AllowlistEntry.created_at.desc()).all()


@router.post("", response_model=AllowlistOut, status_code=status.HTTP_201_CREATED)
def add_allowlist_entry(
    payload: AllowlistCreate,
    request: Request,
    db: Session = Depends(get_db),
    analyst: User = Depends(require_analyst),
):
    if not is_valid_ip_or_cidr(payload.ip_or_cidr):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Not a valid IP address or CIDR")
    if db.query(AllowlistEntry).filter(AllowlistEntry.ip_or_cidr == payload.ip_or_cidr).one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Already on the allowlist")
    entry = AllowlistEntry(ip_or_cidr=payload.ip_or_cidr, note=payload.note, created_by=analyst.email)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    log_action(db, "allowlist.add", "allowlist_entry", entry.id, {"ip": entry.ip_or_cidr}, analyst, get_client_ip(request))
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_allowlist_entry(
    entry_id: str, request: Request, db: Session = Depends(get_db), analyst: User = Depends(require_analyst)
):
    entry = db.get(AllowlistEntry, entry_id)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entry not found")
    db.delete(entry)
    db.commit()
    log_action(db, "allowlist.remove", "allowlist_entry", entry_id, {"ip": entry.ip_or_cidr}, analyst, get_client_ip(request))
