namespace HF {
  type ProvenanceRecord = Record<string, unknown> & {provenance?:ResultProvenance};

  const provenanceObject=(value:unknown):Record<string,unknown>|null=>
    value&&typeof value==='object'&&!Array.isArray(value)?value as Record<string,unknown>:null;

  const provenanceList=(value:unknown):unknown[]=>Array.isArray(value)?value:[];

  function provenanceLink(title:string,url:string):string {
    const href=safeURL(url);
    return href==='#'?escapeHTML(title):`<a href="${href}" target="_blank" rel="noopener noreferrer">${escapeHTML(title)}</a>`;
  }

  function provenanceSources(values:unknown[]):string {
    const links=values.flatMap(value=>{
      const source=provenanceObject(value);
      if(!source)return [];
      const title=String(source.title??source.name??'Source reference');
      const url=typeof source.url==='string'?source.url:'';
      const link=url?provenanceLink(title,url):escapeHTML(title);
      const scope=source.scope?` · ${escapeHTML(String(source.scope))}`:'';
      return [`<li>${link}${scope}</li>`];
    });
    return links.length?`<h4>Sources</h4><ul>${links.join('')}</ul>`:'';
  }

  function provenanceFields(label:string,fields:Record<string,unknown>):string {
    const entries=Object.entries(fields);
    if(!entries.length)return '';
    const values=entries.map(([key,value])=>{
      const rendered=typeof value==='string'?value:JSON.stringify(value)??String(value);
      return `<span><strong>${escapeHTML(key)}:</strong> ${escapeHTML(rendered)}</span>`;
    });
    return `<p><strong>${escapeHTML(label)}:</strong> ${values.join('; ')}</p>`;
  }

  /** Render provenance consistently for API records, hybrid results, study results and legacy examples. */
  export function resultProvenanceView(result:BaseResult|HybridResult|StudyResult):string {
    const record=result as unknown as ProvenanceRecord;
    const provenance=record.provenance;
    const digestPattern=/^[a-f0-9]{64}$/i;
    const sourceDigest=provenance?.source_revision;
    const sourceBound=provenance?.schema==='helioforge.result-provenance.v1'
      && provenance.status==='source_bound'
      && typeof sourceDigest==='string'&&digestPattern.test(sourceDigest);
    const modelName=sourceBound?String(provenance?.model.id??'unknown'):
      String(record.model??record.study??'unknown model');
    const modelVersion=sourceBound?String(provenance?.model.version??'unversioned'):
      String(record.model_version??'version unknown');
    const sourceStatus=sourceBound
      ?`Source-bound record · ${escapeHTML(sourceDigest!.toLowerCase())}`
      :'Legacy/unknown source provenance. No source revision or approval is inferred from a model label, run ID, or result hash.';
    const contract=sourceBound?provenance?.model_contract:null;
    const contractBlock=contract
      ?`<p>Model contract: ${provenanceLink(contract.title,contract.url)}. ${escapeHTML(contract.url_scope)}</p>`
      :'';
    const files=sourceBound&&provenance?.source_files.length
      ?`<p>Source files: ${provenance.source_files.map(escapeHTML).join(', ')}</p>`:'';
    const inputDigest=sourceBound?provenance?.input.sha256:null;
    const requestDigest=typeof record.input_sha256==='string'&&digestPattern.test(record.input_sha256)
      ?record.input_sha256:null;
    const inputBlock=inputDigest
      ?`<p>Effective model input SHA-256: ${escapeHTML(inputDigest)}${requestDigest&&requestDigest!==inputDigest
        ?`<br>Saved request SHA-256: ${escapeHTML(requestDigest)}`:''}</p>`
      :'';
    const datasetDigest=sourceBound?provenance?.data.dataset_revision:null;
    const dataBlock=sourceBound
      ?`<p>Data origin: ${escapeHTML(provenance?.data.kind??'unknown')}. Dataset revision: ${datasetDigest?escapeHTML(datasetDigest):'not declared'}.</p>`:'';
    const unitsBlock=sourceBound?provenanceFields('Units',provenance?.units??{}):'';
    const horizonBlock=sourceBound&&provenance?.horizon?provenanceFields('Horizon',provenance.horizon):'';
    const endpointsBlock=sourceBound?provenanceFields('Endpoints',provenance?.endpoints??{}):'';
    const approvalBlock=sourceBound
      ?`<p>Integrity scope: ${escapeHTML(provenance?.integrity.source_digest_scope??'not specified')}. Approval: ${escapeHTML(provenance?.integrity.approval_status??'not assessed')}; signature verified: ${provenance?.integrity.signature_verified===true?'yes':'no'}.</p>`
      :'';
    const equations=sourceBound?provenance?.equations??[]:provenanceList(record.equations).filter((value):value is string=>typeof value==='string');
    const equationBlock=equations.length?`<h4>Equations</h4><ul>${equations.map(e=>`<li>${escapeHTML(e)}</li>`).join('')}</ul>`:'';
    const rawSources=sourceBound?provenance?.sources??[]:provenanceList(record.sources);
    const sourceBlock=provenanceSources(rawSources);
    const limitations=sourceBound?provenance?.limitations??[]:provenanceList(record.warnings);
    const limitationBlock=limitations.length
      ?`<h4>Warnings and limitations</h4><ul>${limitations.map(value=>`<li>${escapeHTML(String(value))}</li>`).join('')}</ul>`:'';
    return `<details class="method-details"><summary>Model provenance & limits</summary><div><p>${sourceStatus}</p><p>Model: ${escapeHTML(modelName)} · version ${escapeHTML(modelVersion)}.</p>${contractBlock}${files}${inputBlock}${dataBlock}${unitsBlock}${horizonBlock}${endpointsBlock}${approvalBlock}${equationBlock}${sourceBlock}${limitationBlock}</div></details>`;
  }

