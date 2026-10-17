// Guard against preview-only patches disappearing during the next source build.
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import assert from 'node:assert/strict';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const [preview,js,css]=await Promise.all(['HelioForge-Preview.html','apps/web/dist/app.js','apps/web/dist/styles.css'].map(p=>readFile(path.join(root,p),'utf8')));
assert(preview.includes(`<script>${js.replaceAll('</script','<\\/script')}</script>`),'Standalone script diverges from compiled source');
assert(preview.includes(`<style>${css}</style>`),'Standalone stylesheet diverges from compiled source');
for(const source of ['styles.css','champion.css','study-visuals.css','workflows.css','experiences.css'])assert(css.includes(await readFile(path.join(root,'apps/web/src',source),'utf8')),`Missing source CSS: ${source}`);
assert(js.includes('createStudyController')&&js.includes('createWorkflowController'));
console.log('PASS standalone runtime and stylesheet exactly match compiled canonical sources');
