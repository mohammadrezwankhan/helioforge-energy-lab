namespace HF { // eslint-disable-line @typescript-eslint/no-namespace, @typescript-eslint/no-unused-vars -- HF is the ordered global-script bundle namespace; modules change its shared runtime contract.
  export interface ProvenanceSource { title?: string; name?: string; url?: string; scope?: string; status?: string }
  export interface ResultProvenance {
    schema: string; status: string; model: {id:string;version:string|null}; source_revision: string; source_files: string[];
    input: {sha256:string;scope:string;canonicalization:string};
    data: {kind:string;identity:Record<string,unknown>|null;dataset_revision:string|null;dataset_revision_scope?:string|null};
    units: Record<string,string>; horizon: Record<string,unknown>|null; endpoints: Record<string,unknown>;
    model_contract: {title:string;url:string;implementation_files:string[];url_scope:string};
    equations: string[]; sources: ProvenanceSource[]; limitations: string[];
    integrity: {source_hash_algorithm:string;input_hash_algorithm:string;source_digest_scope:string;
      signature_verified:boolean;human_approval_recorded:boolean;approval_status:string};
  }
}
