from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip
from app.core.rbac import require_admin, require_analyst, require_viewer
from app.core.security import encrypt_secret
from app.db.session import get_db
from app.models.threat_intel import ThreatIntelSource
from app.models.user import User
from app.schemas.device import TestConnectionResult
from app.schemas.threat_intel import ThreatIntelSourceCreate, ThreatIntelSourceOut, ThreatIntelSourceUpdate
from app.services.audit import log_action
from app.services.threat_intel import fetch_source

router = APIRouter(prefix="/threat-intel", tags=["threat-intel"])


@router.get("", response_model=list[ThreatIntelSourceOut], dependencies=[Depends(require_viewer)])
def list_sources(db: Session = Depends(get_db)):
    return db.query(ThreatIntelSource).order_by(ThreatIntelSource.name).all()


@router.post("", response_model=ThreatIntelSourceOut, status_code=status.HTTP_201_CREATED)
def create_source(
    payload: ThreatIntelSourceCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if db.query(ThreatIntelSource).filter(ThreatIntelSource.name == payload.name).one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "A source with this name already exists")
    source = ThreatIntelSource(
        name=payload.name,
        url=payload.url,
        format=payload.format,
        api_key_encrypted=encrypt_secret(payload.api_key),
        enabled=payload.enabled,
        refresh_interval_minutes=payload.refresh_interval_minutes,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    log_action(db, "threat_intel.create", "threat_intel_source", source.id, {"name": source.name}, admin, get_client_ip(request))
    return source


@router.patch("/{source_id}", response_model=ThreatIntelSourceOut)
def update_source(
    source_id: str,
    payload: ThreatIntelSourceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    source = db.get(ThreatIntelSource, source_id)
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found")
    data = payload.model_dump(exclude_unset=True)
    api_key = data.pop("api_key", None)
    for field, value in data.items():
        setattr(source, field, value)
    if api_key:
        source.api_key_encrypted = encrypt_secret(api_key)
    db.commit()
    db.refresh(source)
    log_action(db, "threat_intel.update", "threat_intel_source", source.id, data, admin, get_client_ip(request))
    return source


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(
    source_id: str, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    source = db.get(ThreatIntelSource, source_id)
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found")
    db.delete(source)
    db.commit()
    log_action(db, "threat_intel.delete", "threat_intel_source", source_id, user=admin, ip_address=get_client_ip(request))


@router.post("/{source_id}/fetch-now", response_model=TestConnectionResult, dependencies=[Depends(require_analyst)])
def fetch_now(source_id: str, db: Session = Depends(get_db)):
    source = db.get(ThreatIntelSource, source_id)
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found")
    ok, message, _count = fetch_source(db, source)
    return TestConnectionResult(ok=ok, message=message)
