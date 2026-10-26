namespace HF {
  export interface TerminalManifest {
    schema: 'helioforge.terminal.v1';
    generatedAt: string;
    stateSha256: string;
    payload: {
      solver: {algorithm: string; dtHours: number; steps: number; iterations: null};
      run: TerminalRun;
    };
  }
  export function terminalCanonical(value: unknown): string {
    if(value===null)return 'null';
    if(typeof value==='number'){
      if(!Number.isFinite(value))throw new Error('Manifest numbers must be finite.');
      return JSON.stringify(value);
    }
    if(typeof value==='string'||typeof value==='boolean')return JSON.stringify(value);
    if(Array.isArray(value))return '['+value.map(terminalCanonical).join(',')+']';
    if(typeof value==='object')return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+terminalCanonical((value as Record<string,unknown>)[k])).join(',')+'}';
    throw new Error('Unsupported manifest value.');
  }
  async function terminalDigest(value:unknown):Promise<string>{
    if(!globalThis.crypto?.subtle)throw new Error('SHA-256 requires HTTPS or a localhost browser.');
    return [...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(terminalCanonical(value))))].map(b=>b.toString(16).padStart(2,'0')).join('');
  }
  export async function terminalCreateManifest(run:TerminalRun):Promise<TerminalManifest>{
    const payload:TerminalManifest['payload']={solver:{algorithm:'greedy-hourly-energy-balance',dtHours:1,steps:24,iterations:null},run:structuredClone(run)};
    return {schema:'helioforge.terminal.v1',generatedAt:new Date().toISOString(),stateSha256:await terminalDigest(payload),payload};
  }
  export async function terminalReadManifest(value:unknown):Promise<TerminalRun>{
    if(!value||typeof value!=='object')throw new Error('Expected a Terminal run manifest.');
    const m=value as TerminalManifest;
    if(m.schema!=='helioforge.terminal.v1'||typeof m.stateSha256!=='string'||!/^[a-f0-9]{64}$/.test(m.stateSha256)||!m.payload?.run)throw new Error('Unknown or incomplete Terminal manifest.');
    if(await terminalDigest(m.payload)!==m.stateSha256)throw new Error('Manifest hash does not match its inputs, solver and output series.');
    const solved=terminalSolve(terminalValidateInputs(m.payload.run.inputs));
    // A digest is integrity evidence, not authenticity. Rerun instead of trusting imported outputs.
    const fresh=await terminalCreateManifest(solved);
    if(fresh.stateSha256!==m.stateSha256)throw new Error('Manifest model or output series differs from the reproducible current model.');
    return solved;
  }
  export function terminalEncodeState(inputs:TerminalInputs):string{return encodeURIComponent(terminalCanonical(terminalValidateInputs(inputs)));}
  export function terminalDecodeState(state:string):TerminalInputs{
    if(state.length>12000)throw new Error('Query state is too large.');
    return terminalValidateInputs(JSON.parse(decodeURIComponent(state)) as unknown);
  }
  export function terminalManifestCSV(m:TerminalManifest):string{
    const run=m.payload.run;
    const meta:Record<string,unknown>={schema:m.schema,generatedAt:m.generatedAt,stateSha256:m.stateSha256,model:run.modelVersion,dataKind:run.dataKind,status:run.status,flags:JSON.stringify(run.flags),warnings:JSON.stringify(run.warnings),...m.payload.solver,...run.inputs,...run.metrics};
    return toCSV(m.payload.run.rows.map(row=>({...meta,...row})));
  }
  export function terminalManifestMarkdown(m:TerminalManifest):string{
    const r=m.payload.run;
    return ['# HelioForge Terminal run',`Generated: ${m.generatedAt}`,`SHA-256: ${m.stateSha256}`,`Model: ${r.modelVersion}`,
      'Synthetic 24-hour greedy energy adequacy screen. No optimization, thermal dynamics or annualization.',
      '## Governing recurrence',
      'grid import + PV + discharge + unserved = load + charge + export + curtailment',
      'SOC[t+1] = SOC[t] + sqrt(roundtripEfficiency) * charge - discharge / sqrt(roundtripEfficiency)',
      'Time step: 1 hour. Steps: 24. Solver iterations: not applicable (direct recurrence).',
      'Initial and terminal SOC may differ; compare both endpoints and demand service before comparing cost.',
      '## Inputs','```json',JSON.stringify(r.inputs,null,2),'```',
      '## Metrics','```json',JSON.stringify(r.metrics,null,2),'```',
      '## Full hourly series (CSV)','```csv',toCSV(r.rows as unknown as Record<string,unknown>[]),'```',
      '## Flags and limits',...r.flags.map(f=>'- '+(typeof f==='string'?f:JSON.stringify(f))),...r.warnings.map(w=>'- '+w),
      '## Complete integrity payload','```json',terminalCanonical(m.payload),'```'].join('\n\n');
  }
}
