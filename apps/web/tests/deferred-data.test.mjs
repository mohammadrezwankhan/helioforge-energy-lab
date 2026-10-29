import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {createHash,webcrypto} from 'node:crypto';
const script=fs.readFileSync(new URL('../dist/app.js',import.meta.url),'utf8');
function fixture(value,fetcher){
  const bytes=Buffer.from(JSON.stringify(value)),sha256=createHash('sha256').update(bytes).digest('hex');
  const ref={path:`data/${sha256}.json`,sha256,bytes:bytes.length};
  const box=vm.createContext({URL,Intl,structuredClone,TextDecoder,Uint8Array,crypto:webcrypto,AbortSignal,location:{href:'https://example.test/run/#hybrid'},fetch:fetcher});
  vm.runInContext(script,box);return {hf:box.HF,ref,bytes,box};
}
test('verified example requests coalesce and preserve exact decoded data',async()=>{
  let calls=0;const f=fixture({x:[1,null,3]},async()=>{calls++;return {ok:true,arrayBuffer:async()=>f.bytes.buffer.slice(f.bytes.byteOffset,f.bytes.byteOffset+f.bytes.byteLength)};});
  const [a,b]=await Promise.all([f.hf.loadExampleAsset(f.ref),f.hf.loadExampleAsset(f.ref)]);
  assert.equal(JSON.stringify(a),'{"x":[1,null,3]}');assert.equal(a,b);assert.equal(calls,1);
});
test('network failure retries; same-size corruption cannot be cached as an example',async()=>{
  let calls=0;const f=fixture({x:1},async()=>{calls++;if(calls===1)throw Error('offline');const bytes=Buffer.from(calls===2?'{"x":2}':'{"x":1}');return {ok:true,arrayBuffer:async()=>bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength)};});
  await assert.rejects(f.hf.loadExampleAsset(f.ref),/offline/);
  await assert.rejects(f.hf.loadExampleAsset(f.ref),/integrity/);
  assert.equal(JSON.stringify(await f.hf.loadExampleAsset(f.ref)),'{"x":1}');assert.equal(calls,3);
});
test('manifest paths and sizes cannot escape the content-addressed local data directory',async()=>{
  const f=fixture({},()=>{throw Error('must not fetch');});
  await assert.rejects(f.hf.loadExampleAsset({...f.ref,path:'https://external.test/data.json'}),/manifest/);
  await assert.rejects(f.hf.loadExampleAsset({...f.ref,bytes:Infinity}),/manifest/);
});
