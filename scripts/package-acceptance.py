"""Package review changes, raw evidence, and the exact local candidate site."""
import hashlib
import json
import os
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('HELIOFORGE_EVIDENCE_DIR', ROOT / 'docs/remediation-20261028'))
SITE = Path(os.environ.get('HELIOFORGE_ACCEPTANCE_SITE', ROOT / '.cloudflare/acceptance-final/site'))
PREFIX = OUT.relative_to(ROOT).as_posix()
DELIVERY = ROOT.parent / 'delivery'
DELIVERY.mkdir(exist_ok=True)
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)
(OUT / 'review.patch').write_bytes(git('diff', '--binary', '--full-index', 'HEAD'))
changed=set(git('diff','--name-only','-z','HEAD').decode().split('\0'))
changed.update(git('ls-files','--others','--exclude-standard','-z').decode().split('\0'))
files={relative:ROOT/relative for relative in changed if relative and (ROOT/relative).is_file()}
# Empty shell-diagnostic redirection artifact; never part of the application or delivery.
files.pop('x.bytes)))', None)
files.pop(PREFIX+'/DELIVERY_MANIFEST.json', None)
# Ignored logs are intentional evidence. Include them explicitly, excluding this active log.
for path in OUT.rglob('*'):
    if path.is_file() and path.name not in {'package.log','DELIVERY_MANIFEST.json'}:
        files[path.relative_to(ROOT).as_posix()]=path
for path in SITE.rglob('*'):
    if path.is_file():
        files['candidate-site/'+path.relative_to(SITE).as_posix()]=path
manifest={'schema':'helioforge.delivery.v1','base_commit':git('rev-parse','HEAD').decode().strip(),
          'contents':'Changed/new files relative to the source baseline, including tests and raw evidence; tracked diff in review.patch; exact ready-to-serve candidate in candidate-site/. No installed dependencies, credentials, local SQLite, temporary TLS key, or production publication.',
          'files':[{'path':name,'bytes':p.stat().st_size,'sha256':sha(p)} for name,p in sorted(files.items())]}
(OUT/'DELIVERY_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
files[PREFIX+'/DELIVERY_MANIFEST.json']=OUT/'DELIVERY_MANIFEST.json'
archive=DELIVERY/os.environ.get('HELIOFORGE_ARCHIVE_NAME','helioforge-remediation-source-and-evidence.zip')
if archive.parent.resolve()!=DELIVERY.resolve():
    raise ValueError('Archive must be a filename within the delivery directory')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for name,path in sorted(files.items()):
        z.write(path,name)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None, 'Archive CRC verification failed'
delivery={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),
          'manifest':str(OUT/'DELIVERY_MANIFEST.json'),'files':len(files),'production_changed':False}
(DELIVERY/(archive.stem+'-receipt.json')).write_text(json.dumps(delivery,indent=2)+'\n',encoding='utf-8')
print(json.dumps(delivery))
