"""Import all ORM models so Base.metadata is fully populated for Alembic autogenerate."""
from app.db.base import Base  # noqa: F401
from app.models.user import User, UserRole  # noqa: F401
from app.models.device import FortiGateDevice, ForticloudCredential, PollCursor, LogSource  # noqa: F401
from app.models.auth_event import AuthEvent  # noqa: F401
from app.models.blacklist import BlacklistEntry, BlacklistReason, BlacklistStatus  # noqa: F401
from app.models.allowlist import AllowlistEntry  # noqa: F401
from app.models.threat_intel import ThreatIntelSource, ThreatIntelFormat  # noqa: F401
from app.models.rules import DetectionRule  # noqa: F401
from app.models.azure_publish import AzurePublishConfig, PublishedFeedPart  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401

__all__ = [
    "Base",
    "User",
    "UserRole",
    "FortiGateDevice",
    "ForticloudCredential",
    "PollCursor",
    "LogSource",
    "AuthEvent",
    "BlacklistEntry",
    "BlacklistReason",
    "BlacklistStatus",
    "AllowlistEntry",
    "ThreatIntelSource",
    "ThreatIntelFormat",
    "DetectionRule",
    "AzurePublishConfig",
    "PublishedFeedPart",
    "AuditLog",
]
