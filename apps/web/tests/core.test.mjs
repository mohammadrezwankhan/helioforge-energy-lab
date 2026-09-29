import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const context=vm.createContext({URL,Intl,Number,String,Math,Array,Object,JSON,Set,structuredClone});
vm.runInContext(fs.readFileSync(new URL('../dist/app.js',import.meta.url),'utf8'),context);
const h=context.HF;
test('escapes HTML attributes and text',()=>assert.equal(h.escapeHTML('<script>"\'&'), '&lt;script&gt;&quot;&#39;&amp;'));
test('null is displayed as a dash, not a fictitious zero',()=>assert.equal(h.fmt(null),'—'));
test('zero is a valid number',()=>assert.equal(h.fmt(0),'0'));
test('money preserves negative sign',()=>assert.equal(h.money(-1234),'−€1,234'));
test('blocks javascript source URLs',()=>assert.equal(h.safeURL('javascript:alert(1)'),'#'));
test('allows HTTPS source URLs',()=>assert.equal(h.safeURL('https://www.cre.fr/'),'https://www.cre.fr/'));
test('CSV defuses spreadsheet formulas in text',()=>assert.equal(h.csvCell('=1+1'),'"\'=1+1"'));
test('CSV numeric negative remains numeric',()=>assert.equal(h.csvCell(-5),'"-5"'));
test('CSV escapes quotes',()=>assert.equal(h.csvCell('a"b'),'"a""b"'));
test('rejects blank numeric input',()=>assert.throws(()=>h.finiteInput('','CAPEX')));
test('rejects infinite numeric input',()=>assert.throws(()=>h.finiteInput('Infinity','CAPEX')));
test('accepts finite numeric input',()=>assert.equal(h.finiteInput('12.5','CAPEX'),12.5));
test('portfolio filter composes geography and search',()=>assert.equal(h.filterProjects(h.SNAPSHOT.portfolio,'FR','solstice').length,1));
test('portfolio zero results is supported',()=>assert.equal(h.filterProjects(h.SNAPSHOT.portfolio,'FR','missing').length,0));
test('snapshot states synthetic provenance',()=>assert.equal(h.SNAPSHOT.data_kind,'synthetic'));
test('all twelve views render without a DOM dependency',()=>{
 const state={hybrid:h.initialHybridState(),page:'overview',connected:false,busy:false,data:h.SNAPSHOT,marketFilter:'ALL',search:'',chartMode:'dispatch',forecastYears:20,runs:[],motionOff:false};
 for(const p of h.PAGES){state.page=p.id;assert.ok(h.content(state).length>500,p.id);}
});
test('charts have accessible titles and data tables',()=>{
 const chart=h.lineChart(['a','b'],[{name:'Power',values:[1,2],color:'#aaa'}],{unit:'MW'});
 assert.ok(chart.includes('role="img"'));assert.ok(chart.includes('<table>'));assert.ok(chart.includes('Power (MW)'));
});
test('clamp is bounded',()=>{assert.equal(h.clamp(99,0,10),10);assert.equal(h.clamp(-4,0,10),0);});

// Regression checks for edge states discovered during browser review.
test('empty charts show no-data rather than fabricated zero observations',()=>{
 assert.ok(h.lineChart([],[],{}).includes('No applicable observations'));
});
test('debt-free finance captions and overview do not claim a covenant breach',()=>{
 const data=JSON.parse(JSON.stringify(h.SNAPSHOT));
 data.finance.minimum_dscr=null;data.finance.covenant_pass=null;
 data.finance.rows.forEach(r=>r.dscr=null);
 const state={hybrid:h.initialHybridState(),page:'investment',connected:true,busy:false,data,marketFilter:'ALL',search:'',chartMode:'dispatch',forecastYears:20,runs:[],motionOff:false};
 assert.ok(h.content(state).includes('No debt service'));
 state.page='overview';assert.ok(h.content(state).includes('Unlevered screening case'));
});
