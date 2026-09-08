from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip
from app.core.rbac import require_admin, require_viewer
from app.db.session import get_db
from app.models.rules import DetectionRule
from app.models.user import User
from app.schemas.rules import DetectionRuleCreate, DetectionRuleOut, DetectionRuleUpdate
from app.services.audit import log_action

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=list[DetectionRuleOut], dependencies=[Depends(require_viewer)])
def list_rules(db: Session = Depends(get_db)):
    return db.query(DetectionRule).order_by(DetectionRule.name).all()


@router.post("", response_model=DetectionRuleOut, status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: DetectionRuleCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    rule = DetectionRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    log_action(db, "rule.create", "detection_rule", rule.id, {"name": rule.name}, admin, get_client_ip(request))
    return rule


@router.patch("/{rule_id}", response_model=DetectionRuleOut)
def update_rule(
    rule_id: str,
    payload: DetectionRuleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    rule = db.get(DetectionRule, rule_id)
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    log_action(db, "rule.update", "detection_rule", rule.id, data, admin, get_client_ip(request))
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    rule_id: str, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    rule = db.get(DetectionRule, rule_id)
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    db.delete(rule)
    db.commit()
    log_action(db, "rule.delete", "detection_rule", rule_id, user=admin, ip_address=get_client_ip(request))
