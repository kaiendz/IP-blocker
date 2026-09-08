from typing import Optional

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User


def log_action(
    db: Session,
    action: str,
    target_type: str = "",
    target_id: str = "",
    detail: Optional[dict] = None,
    user: Optional[User] = None,
    ip_address: str = "",
) -> None:
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            actor_label=user.email if user else "system",
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail or {},
            ip_address=ip_address,
        )
    )
    db.commit()
