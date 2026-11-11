"""Kept for compatibility: runs the same maintenance as `python -m yondo_api.jobs`."""

from yondo_api.jobs import run

if __name__ == '__main__':
    raise SystemExit(run())
