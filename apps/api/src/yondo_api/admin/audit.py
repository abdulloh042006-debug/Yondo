from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.core.time import utc_now
from yondo_api.models.user import User
from yondo_api.safety.models import AdminAuditLog


def audit(
    session: AsyncSession,
    admin: User,
    action: str,
    target_type: str,
    target_id: UUID,
    reason: str = '',
    data: dict[str, Any] | None = None,
) -> None:
    session.add(
        AdminAuditLog(
            admin_id=admin.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            reason=reason,
            data={key: str(value) for key, value in (data or {}).items()},
            created_at=utc_now(),
        )
    )
