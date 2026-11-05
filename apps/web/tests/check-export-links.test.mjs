import test from 'node:test';
import assert from 'node:assert/strict';
import {hasAnchorUnder,hasExactAnchor,hasGuideLink,parseHtmlDocument} from '../../../scripts/html-document.mjs';

const methodology='https://mktrade.co.business/methodology/';
const profile='https://mrkhan.co.technology/';

test('HTML evidence extracts real script bodies and decoded link attributes',()=>{
  const document=parseHtmlDocument('<SCRIPT src="app.js?x=1&amp;y=2"></SCRIPT><script>const value="<a href=not-a-link>";</script><A HREF="https://mktrade.co.business/methodology&#47;">MKTrade <strong>methodology</strong></A>');
  assert.deepEqual(document.scripts,[{src:'app.js?x=1&y=2',body:''},{src:null,body:'const value="<a href=not-a-link>";'}]);
  assert.deepEqual(document.anchors,[{href:methodology,text:'MKTrade methodology'}]);
});

test('script extraction follows browser raw-text end tag boundaries',()=>{
  for(const closing of ['</script>','</SCRIPT>','</script\t\n data-fixture>','</script/>']){
    const document=parseHtmlDocument('<script>const value=1;'+closing+'<script>const next=2;</script>');
    assert.deepEqual(document.scripts.map(script=>script.body),['const value=1;','const next=2;']);
  }
});

test('an exact required anchor permits browser-normalized host and port',()=>{
  assert.equal(hasExactAnchor('<a href="https://MKTRADE.CO.BUSINESS:443/methodology/">MKTrade <strong>methodology</strong></a>',methodology,'MKTrade methodology'),true);
  assert.equal(hasExactAnchor('<a href="https://mktrade.co.business/methodology&#47;">MKTrade methodology</a>',methodology),true);
});

test('required anchors reject URL substrings and altered destinations',()=>{
  const wrongDestinations=[
    'https://example.invalid/https://mktrade.co.business/methodology/',
    'https://example.invalid/?next=https://mktrade.co.business/methodology/',
    'https://example.invalid/#https://mktrade.co.business/methodology/',
    'https://mktrade.co.business.example.invalid/methodology/',
    'https://mktrade.co.business@example.invalid/methodology/',
    'https://viewer@mktrade.co.business/methodology/',
    'http://mktrade.co.business/methodology/',
    'https://mktrade.co.business/methodology/extra/',
    'https://mktrade.co.business/methodology/?next=example',
    '//mktrade.co.business/methodology/',
    'not-a-url',
  ];
  for(const href of wrongDestinations)assert.equal(hasExactAnchor(`<a href="${href}">MKTrade methodology</a>`,methodology),false,href);
});

test('a URL in text, comments, scripts, or inert markup cannot satisfy a link gate',()=>{
  const documents=[
    `<p>${methodology}</p>`,
    `<!-- <a href="${methodology}">MKTrade methodology</a> -->`,
    `<script>const value='<a href="${methodology}">MKTrade methodology</a>';</script>`,
    `<textarea><a href="${methodology}">MKTrade methodology</a></textarea>`,
    `<div data-href="${methodology}">MKTrade methodology</div>`,
    `<a href="https://example.invalid/">${methodology}</a>`,
    `<template><a href="${methodology}">MKTrade methodology</a></template>`,
    `<noscript><a href="${methodology}">MKTrade methodology</a></noscript>`,
  ];
  for(const html of documents)assert.equal(hasExactAnchor(html,methodology),false,html);
});

test('duplicate attributes follow the browser first href and preserve link text requirements',()=>{
  assert.equal(hasExactAnchor(`<a href="https://example.invalid/" href="${methodology}">MKTrade methodology</a>`,methodology),false);
  assert.equal(hasExactAnchor(`<a href="${methodology}" href="https://example.invalid/">MKTrade methodology</a>`,methodology),true);
  assert.equal(hasExactAnchor(`<a href="${profile}">Different author</a>`,profile,'Mohammad Rezwan Khan'),false);
});

test('retired application links are detected by their parsed origin and path',()=>{
  const retired='https://khanlab.co.technology/apps/';
  for(const href of [retired,retired+'old/','https://KHANLAB.CO.TECHNOLOGY:443/apps/old/','https://viewer@khanlab.co.technology/apps/','https://khanlab.co.technology/other/../apps/']){
    assert.equal(hasAnchorUnder(`<a href="${href}">Old application</a>`,retired,'https://mklab.co.technology/'),true,href);
  }
  assert.equal(hasAnchorUnder('<a href="https://khanlab.co.technology/apps&#47;">Old application</a>',retired,'https://mklab.co.technology/'),true);
  for(const href of ['https://example.invalid/?next='+retired,'https://khanlab.co.technology.example.invalid/apps/','https://khanlab.co.technology/apps-other/','/apps/']){
    assert.equal(hasAnchorUnder(`<a href="${href}">Different destination</a>`,retired,'https://mklab.co.technology/'),false,href);
  }
});

test('generated guide bullets require an exact parsed destination',()=>{
  assert.equal(hasGuideLink('## Links\n- [Maintainer profile](https://mrkhan.co.technology/)\n','Maintainer profile',profile),true);
  assert.equal(hasGuideLink('- [Maintainer profile](https://MRKHAN.CO.TECHNOLOGY:443/)','Maintainer profile',profile),true);
  for(const line of [
    '- [Maintainer profile](https://example.invalid/https://mrkhan.co.technology/)',
    '- [Maintainer profile](https://mrkhan.co.technology.example.invalid/)',
    '- [Maintainer profile](https://viewer@mrkhan.co.technology/)',
    '- [Maintainer profile](https://mrkhan.co.technology/?next=example)',
    '- [https://mrkhan.co.technology/](https://example.invalid/)',
    'Text mentioning https://mrkhan.co.technology/',
  ])assert.equal(hasGuideLink(line,'Maintainer profile',profile),false,line);
});
