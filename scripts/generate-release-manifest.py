"""Record versioned release inputs; text hashes use explicit LF normalization."""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
names = subprocess.check_output(
    ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT,
).decode().split('\0')
files = []
for name in sorted(set(names)):
    if not name or name == 'RELEASE_MANIFEST.json':
        continue
    path = ROOT / name
    if not path.is_file():
        continue
    data = path.read_bytes()
    item = {'path': name, 'bytes': len(data)}
    if not name.startswith(('assets/engineering-hero/', 'docs/champion/')) and name != 'start-windows.cmd':
        try:
            data.decode('utf-8')
            if b'\0' not in data:
                data = data.replace(b'\r\n', b'\n')
                item['text_mode'] = 'lf'
                item['bytes'] = len(data)
        except UnicodeError:
            pass
    item['sha256'] = hashlib.sha256(data).hexdigest()
    files.append(item)
browser = json.loads((ROOT / 'docs/terminal-audit/browser-terminal.json').read_text(encoding='utf-8'))
manifest = {
    'application': 'HelioForge Terminal', 'version': '2.0.0', 'build_id': 'terminal-2.0.0',
    'prepared_utc': datetime.now(UTC).isoformat(),
    'intended_use': 'bounded synthetic research and education; see deployment receipt for publication',
    'catalog_version': '0.2.0',
    'catalogue_counts': {'architectures': 36, 'runnable_architectures': 19,
                         'study_only_architectures': 17, 'scenarios': 24, 'lessons': 36,
                         'runnable_combinations': 285},
    'verification': {'backend_tests_passed': 653, 'frontend_tests_passed': 186,
                     'browser': browser['summary'],
                     'backend_warnings': 'Two upstream TestClient deprecations; no product warning suppressed.'},
    'upstream_revision': 'd14b71f50ef400a50d3ccd4792dcd59238c64f56',
    'hash_semantics': 'SHA-256; LF-normalized UTF-8 where text_mode=lf, exact bytes otherwise; not signatures',
    'file_list_sha256': hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
    'files': files,
}
(ROOT / 'RELEASE_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
print(f'Recorded {len(files)} release inputs.')
