namespace HF {
  export interface StudyField { name:string;label:string;default:number;min:number;max:number;step:number;unit?:string }
  export interface StudyDefinition { id:string;page:string;title:string;summary:string;kind?:string;fields:StudyField[];data_fields?:{name:string;label:string;default:unknown}[];equations:string[];limitations:string[];sources:{title:string;url:string}[] }
  export interface StudyResult { study:string;model_version:string;inputs:Record<string,unknown>;data_kind:string;metrics:{label:string;value:number|string|null;unit:string}[];series:{name:string;x_label:string;y_unit:string;x:(string|number)[];y:(number|null)[]}[];table:Record<string,unknown>[];details?:Record<string,unknown>;warnings:string[];equations:string[];limitations:string[];sources:{title:string;url:string}[];evidence_sha256:string;input_sha256?:string;source_revision?:string;dataset_revision?:string|null;provenance?:ResultProvenance }
  export interface StudyBundle {catalogue:StudyDefinition[];results:Record<string,StudyResult>}
  export interface StudyDraft {id:string;values:Record<string,string>;result:StudyResult;dirty:boolean;busy:boolean;error:string;slice:number;selectedSeries:number}
}
