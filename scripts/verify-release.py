"""Verify packaged file hashes and catalogue/source contracts without external access."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
manifest_path = ROOT / 'RELEASE_MANIFEST.json'
if not manifest_path.exists():
    raise SystemExit('RELEASE_MANIFEST.json is missing.')
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
failures = []
for item in manifest['files']:
    name = item['path']
    path = (ROOT / name).resolve()
    if not path.is_relative_to(ROOT):
        failures.append(f'Unsafe manifest path: {name}')
        continue
    if not path.is_file():
        failures.append(f'Missing: {name}')
    elif hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
        failures.append(f'Changed: {name}')
cat = json.loads((ROOT / 'apps/api/helioforge/data/hybrid_catalog.json').read_text(encoding='utf-8'))
if (len(cat['systems']), len(cat['scenarios']), len(cat['lessons'])) != (36, 24, 36):
    failures.append('Catalogue counts differ from this versioned release.')
if failures:
    print('\n'.join(failures), file=sys.stderr)
    raise SystemExit(1)
print(f"Verified {len(manifest['files'])} release file hashes and the 36/24/36 catalogue contract.")
print('Hashes detect release drift; they are not signatures or independent security validation.')
