namespace HF { // eslint-disable-line @typescript-eslint/no-namespace, @typescript-eslint/no-unused-vars -- HF is the ordered global-script bundle namespace; modules change its shared runtime contract.
  export interface EvidenceEnvelope {format:'helioforge-evidence-v1';payload:unknown;sha256:string;signatures:{algorithm:'ECDSA-P256-SHA256';public_key:JsonWebKey;signature:string;identity:string}[]}
  export function canonicalEvidence(value:unknown):string {
    if(typeof value==='number'&&!Number.isFinite(value))throw Error('Evidence numbers must be finite.');
    if(Array.isArray(value))return '['+value.map(canonicalEvidence).join(',')+']';
    if(value!==null&&typeof value==='object')return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+canonicalEvidence((value as Record<string,unknown>)[k])).join(',')+'}';
    const json:unknown=JSON.stringify(value);if(typeof json!=='string')throw Error('Evidence must contain JSON values.');return json;
  }
  const to64=(bytes:ArrayBuffer):string=>btoa(String.fromCharCode(...new Uint8Array(bytes)));
  const from64=(value:string):Uint8Array<ArrayBuffer>=>Uint8Array.from(atob(value),c=>c.charCodeAt(0));
  async function digestEvidence(bytes:Uint8Array<ArrayBuffer>):Promise<string>{return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');}
  export async function signEvidence(payload:unknown):Promise<EvidenceEnvelope> {
    const localCrypto=browserCrypto();
    if(!localCrypto?.subtle)throw Error('Signing requires a secure browser context (HTTPS or localhost).');
    const data=new TextEncoder().encode(canonicalEvidence(payload));
    const pair=await crypto.subtle.generateKey({name:'ECDSA',namedCurve:'P-256'},false,['sign','verify']);
    const signature=await crypto.subtle.sign({name:'ECDSA',hash:'SHA-256'},pair.privateKey,data);
    return {format:'helioforge-evidence-v1',payload,sha256:await digestEvidence(data),signatures:[{algorithm:'ECDSA-P256-SHA256',public_key:await crypto.subtle.exportKey('jwk',pair.publicKey),signature:to64(signature),identity:'Ephemeral local browser key; person and authority unverified'}]};
  }
  export async function verifyEvidence(envelope:unknown):Promise<{valid:boolean;signers:number}> {
    const value=recordValue(envelope), invalid={valid:false,signers:0};
    if(!value||value.format!=='helioforge-evidence-v1'||typeof value.sha256!=='string'||!Array.isArray(value.signatures)||value.signatures.length<1||value.signatures.length>20)return invalid;
    const signatures:unknown[]=value.signatures,keys=new Set<string>();
    try {
      const data=new TextEncoder().encode(canonicalEvidence(value.payload));
      if(await digestEvidence(data)!==value.sha256)return invalid;
      for(const raw of signatures){
        const signature=recordValue(raw),publicKey=recordValue(signature?.public_key);
        if(!signature||signature.algorithm!=='ECDSA-P256-SHA256'||typeof signature.signature!=='string'||!publicKey||publicKey.kty!=='EC'||publicKey.crv!=='P-256'||typeof publicKey.x!=='string'||typeof publicKey.y!=='string'||'d' in publicKey)return invalid;
        const jwk:JsonWebKey={kty:publicKey.kty,crv:publicKey.crv,x:publicKey.x,y:publicKey.y};
        if('ext' in publicKey){if(typeof publicKey.ext!=='boolean')return invalid;jwk.ext=publicKey.ext;}
        if('key_ops' in publicKey){
          if(!Array.isArray(publicKey.key_ops))return invalid;
          const operations:unknown[]=publicKey.key_ops;
          if(!operations.every((operation):operation is string=>typeof operation==='string'))return invalid;
          jwk.key_ops=operations;
        }
        for(const field of ['alg','use'] as const){if(field in publicKey){const fieldValue=publicKey[field];if(typeof fieldValue!=='string')return invalid;jwk[field]=fieldValue;}}
        const id=publicKey.x+':'+publicKey.y;
        if(keys.has(id))return invalid;
        keys.add(id);
        const key=await crypto.subtle.importKey('jwk',jwk,{name:'ECDSA',namedCurve:'P-256'},false,['verify']);
        if(!await crypto.subtle.verify({name:'ECDSA',hash:'SHA-256'},key,from64(signature.signature),data))return invalid;
      }
    }catch{return invalid;}
    return {valid:true,signers:keys.size};
  }
}
