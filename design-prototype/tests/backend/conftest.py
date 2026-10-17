"""Re-uses the backend's own fixtures so these tests run against the REAL FastAPI app + real DB (SQLite by default,
PostgreSQL when YONDO_TEST_DATABASE_URL is set). Run from apps/api:  python -m pytest ../../design-prototype/tests/backend -c pyproject.toml"""
import pathlib
import sys

API = pathlib.Path(__file__).resolve().parents[3] / 'apps' / 'api'
sys.path.insert(0, str(API))
pytest_plugins = ['tests.companions.conftest']
