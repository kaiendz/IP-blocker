from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip
from app.core.rbac import require_admin, require_analyst, require_viewer
from app.core.security import decrypt_secret, encrypt_secret
from app.db.session import get_db
from app.models.device import ForticloudCredential, FortiGateDevice, LogSource
from app.models.user import User
from app.schemas.device import (
    DeviceCreate,
    DeviceOut,
    DeviceUpdate,
    ForticloudCredentialCreate,
    ForticloudCredentialOut,
    TestConnectionResult,
)
from app.services.audit import log_action
from app.services.forticloud_client import ForticloudClient
from app.services.fortigate_client import FortiGateClient
from app.services.poller import poll_device

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=list[DeviceOut], dependencies=[Depends(require_viewer)])
def list_devices(db: Session = Depends(get_db)):
    return db.query(FortiGateDevice).order_by(FortiGateDevice.name).all()


@router.post("", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def create_device(
    payload: DeviceCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    device = FortiGateDevice(
        name=payload.name,
        host=payload.host,
        port=payload.port,
        vdom=payload.vdom,
        api_token_encrypted=encrypt_secret(payload.api_token),
        verify_tls=payload.verify_tls,
        site_tag=payload.site_tag,
        poll_enabled=payload.poll_enabled,
        log_source=payload.log_source,
        forticloud_credential_id=payload.forticloud_credential_id,
        forticloud_serial=payload.forticloud_serial,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    log_action(db, "device.create", "device", device.id, {"name": device.name, "host": device.host}, admin, get_client_ip(request))
    return device


@router.patch("/{device_id}", response_model=DeviceOut)
def update_device(
    device_id: str,
    payload: DeviceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    device = db.get(FortiGateDevice, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found")
    data = payload.model_dump(exclude_unset=True)
    api_token = data.pop("api_token", None)
    for field, value in data.items():
        setattr(device, field, value)
    if api_token:
        device.api_token_encrypted = encrypt_secret(api_token)
    db.commit()
    db.refresh(device)
    log_action(db, "device.update", "device", device.id, {k: v for k, v in data.items()}, admin, get_client_ip(request))
    return device


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: str, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    device = db.get(FortiGateDevice, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found")
    db.delete(device)
    db.commit()
    log_action(db, "device.delete", "device", device_id, user=admin, ip_address=get_client_ip(request))


@router.post("/{device_id}/test-connection", response_model=TestConnectionResult, dependencies=[Depends(require_analyst)])
def test_connection(device_id: str, db: Session = Depends(get_db)):
    device = db.get(FortiGateDevice, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found")
    if device.log_source == LogSource.device_api:
        client = FortiGateClient(
            device.host, device.port, decrypt_secret(device.api_token_encrypted), device.verify_tls, device.vdom
        )
        ok, message = client.test_connection()
    else:
        if not device.forticloud_credential_id:
            return TestConnectionResult(ok=False, message="No FortiCloud credential linked")
        cred = db.get(ForticloudCredential, device.forticloud_credential_id)
        if cred is None:
            return TestConnectionResult(ok=False, message="Linked FortiCloud credential not found")
        client = ForticloudClient(
            decrypt_secret(cred.client_id_encrypted), decrypt_secret(cred.client_secret_encrypted), cred.api_gateway
        )
        ok, message = client.test_connection()
    return TestConnectionResult(ok=ok, message=message)


@router.post("/{device_id}/poll-now", response_model=TestConnectionResult, dependencies=[Depends(require_analyst)])
def poll_now(device_id: str, db: Session = Depends(get_db)):
    device = db.get(FortiGateDevice, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found")
    ok, message, count = poll_device(db, device)
    return TestConnectionResult(ok=ok, message=f"{message} ({count} event(s) ingested)")


# --- FortiCloud credentials ---

@router.get("/forticloud-credentials", response_model=list[ForticloudCredentialOut], dependencies=[Depends(require_viewer)])
def list_forticloud_credentials(db: Session = Depends(get_db)):
    return db.query(ForticloudCredential).order_by(ForticloudCredential.name).all()


@router.post("/forticloud-credentials", response_model=ForticloudCredentialOut, status_code=status.HTTP_201_CREATED)
def create_forticloud_credential(
    payload: ForticloudCredentialCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    cred = ForticloudCredential(
        name=payload.name,
        client_id_encrypted=encrypt_secret(payload.client_id),
        client_secret_encrypted=encrypt_secret(payload.client_secret),
        api_gateway=payload.api_gateway,
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    log_action(db, "forticloud_credential.create", "forticloud_credential", cred.id, {"name": cred.name}, admin, get_client_ip(request))
    return cred


@router.delete("/forticloud-credentials/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_forticloud_credential(
    credential_id: str, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    cred = db.get(ForticloudCredential, credential_id)
    if cred is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Credential not found")
    db.delete(cred)
    db.commit()
    log_action(db, "forticloud_credential.delete", "forticloud_credential", credential_id, user=admin, ip_address=get_client_ip(request))
