from yondo_api.models.user import UserRoleType
from yondo_api.security.permissions import Permission, has_permission


def test_admin_permission_is_not_inherited_by_customer():
    assert not has_permission({UserRoleType.CUSTOMER}, Permission.ACCESS_ADMIN)


def test_admin_has_moderation_permission():
    assert has_permission({UserRoleType.ADMIN}, Permission.MODERATE_USERS)


def test_two_sided_user_combines_role_permissions():
    roles = {UserRoleType.CUSTOMER, UserRoleType.COMPANION}
    assert has_permission(roles, Permission.USE_MARKETPLACE)
    assert has_permission(roles, Permission.MANAGE_COMPANION_PROFILE)

