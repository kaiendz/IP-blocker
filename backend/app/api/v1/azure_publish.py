from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip
from app.core.rbac import require_admin, require_analyst, require_viewer
from app.core.security import encrypt_secret
from app.db.session import get_db
from app.models.azure_publish import AzurePublishConfig, PublishedFeedPart
from app.models.user import User
from app.schemas.azure_publish import (
    AzurePublishConfigOut,
    AzurePublishConfigUpdate,
    PublishedFeedPartOut,
    PublishNowResult,
)
from app.services.audit import log_action
from app.services.azure_publisher import publish

router = APIRouter(prefix="/azure-publish", tags=["azure-publish"])


def _get_or_create_config(db: Session) -> AzurePublishConfig:
    config = db.query(AzurePublishConfig).first()
    if config is None:
        config = AzurePublishConfig()
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def _to_out(config: AzurePublishConfig) -> AzurePublishConfigOut:
    return AzurePublishConfigOut(
        container_name=config.container_name,
        blob_prefix=config.blob_prefix,
        chunk_size=config.chunk_size,
        sas_expiry_days=config.sas_expiry_days,
        publish_interval_minutes=config.publish_interval_minutes,
        generate_sas=config.generate_sas,
        enabled=config.enabled,
        has_connection_string=bool(config.connection_string_encrypted),
        has_sas_url=bool(config.sas_url_encrypted),
    )


@router.get("/config", response_model=AzurePublishConfigOut, dependencies=[Depends(require_viewer)])
def get_config(db: Session = Depends(get_db)):
    return _to_out(_get_or_create_config(db))


@router.put("/config", response_model=AzurePublishConfigOut)
def update_config(
    payload: AzurePublishConfigUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    config = _get_or_create_config(db)
    data = payload.model_dump(exclude_unset=True)
    conn_str = data.pop("connection_string", None)
    sas_url = data.pop("sas_url", None)
    for field, value in data.items():
        setattr(config, field, value)
    if conn_str:
        config.connection_string_encrypted = encrypt_secret(conn_str)
    if sas_url:
        config.sas_url_encrypted = encrypt_secret(sas_url)
    db.commit()
    db.refresh(config)
    log_action(db, "azure_publish.config_update", "azure_publish_config", config.id, {k: v for k, v in data.items()}, admin, get_client_ip(request))
    return _to_out(config)


@router.get("/parts", response_model=list[PublishedFeedPartOut], dependencies=[Depends(require_viewer)])
def list_parts(db: Session = Depends(get_db)):
    return db.query(PublishedFeedPart).order_by(PublishedFeedPart.part_index).all()


@router.post("/publish-now", response_model=PublishNowResult, dependencies=[Depends(require_analyst)])
def publish_now(request: Request, db: Session = Depends(get_db), analyst: User = Depends(require_analyst)):
    ok, message, parts = publish(db)
    log_action(db, "azure_publish.publish_now", "azure_publish", "", {"ok": ok, "message": message}, analyst, get_client_ip(request))
    return PublishNowResult(ok=ok, message=message, parts=parts)
