import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { gunzipSync } from 'node:zlib';

const priorDigest = '0c10ffc6f2e0c1b37ec2131125c62411116cf463ee27398a6fe06e5198df5936';
const priorFileHash = 'ee6ad1e6d44e89f5971fbf2e27a07c05de2dfeef76bba171456c15b1b2cad546';
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');

// Existing exports contain case digests. Preserve those exact URLs across v1 publications.
export function preserveHybridPublications(examples, runtime, currentDigest) {
  const previous = gunzipSync(readFileSync(join(examples, 'publications', priorDigest + '.json.gz')));
  if (sha256(previous) !== priorFileHash) throw Error('Archived v1 publication bytes changed');
  const archive = JSON.parse(previous);
  const current = readFileSync(join(examples, 'hybrid-bundle.json'));
  const next = JSON.parse(current);
  if (archive.dataset_sha256 !== priorDigest || next.dataset_sha256 !== currentDigest ||
      !/^[a-f0-9]{64}$/.test(currentDigest)) throw Error('Invalid v1 publication digest');
  if (currentDigest === priorDigest && !previous.equals(current)) throw Error('Conflicting v1 publication');
  const cases = new Map(next.cases.map(entry => [entry.id, entry]));
  for (const entry of archive.cases) {
    const updated = cases.get(entry.id);
    if (!updated || updated.result.input_sha256 !== entry.result.input_sha256) {
      throw Error('Archived v1 case identity changed: ' + entry.id);
    }
    const bytes = JSON.stringify(entry);
    writeFileSync(join(runtime, 'data', sha256(bytes) + '.json'), bytes);
  }
  const catalog = join(runtime, 'publications');
  mkdirSync(catalog, { recursive: true });
  writeFileSync(join(catalog, priorDigest + '.json'), previous);
  writeFileSync(join(catalog, currentDigest + '.json'), current);
}
