"""Kept for compatibility: runs the same maintenance as `python -m yondo_api.jobs`."""

import asyncio

from yondo_api.jobs import main

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
