from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from yondo_api.models.user import AccountStatus, User, UserRoleType


def test_required_account_status_values_are_stable():
    assert {status.value for status in AccountStatus} == {
        'active',
        'verification_pending',
        'restricted',
        'suspended',
        'banned',
    }


def test_required_role_values_are_stable():
    assert {role.value for role in UserRoleType} == {
        'customer',
        'companion',
        'vendor',
        'admin',
    }


def test_phone_number_is_persisted_as_unique_private_data():
    table_sql = str(CreateTable(User.__table__).compile(dialect=postgresql.dialect()))
    assert 'phone_number' in table_sql
    assert User.__table__.c.phone_number.unique
