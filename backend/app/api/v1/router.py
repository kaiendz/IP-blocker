from fastapi import APIRouter

from app.api.v1 import (
    allowlist,
    audit,
    auth,
    azure_publish,
    blacklist,
    dashboard,
    devices,
    events,
    rules,
    threat_intel,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(devices.router)
api_router.include_router(events.router)
api_router.include_router(blacklist.router)
api_router.include_router(allowlist.router)
api_router.include_router(threat_intel.router)
api_router.include_router(rules.router)
api_router.include_router(azure_publish.router)
api_router.include_router(audit.router)
api_router.include_router(dashboard.router)
