"""Fail if the Terminal release removes baseline source wiring or original model code."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'd14b71f50ef400a50d3ccd4792dcd59238c64f56'


def original(name: str) -> str:
    return subprocess.check_output(['git', 'show', f'{BASE}:{name}'], cwd=ROOT).decode().replace('\r\n', '\n')


paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE, 'apps/web/src'], cwd=ROOT).decode().splitlines()
old = '\n'.join(original(name) for name in paths if name.endswith('.ts'))
new = '\n'.join(path.read_text(encoding='utf-8') for path in (ROOT / 'apps/web/src').glob('*.ts'))
data_names = set(re.findall(r'data-([a-z][a-z0-9-]+)', old))
assert data_names <= set(re.findall(r'data-([a-z][a-z0-9-]+)', new)), 'Removed baseline data identity'
events = set(re.findall(r"addEventListener\(['\"]([^'\"]+)", old))
assert events <= set(re.findall(r"addEventListener\(['\"]([^'\"]+)", new)), 'Removed baseline event kind'
api = 'apps/api/helioforge/'
models = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE, api + 'engines'], cwd=ROOT).decode().splitlines()
preserved = [api + 'main.py', api + 'schemas.py', api + 'data/hybrid_catalog.json', *models]
for name in preserved:
    assert original(name) == (ROOT / name).read_text(encoding='utf-8'), f'Original model/contract changed: {name}'
print(json.dumps({'status': 'passed', 'baseline': BASE, 'data_identities': len(data_names),
                  'event_kinds': len(events), 'unchanged_model_and_contract_files': len(preserved)}))
