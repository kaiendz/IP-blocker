"""Role-based access control dependency helpers.

Roles are strictly ordered admin > analyst > viewer. Most endpoints just need
`require_role(UserRole.analyst)` ("analyst or higher"); a few admin-only
endpoints (user management, Azure/device secrets) need `require_role(UserRole.admin)`.
"""
from fastapi import Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.user import User, UserRole

_ROLE_RANK = {UserRole.viewer: 0, UserRole.analyst: 1, UserRole.admin: 2}


def require_role(minimum_role: UserRole):
    def _dependency(user: User = Depends(get_current_user)) -> User:
        if _ROLE_RANK[user.role] < _ROLE_RANK[minimum_role]:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"This action requires the '{minimum_role.value}' role or higher",
            )
        return user

    return _dependency


require_viewer = require_role(UserRole.viewer)
require_analyst = require_role(UserRole.analyst)
require_admin = require_role(UserRole.admin)
