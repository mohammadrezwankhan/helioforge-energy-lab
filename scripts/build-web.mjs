import { readFile, writeFile, mkdir, copyFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const web=path.join(root,'apps/web'), dist=path.join(web,'dist');
await mkdir(dist,{recursive:true});
for(const [from,to] of [['index.html','index.html'],['src/styles.css','styles.css'],['public/favicon.svg','favicon.svg']])await copyFile(path.join(web,from),path.join(dist,to));
const html=await readFile(path.join(web,'index.html'),'utf8');
const css=(await readFile(path.join(web,'src/styles.css'),'utf8'))+'\n'+(await readFile(path.join(web,'src/champion.css'),'utf8'));
await writeFile(path.join(dist,'styles.css'),css);
const js=await readFile(path.join(dist,'app.js'),'utf8');
const favicon=await readFile(path.join(web,'public/favicon.svg'),'utf8');
const standalone=html.replace('<link rel="icon" href="favicon.svg" type="image/svg+xml">',`<link rel="icon" href="data:image/svg+xml,${encodeURIComponent(favicon)}" type="image/svg+xml">`)
  .replace('<link rel="stylesheet" href="styles.css">',`<style>${css}</style>`)
  .replace('<script src="app.js" defer></script>',`<script>${js.replaceAll('</script','<\\/script')}</script>`);
await writeFile(path.join(root,'HelioForge-Preview.html'),standalone);
console.log(`Built dashboard and standalone preview (${(Buffer.byteLength(standalone)/1024).toFixed(1)} KiB, no runtime dependencies).`);
