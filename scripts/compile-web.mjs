import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const web = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../apps/web');

// Emit scripts independently, then restore the declared global-namespace order.
// A fresh directory prevents removed sources from leaking stale JS into the bundle.
export function compileScripts(files, outFile) {
  files = files.map(file => path.resolve(file));
  let rootDir = path.dirname(files[0]);
  while (files.some(file => path.relative(rootDir, file).startsWith('..' + path.sep))) {
    rootDir = path.dirname(rootDir);
  }
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'hf-compile-'));
  try {
    execFileSync(process.execPath, [
      path.join(web, 'node_modules/typescript/bin/tsc'),
      '--target', 'ES2022', '--lib', 'ES2022,DOM,DOM.Iterable', '--strict',
      '--noUncheckedIndexedAccess', '--noImplicitOverride', '--noUnusedLocals',
      '--noUnusedParameters', '--module', 'preserve', '--moduleDetection', 'legacy',
      '--rootDir', rootDir, '--outDir', temp, ...files,
    ], {cwd: temp, stdio: 'pipe'});
    const js = files.map(file => fs.readFileSync(
      path.join(temp, path.relative(rootDir, file).replace(/\.ts$/, '.js')), 'utf8',
    )).join('\n;\n');
    fs.mkdirSync(path.dirname(outFile), {recursive: true});
    fs.writeFileSync(outFile, js + '\n');
  } finally {
    fs.rmSync(temp, {recursive: true, force: true});
  }
}
