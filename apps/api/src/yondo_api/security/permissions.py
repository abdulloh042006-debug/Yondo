from enum import StrEnum

from yondo_api.models.user import UserRoleType


class Permission(StrEnum):
    USE_MARKETPLACE = 'marketplace:use'
    MANAGE_COMPANION_PROFILE = 'companion_profile:manage'
    MANAGE_VENDOR_CATALOG = 'vendor_catalog:manage'
    ACCESS_ADMIN = 'admin:access'
    MODERATE_USERS = 'users:moderate'


ROLE_PERMISSIONS: dict[UserRoleType, frozenset[Permission]] = {
    UserRoleType.CUSTOMER: frozenset({Permission.USE_MARKETPLACE}),
    UserRoleType.COMPANION: frozenset(
        {Permission.USE_MARKETPLACE, Permission.MANAGE_COMPANION_PROFILE}
    ),
    UserRoleType.VENDOR: frozenset({Permission.MANAGE_VENDOR_CATALOG}),
    UserRoleType.ADMIN: frozenset({Permission.ACCESS_ADMIN, Permission.MODERATE_USERS}),
}


def has_permission(roles: set[UserRoleType], permission: Permission) -> bool:
    return any(permission in ROLE_PERMISSIONS.get(role, frozenset()) for role in roles)

