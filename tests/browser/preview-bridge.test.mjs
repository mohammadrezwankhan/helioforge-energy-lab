import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { createServer, request } from 'node:http';
import { test } from 'node:test';

async function preview(t, extra = {}) {
  const child = spawn(process.execPath, ['scripts/preview-demo.mjs'], {
    env: { ...process.env, PORT: '0', HELIOFORGE_PREVIEW_API_PORT: '', ...extra },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  t.after(() => child.kill());
  const [chunk] = await once(child.stdout, 'data');
  const base = String(chunk).match(/http:\/\/127\.0\.0\.1:\d+/)?.[0];
  assert.ok(base);
  return base;
}

test('default preview remains read-only', async (t) => {
  const base = await preview(t);
  assert.equal((await fetch(`${base}/api/overview`)).status, 404);
  assert.equal((await fetch(`${base}/api/hybrid/simulate`, {method:'POST'})).status, 405);
});

test('opt-in bridge permits only same-origin bounded hybrid routes', async (t) => {
  const calls = [];
  const upstream = createServer((req, res) => {
    calls.push([req.method, req.url, req.headers.origin]);
    res.writeHead(200, {'Content-Type':'application/json'});
    res.end(JSON.stringify({ok:true}));
  });
  upstream.listen(0, '127.0.0.1');
  await once(upstream, 'listening');
  t.after(() => upstream.close());
  const base = await preview(t, {HELIOFORGE_PREVIEW_API_PORT:String(upstream.address().port)});
  assert.equal((await fetch(`${base}/api/overview?market=DK`)).status, 200);
  assert.equal((await fetch(`${base}/api/runs`)).status, 200);
  const badHostStatus = await new Promise((resolve, reject) => {
    const req = request(`${base}/api/overview`, {headers:{host:'attacker.example'}}, res => {res.resume(); resolve(res.statusCode);});
    req.on('error', reject); req.end();
  });
  assert.equal(badHostStatus, 403);
  assert.equal((await fetch(`${base}/api/runs/not-a-uuid`)).status, 404);
  assert.equal((await fetch(`${base}/api/hybrid/simulate`, {method:'POST', headers:{'content-type':'application/json'}, body:'{}'})).status, 403);
  assert.equal((await fetch(`${base}/api/hybrid/simulate`, {method:'POST', headers:{origin:base,'content-type':'application/json'}, body:'{}'})).status, 200);
  assert.equal((await fetch(`${base}/api/hybrid/simulate`, {method:'POST', headers:{origin:'https://evil.example','content-type':'application/json'}, body:'{}'})).status, 403);
  assert.equal((await fetch(`${base}/api/hybrid/simulate`, {method:'POST', headers:{origin:base,'content-type':'application/json'}, body:'x'.repeat(1_000_001)})).status, 413);
  const chunkedStatus = await new Promise((resolve, reject) => {
    const req = request(`${base}/api/hybrid/simulate`, {method:'POST', headers:{origin:base,'content-type':'application/json','transfer-encoding':'chunked'}}, res => {res.resume(); resolve(res.statusCode);});
    req.on('error', reject); req.write('x'.repeat(600_000)); req.end('x'.repeat(400_001));
  });
  assert.equal(chunkedStatus, 413);
  assert.equal((await fetch(`${base}/api/evidence/document`, {method:'POST', headers:{origin:base,'content-type':'application/json'}, body:'{}'})).status, 404);
  assert.equal(calls.length, 3);
  assert.equal(calls[2][2], base);
});
