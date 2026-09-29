import pytest
from fastapi.testclient import TestClient

from yondo_api.config import Settings
from yondo_api.main import create_application


@pytest.fixture
def app():
    return create_application(
        Settings(
            environment='test',
            database_url='postgresql+psycopg://yondo:yondo@localhost:5432/yondo_test',
            redis_url='redis://localhost:6379/15',
        )
    )


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client

