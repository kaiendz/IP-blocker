"""One-time bootstrap: creates the initial admin user, a default detection
rule, the seeded free threat-intel sources, and an empty Azure publish config
row, if they don't already exist. Safe to run repeatedly (idempotent)."""
import logging

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.azure_publish import AzurePublishConfig
from app.models.rules import DetectionRule
from app.models.threat_intel import ThreatIntelSource
from app.models.user import User, UserRole
from app.services.threat_intel import DEFAULT_SOURCES

logger = logging.getLogger(__name__)


def run_seed() -> None:
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == settings.BOOTSTRAP_ADMIN_EMAIL).one_or_none():
            db.add(
                User(
                    email=settings.BOOTSTRAP_ADMIN_EMAIL,
                    hashed_password=hash_password(settings.BOOTSTRAP_ADMIN_PASSWORD),
                    full_name="Administrator",
                    role=UserRole.admin,
                )
            )
            logger.warning(
                "Bootstrapped admin user %s — change this password immediately after first login.",
                settings.BOOTSTRAP_ADMIN_EMAIL,
            )

        if db.query(DetectionRule).count() == 0:
            db.add(
                DetectionRule(
                    name="Default brute-force rule",
                    scope="global",
                    event_types=["sslvpn"],
                    threshold_count=settings.DEFAULT_THRESHOLD_COUNT,
                    window_minutes=settings.DEFAULT_WINDOW_MINUTES,
                    ttl_hours=settings.DEFAULT_TTL_HOURS,
                    enabled=True,
                )
            )

        existing_names = {s.name for s in db.query(ThreatIntelSource.name).all()}
        for src in DEFAULT_SOURCES:
            if src["name"] not in existing_names:
                db.add(ThreatIntelSource(**src, enabled=False))  # off by default; enable per-source in the UI

        if db.query(AzurePublishConfig).count() == 0:
            db.add(AzurePublishConfig())

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_seed()
