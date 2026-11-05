import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';

// HTML parsing is build/test tooling from the existing locked web workspace.
const require=createRequire(new URL('../apps/web/package.json',import.meta.url));
const {parse}=await import(pathToFileURL(require.resolve('parse5')).href);

function textContent(element){
  const parts=[],pending=[element];
  while(pending.length){
    const node=pending.pop();
    if(node.nodeName==='#text')parts.push(node.value);
    const children=node.childNodes||[];
    for(let index=children.length-1;index>=0;index--)pending.push(children[index]);
  }
  return parts.join('');
}

/** Read browser-parsed scripts and anchors; comments and inert template contents are not elements. */
export function parseHtmlDocument(html){
  const scripts=[],anchors=[],pending=[parse(html,{scriptingEnabled:true})];
  while(pending.length){
    const node=pending.pop();
    if(node.tagName==='script')scripts.push({src:node.attrs.find(attribute=>attribute.name==='src')?.value??null,body:textContent(node)});
    if(node.tagName==='a'){
      const href=node.attrs.find(attribute=>attribute.name==='href')?.value;
      if(href!==undefined)anchors.push({href,text:textContent(node)});
    }
    const children=node.childNodes||[];
    for(let index=children.length-1;index>=0;index--)pending.push(children[index]);
  }
  return {scripts,anchors};
}

function exactUrl(candidate,expected){
  try{
    const parsed=new URL(candidate);
    return parsed.username===''&&parsed.password===''&&parsed.href===expected.href;
  }catch{
    return false;
  }
}

/** Require an actual anchor with the complete normalized destination and optional label. */
export function hasExactAnchor(html,expectedUrl,text){
  const expected=new URL(expectedUrl);
  return parseHtmlDocument(html).anchors.some(anchor=>exactUrl(anchor.href,expected)&&(text===undefined||anchor.text.trim()===text));
}

/** Find links to a directory on one origin, including links beneath that directory. */
export function hasAnchorUnder(html,directoryUrl,baseUrl){
  const directory=new URL(directoryUrl);
  if(!directory.pathname.endsWith('/'))throw new TypeError('Link directory must end with a slash.');
  return parseHtmlDocument(html).anchors.some(anchor=>{
    try{
      const destination=new URL(anchor.href,baseUrl);
      return destination.origin===directory.origin&&destination.pathname.startsWith(directory.pathname);
    }catch{
      return false;
    }
  });
}

/** Validate the complete bullet-link form emitted by the generated plain-text guide. */
export function hasGuideLink(text,label,expectedUrl){
  const prefix='- ['+label+'](',expected=new URL(expectedUrl);
  return text.split(/\r?\n/).some(line=>{
    const bullet=line.trim();
    return bullet.startsWith(prefix)&&bullet.endsWith(')')&&exactUrl(bullet.slice(prefix.length,-1),expected);
  });
}
