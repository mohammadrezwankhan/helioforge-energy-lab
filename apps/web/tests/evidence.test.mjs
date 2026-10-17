import test from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import fs from 'node:fs';
import vm from 'node:vm';
const c=vm.createContext({URL,Intl,Number,String,Math,Array,Object,JSON,Set,Map,structuredClone,crypto:webcrypto,TextEncoder,Uint8Array,btoa,atob});
vm.runInContext(fs.readFileSync(new URL('../dist/app.js',import.meta.url),'utf8'),c);
const h=c.HF;
test('evidence canonical serialization ignores object insertion order but preserves arrays',()=>{
 assert.equal(h.canonicalEvidence({b:2,a:1}),h.canonicalEvidence({a:1,b:2}));
 assert.notEqual(h.canonicalEvidence([1,2]),h.canonicalEvidence([2,1]));
 assert.throws(()=>h.canonicalEvidence({value:Infinity}),/finite/);
});
test('actual browser signature verifies and tampering fails',async()=>{
 const e=await h.signEvidence({study:'test',value:4});
 assert.equal((await h.verifyEvidence(e)).valid,true);
 assert.match(e.signatures[0].identity,/unverified/);
 e.payload.value=5;assert.equal((await h.verifyEvidence(e)).valid,false);
});
test('multiple independently generated keys verify while duplicate signatures are rejected',async()=>{
 const a=await h.signEvidence({value:7}),b=await h.signEvidence({value:7});
 a.signatures.push(...b.signatures);assert.equal((await h.verifyEvidence(a)).signers,2);
 a.signatures.push(a.signatures[0]);assert.equal((await h.verifyEvidence(a)).valid,false);
});
