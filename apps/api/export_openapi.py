"""Export or verify the checked-in frontend OpenAPI contract.

Run from apps/api:
    python export_openapi.py
    python export_openapi.py --check

This script generates a schema only; no database or external network is used.
"""

import json
import sys
from pathlib import Path

from yondo_api.config import Settings
from yondo_api.main import create_application


def main() -> int:
    app = create_application(
        Settings(
            _env_file=None,
            environment='test',
            database_url='sqlite+aiosqlite:///:memory:',
        )
    )
    output = json.dumps(
        app.openapi(), ensure_ascii=False, sort_keys=True, indent=2
    ) + '\n'
    target = Path(__file__).resolve().parents[2] / 'docs' / 'openapi-v1.json'
    if '--check' in sys.argv:
        if not target.exists() or target.read_text(encoding='utf-8') != output:
            print('Frontend OpenAPI contract is outdated. Run python export_openapi.py.')
            return 1
        print('Frontend OpenAPI contract matches FastAPI.')
        return 0
    target.write_text(output, encoding='utf-8')
    print(f'Exported {len(app.openapi()["paths"])} endpoints to {target}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
