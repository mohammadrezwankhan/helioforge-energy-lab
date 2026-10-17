import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const c=vm.createContext({URL,Intl,Number,String,Math,Array,Object,JSON,Set,Map,structuredClone});
vm.runInContext(fs.readFileSync(new URL('../dist/app.js',import.meta.url),'utf8'),c);
const h=c.HF;
const def={id:'test-study',page:'research',title:'<script>bad</script>',summary:'A test',fields:[{name:'age',label:'Age',default:10,min:0,max:100,step:1}],data_fields:[],equations:['x < y'],limitations:['Uncalibrated'],sources:[]};
const result={study:def.id,metrics:[{label:'Metric',value:null,unit:'MW'}],series:[{name:'Actual',x_label:'t',y_unit:'kW',x:[0,1,2],y:[-4,null,7]}],table:[],warnings:[],evidence_sha256:'abc',inputs:{age:10}};
test('study result preserves nulls and negative values and escapes labels',()=>{
 const html=h.studyResultView(def,result,0,0);assert.doesNotMatch(html,/<script>/);assert.match(html,/—/);assert.match(html,/-4/);assert.match(html,/7/);
});
test('study chart retains gaps instead of drawing an invented zero',()=>{
 const html=h.studyChart(result.series[0],0);assert.match(html,/Missing/);assert.doesNotMatch(html,/NaN|Infinity/);
});
test('study table CSV includes all records and neutralizes text formula injection',()=>{
 const csv=h.toCSV([{asset:'=HYPERLINK("x")',value:-3}]);assert.match(csv,/'=HYPERLINK/);assert.match(csv,/"-3"/);
});
