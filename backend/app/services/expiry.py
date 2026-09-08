"""Expires blacklist entries whose TTL has passed."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.blacklist import BlacklistEntry, BlacklistStatus


def expire_due_entries(db: Session) -> int:
    now = datetime.now(timezone.utc)
    due = (
        db.query(BlacklistEntry)
        .filter(
            BlacklistEntry.status == BlacklistStatus.active,
            BlacklistEntry.expires_at.is_not(None),
            BlacklistEntry.expires_at <= now,
        )
        .all()
    )
    for entry in due:
        entry.status = BlacklistStatus.expired
    db.commit()
    return len(due)
