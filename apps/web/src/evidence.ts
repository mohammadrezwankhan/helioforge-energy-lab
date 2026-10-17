namespace HF {
  export interface EvidenceEnvelope {format:'helioforge-evidence-v1';payload:unknown;sha256:string;signatures:{algorithm:'ECDSA-P256-SHA256';public_key:JsonWebKey;signature:string;identity:string}[]}
  export function canonicalEvidence(value:unknown):string {
    if(typeof value==='number'&&!Number.isFinite(value))throw Error('Evidence numbers must be finite.');
    if(Array.isArray(value))return '['+value.map(canonicalEvidence).join(',')+']';
    if(value!==null&&typeof value==='object')return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+canonicalEvidence((value as Record<string,unknown>)[k])).join(',')+'}';
    const json=JSON.stringify(value);if(json===undefined)throw Error('Evidence must contain JSON values.');return json;
  }
  const to64=(bytes:ArrayBuffer):string=>btoa(String.fromCharCode(...new Uint8Array(bytes)));
  const from64=(value:string):Uint8Array<ArrayBuffer>=>Uint8Array.from(atob(value),c=>c.charCodeAt(0));
  async function digestEvidence(bytes:Uint8Array<ArrayBuffer>):Promise<string>{return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');}
  export async function signEvidence(payload:unknown):Promise<EvidenceEnvelope> {
    if(!crypto?.subtle)throw Error('Signing requires a secure browser context (HTTPS or localhost).');
    const data=new TextEncoder().encode(canonicalEvidence(payload));
    const pair=await crypto.subtle.generateKey({name:'ECDSA',namedCurve:'P-256'},false,['sign','verify']);
    const signature=await crypto.subtle.sign({name:'ECDSA',hash:'SHA-256'},pair.privateKey,data);
    return {format:'helioforge-evidence-v1',payload,sha256:await digestEvidence(data),signatures:[{algorithm:'ECDSA-P256-SHA256',public_key:await crypto.subtle.exportKey('jwk',pair.publicKey),signature:to64(signature),identity:'Ephemeral local browser key; person and authority unverified'}]};
  }
  export async function verifyEvidence(envelope:EvidenceEnvelope):Promise<{valid:boolean;signers:number}> {
    if(envelope.format!=='helioforge-evidence-v1'||!Array.isArray(envelope.signatures)||envelope.signatures.length<1||envelope.signatures.length>20)return {valid:false,signers:0};
    const data=new TextEncoder().encode(canonicalEvidence(envelope.payload));
    if(await digestEvidence(data)!==envelope.sha256)return {valid:false,signers:0};
    const keys=new Set<string>();
    try{for(const s of envelope.signatures){if(s.algorithm!=='ECDSA-P256-SHA256')return {valid:false,signers:0};const id=String(s.public_key.x)+':'+String(s.public_key.y);if(keys.has(id))return {valid:false,signers:0};keys.add(id);const key=await crypto.subtle.importKey('jwk',s.public_key,{name:'ECDSA',namedCurve:'P-256'},false,['verify']);if(!await crypto.subtle.verify({name:'ECDSA',hash:'SHA-256'},key,from64(s.signature),data))return {valid:false,signers:0};}}catch{return {valid:false,signers:0};}
    return {valid:true,signers:keys.size};
  }
}
