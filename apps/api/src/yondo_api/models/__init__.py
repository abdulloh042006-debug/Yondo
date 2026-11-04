"""Import every ORM model so metadata (Alembic, tests) sees the complete schema."""

from yondo_api.companions import models as companion_models
from yondo_api.models.auth import AuthSession, OtpChallenge
from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType
from yondo_api.notifications import models as notification_models

__all__ = [
    'companion_models',
    'notification_models',
    'AccountStatus',
    'AuthSession',
    'OtpChallenge',
    'User',
    'UserRole',
    'UserRoleType',
]
