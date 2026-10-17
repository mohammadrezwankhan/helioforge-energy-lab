import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const context=vm.createContext({URL,Intl,Number,String,Math,Array,Object,JSON,Set,structuredClone});
vm.runInContext(fs.readFileSync(new URL('../dist/app.js',import.meta.url),'utf8'),context);
const h=context.HF;
test('storage timeline uses one actual dispatch interval and its own ratings',()=>{
 const d=structuredClone(h.SNAPSHOT.dispatch);d.power_kw=2345;d.capacity_kwh=7890;
 const html=h.storageTimeline(d,6);
 assert.match(html,/2\.345 MW/);assert.match(html,/7\.890 MWh/);
 assert.match(html,/06:00/);assert.match(html,/2,710\.6/);
 assert.doesNotMatch(html,/66\.2|50 MWp|ONLINE|SECURE/);
});
test('storage timeline clamps index and keeps separate battery charge and discharge',()=>{
 const d=h.SNAPSHOT.dispatch;
 assert.match(h.storageTimeline(d,-20),/value="0"/);
 assert.match(h.storageTimeline(d,999),/value="23"/);
 assert.match(h.storageTimeline(d,NaN),/value="0"/);
 assert.match(h.storageTimeline(d,13),/Charge/);
 assert.match(h.storageTimeline(d,6),/Discharge/);
 assert.match(h.storageTimeline(d,0),/Idle/);
});
test('storage timeline reports no schedule without inventing measurements',()=>{
 const html=h.storageTimeline({...h.SNAPSHOT.dispatch,schedule:[]},0);
 assert.match(html,/No dispatch intervals/);assert.doesNotMatch(html,/type="range"/);
});
test('storage labels and telemetry escape imported text',()=>{
 const d=structuredClone(h.SNAPSHOT.dispatch);d.schedule[0].label='<img src=x onerror=alert(1)>';
 const html=h.storageTimeline(d,0);assert.ok(!html.includes('<img'));assert.ok(html.includes('&lt;img'));
});
