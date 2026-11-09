// Serve the reviewed snapshot. An optional loopback bridge exposes only hybrid runs.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
const artifact = new URL('../HelioForge-Preview.html', import.meta.url);
const page = await readFile(artifact);
const port = Number(process.env.PORT ?? 4173);
if (!Number.isInteger(port) || port < 0 || port > 65535) throw new Error('PORT must be an integer from 0 to 65535');
const configuredApi = process.env.HELIOFORGE_PREVIEW_API_PORT;
const apiPort = configuredApi ? Number(configuredApi) : null;
if (apiPort !== null && (!Number.isInteger(apiPort) || apiPort < 1 || apiPort > 65535)) throw new Error('HELIOFORGE_PREVIEW_API_PORT must be a loopback port from 1 to 65535');
const server = createServer(async (req, res) => {
  const path = (req.url ?? '/').split('?')[0];
  if (apiPort !== null && path?.startsWith('/api/')) {
    const address = server.address();
    if (!address || typeof address === 'string' || apiPort === address.port) { res.writeHead(503); res.end(); return; }
    const host = `127.0.0.1:${address.port}`;
    const origin = `http://${host}`;
    if (req.headers.host !== host || (req.headers.origin && req.headers.origin !== origin)) { res.writeHead(403); res.end(); return; }
    const getRoute = req.method === 'GET' && (path === '/api/overview' || path === '/api/runs' || /^\/api\/runs\/[0-9a-f-]{36}$/i.test(path));
    const postRoute = req.method === 'POST' && path === '/api/hybrid/simulate';
    if (!getRoute && !postRoute) { res.writeHead(404); res.end(); return; }
    if (postRoute && (req.headers.origin !== origin || !/^application\/json(?:\s*;|$)/i.test(req.headers['content-type'] ?? ''))) { res.writeHead(403); res.end(); return; }
    let size = 0;
    const chunks = [];
    try {
      for await (const chunk of req) {
        size += chunk.length;
        if (size <= 1_000_000) chunks.push(chunk);
      }
    } catch { return; }
    if (size > 1_000_000) { res.writeHead(413); res.end(); return; }
    const headers = {'Content-Type':'application/json', ...(req.headers.origin ? {Origin:req.headers.origin} : {})};
    try {
      const upstream = await fetch(`http://127.0.0.1:${apiPort}${req.url}`, {method:req.method, headers, ...(postRoute ? {body:Buffer.concat(chunks)} : {}), signal:AbortSignal.timeout(30000), redirect:'error'});
      res.writeHead(upstream.status, {'Content-Type':upstream.headers.get('content-type') ?? 'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Permissions-Policy':'camera=(), microphone=(), geolocation=()'});
      res.end(Buffer.from(await upstream.arrayBuffer()));
    } catch { if (!res.headersSent) res.writeHead(502); res.end(); }
    return;
  }
  if (!['GET','HEAD'].includes(req.method)) { res.writeHead(405, {Allow:'GET, HEAD'}); res.end(); return; }
  if (!['/','/index.html'].includes(path)) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, {'Content-Type':'text/html; charset=utf-8','Content-Length':page.length,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'});
  res.end(req.method === 'HEAD' ? undefined : page);
});
server.on('error', error => { console.error(`Preview failed: ${error.code ?? error.message}`); process.exitCode=1; });
server.listen(port,'127.0.0.1',()=>console.log(`HelioForge Energy Lab: http://127.0.0.1:${server.address().port} — synthetic local demo${apiPort === null ? ' (read-only)' : ' (hybrid API bridge enabled)'}`));
