import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

test('download clicks after the initiating event and revokes its blob URL afterward',()=>{
 const tasks=[],created=[],revoked=[],clicked=[];
 const url={createObjectURL(blob){const value=`blob:test/${created.length+1}`;created.push({url:value,type:blob.type,size:blob.size});return value;},revokeObjectURL(value){revoked.push(value);}};
 const document={readyState:'loading',addEventListener(){},createElement(tag){assert.equal(tag,'a');return {href:'',download:'',click(){clicked.push({href:this.href,download:this.download});}};}};
 const context=vm.createContext({URL:url,Blob,document,setTimeout:(callback,delay)=>{tasks.push({callback,delay});return tasks.length;},Intl,Number,String,Math,Array,Object,JSON,Set,structuredClone});
 const bundle=process.env.HF_DOWNLOAD_TEST_BUNDLE??new URL('../dist/app.js',import.meta.url);
 vm.runInContext(fs.readFileSync(bundle,'utf8'),context);

 context.HF.download('study.csv','a,b\r\n1,2','text/csv');
 assert.deepEqual(created,[{url:'blob:test/1',type:'text/csv',size:8}]);
 assert.deepEqual(clicked,[]);
 assert.equal(tasks.length,1);
 assert.equal(tasks[0].delay,0);

 tasks.shift().callback();
 assert.deepEqual(clicked,[{href:'blob:test/1',download:'study.csv'}]);
 assert.equal(tasks.length,1);
 assert.equal(tasks[0].delay,1000);
 assert.deepEqual(revoked,[]);

 tasks.shift().callback();
 assert.deepEqual(revoked,['blob:test/1']);
});
