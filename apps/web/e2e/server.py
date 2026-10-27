"""E2E test backend: thin entry point. The harness (the REAL Yondo API on a throw-away SQLite file, DEMO seed, test
doubles for OTP/storage/identity) lives in infra/deploy/demo/demo_app.py because the public demo image runs the same code.

Usage: python server.py <port> <sqlite-file>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'infra' / 'deploy' / 'demo'))

import demo_app  # noqa: E402

demo_app.run()
