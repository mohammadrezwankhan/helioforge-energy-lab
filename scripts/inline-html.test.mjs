import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {inlineDashboard} from './inline-html.mjs';
import {extractStaticPageText} from './static-page-text.mjs';
test('inline scripts preserve dollar replacement tokens and closing-tag strings literally',()=>{
  const value="$& $` $' </script><SCRIPT> </SCRIPT>";
  const html=inlineDashboard('<head><link rel="stylesheet" href="styles.css"></head><body><script src="app.js" defer></script></body>',{css:'p::before{content:"$&"}',js:'globalThis.example='+JSON.stringify(value)+';',favicon:''});
  assert.doesNotMatch(html,/<script src=/);
  assert.equal((html.match(/<\/script>/gi)||[]).length,1);
  const box={};vm.runInNewContext(html.match(/<script>([\s\S]*)<\/script>/)[1],box);
  assert.equal(box.example,value);assert.ok(html.includes('content:"$&"'));
});

test('static page extraction decodes nested anchor labels once', () => {
  const text = extractStaticPageText('<main><p>&lt;script&gt; &amp; &#39; &#x3c; <a href="/methodology/">&amp;lt;script&amp;gt;</a></p></main>',
    'https://example.test', '/', 'index.html');
  assert.equal(text, "<script> & ' < &lt;script&gt; (https://example.test/methodology/)");
});