  /** Attach complete result metadata to CSV rows without changing scientific row count or cells. */
  export function resultExportRows(result:unknown,rows:Record<string,unknown>[]):Record<string,unknown>[] {
    const record=provenanceObject(result)??{};
    const provenance=provenanceObject(record.provenance)??{};
    const input=provenanceObject(provenance.input)??{};
    const data=provenanceObject(provenance.data)??{};
    const model=provenanceObject(provenance.model)??{};
    const warnings=provenanceList(record.warnings);
    const resultJSON=JSON.stringify(result)??'null';
    const metadata:Record<string,unknown>={
      metadata_schema:'helioforge.result-export.v1',
      model_id:String(model.id??record.study??record.model??'legacy/unknown'),
      model_version:String(model.version??record.model_version??record.model??'legacy/unknown'),
      run_id:String(record.run_id??record.bundle_case_id??'legacy/unknown'),
      input_sha256:String(input.sha256??record.input_sha256??'legacy/unknown'),
      request_input_sha256:String(record.input_sha256??'legacy/unknown'),
      source_revision:String(provenance.source_revision??record.source_revision??'legacy/unknown'),
      dataset_revision:String(data.dataset_revision??record.dataset_revision??'legacy/unknown'),
    };
    const metadataJSON=JSON.stringify({...metadata,provenance:record.provenance??null,warnings});
    const firstRowPayload={metadata_json:metadataJSON,result_json:resultJSON,warnings_json:JSON.stringify(warnings)};
    const mergeWithoutLoss=(row:Record<string,unknown>,addition:Record<string,unknown>):Record<string,unknown>=>{
      const output={...row};
      for(const [key,value] of Object.entries(addition)){
        if(Object.prototype.hasOwnProperty.call(output,key)){
          let preserved=`original_${key}`;
          while(Object.prototype.hasOwnProperty.call(output,preserved)||Object.prototype.hasOwnProperty.call(addition,preserved))
            preserved=`original_${preserved}`;
          output[preserved]=output[key];
        }
        output[key]=value;
      }
      return output;
    };
    if(rows.length===0)return [mergeWithoutLoss({}, {...metadata,...firstRowPayload})];
    return rows.map((row,index)=>mergeWithoutLoss(row,{...metadata,...(index===0?firstRowPayload:{})}));
  }
}
