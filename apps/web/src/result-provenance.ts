namespace HF { // eslint-disable-line @typescript-eslint/no-namespace, @typescript-eslint/no-unused-vars -- HF is the ordered global-script bundle namespace; modules change its shared runtime contract.
  const provenanceObject = (value: unknown): Record<string, unknown> | null =>
    value && typeof value === 'object' && !Array.isArray(value)
      ? (value as Record<string, unknown>)
      : null;

  const provenanceVerified = (value: unknown): boolean => value === true;

  const provenanceList = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);

  function provenanceLink(title: string, url: string): string {
    const href = safeURL(url);
    return href === '#'
      ? escapeHTML(title)
      : `<a href="${href}" target="_blank" rel="noopener noreferrer">${escapeHTML(title)}</a>`;
  }

  function provenanceSources(values: unknown[]): string {
    const links = values.flatMap((value) => {
      const source = provenanceObject(value);
      if (!source) return [];
      const title = displayText(source.title ?? source.name ?? 'Source reference');
      const url = typeof source.url === 'string' ? source.url : '';
      const link = url ? provenanceLink(title, url) : escapeHTML(title);
      const scope = source.scope ? ` · ${escapeHTML(displayText(source.scope))}` : '';
      return [`<li>${link}${scope}</li>`];
    });
    return links.length ? `<h4>Sources</h4><ul>${links.join('')}</ul>` : '';
  }

  function provenanceFields(label: string, fields: Record<string, unknown>): string {
    const entries = Object.entries(fields);
    if (!entries.length) return '';
    const values = entries.map(([key, value]) => {
      const encoded: unknown = JSON.stringify(value);
      const rendered = typeof value === 'string' ? value : typeof encoded === 'string' ? encoded : displayText(value);
      return `<span><strong>${escapeHTML(key)}:</strong> ${escapeHTML(rendered)}</span>`;
    });
    return `<p><strong>${escapeHTML(label)}:</strong> ${values.join('; ')}</p>`;
  }

  /** Render provenance consistently for API records, hybrid results, study results and legacy examples. */
  export function resultProvenanceView(result: unknown): string {
    const record = provenanceObject(result) ?? {};
    const provenance = provenanceObject(record.provenance);
    const digestPattern = /^[a-f0-9]{64}$/i;
    const sourceDigest = typeof provenance?.source_revision === 'string' ? provenance.source_revision : '';
    const bound = provenance?.schema === 'helioforge.result-provenance.v1' &&
      provenance.status === 'source_bound' && digestPattern.test(sourceDigest) ? provenance : null;
    const model = provenanceObject(bound?.model) ?? {};
    const input = provenanceObject(bound?.input) ?? {};
    const data = provenanceObject(bound?.data) ?? {};
    const integrity = provenanceObject(bound?.integrity) ?? {};
    const modelName = bound ? displayText(model.id ?? 'unknown') : displayText(record.model ?? record.study ?? 'unknown model');
    const modelVersion = bound ? displayText(model.version ?? 'unversioned') : displayText(record.model_version ?? 'version unknown');
    const sourceStatus = bound
      ? `Source-bound record · ${escapeHTML(sourceDigest.toLowerCase())}`
      : 'Legacy/unknown source provenance. No source revision or approval is inferred from a model label, run ID, or result hash.';
    const contract = provenanceObject(bound?.model_contract);
    const contractBlock = contract
      ? `<p>Model contract: ${provenanceLink(displayText(contract.title), typeof contract.url === 'string' ? contract.url : '')}. ${escapeHTML(contract.url_scope)}</p>`
      : '';
    const sourceFiles = provenanceList(bound?.source_files);
    const files = sourceFiles.length ? `<p>Source files: ${sourceFiles.map(escapeHTML).join(', ')}</p>` : '';
    const inputDigest = typeof input.sha256 === 'string' ? input.sha256 : null;
    const requestDigest = typeof record.input_sha256 === 'string' && digestPattern.test(record.input_sha256) ? record.input_sha256 : null;
    const inputBlock = inputDigest
      ? `<p>Effective model input SHA-256: ${escapeHTML(inputDigest)}${requestDigest && requestDigest !== inputDigest ? `<br>Saved request SHA-256: ${escapeHTML(requestDigest)}` : ''}</p>`
      : '';
    const datasetDigest = typeof data.dataset_revision === 'string' ? data.dataset_revision : null;
    const dataBlock = bound ? `<p>Data origin: ${escapeHTML(data.kind ?? 'unknown')}. Dataset revision: ${datasetDigest ? escapeHTML(datasetDigest) : 'not declared'}.</p>` : '';
    const unitsBlock = bound ? provenanceFields('Units', provenanceObject(bound.units) ?? {}) : '';
    const horizon = provenanceObject(bound?.horizon);
    const horizonBlock = horizon ? provenanceFields('Horizon', horizon) : '';
    const endpointsBlock = bound ? provenanceFields('Endpoints', provenanceObject(bound.endpoints) ?? {}) : '';
    const approvalBlock = bound
      ? `<p>Integrity scope: ${escapeHTML(integrity.source_digest_scope ?? 'not specified')}. Approval: ${escapeHTML(integrity.approval_status ?? 'not assessed')}; signature verified: ${provenanceVerified(integrity.signature_verified) ? 'yes' : 'no'}.</p>`
      : '';
    const equations = provenanceList(bound ? bound.equations : record.equations).filter((value): value is string => typeof value === 'string');
    const equationBlock = equations.length ? `<h4>Equations</h4><ul>${equations.map((e) => `<li>${escapeHTML(e)}</li>`).join('')}</ul>` : '';
    const sourceBlock = provenanceSources(provenanceList(bound ? bound.sources : record.sources));
    const limitations = provenanceList(bound ? bound.limitations : record.warnings);
    const limitationBlock = limitations.length
      ? `<h4>Warnings and limitations</h4><ul>${limitations.map((value) => `<li>${escapeHTML(displayText(value))}</li>`).join('')}</ul>`
      : '';
    return `<details class="method-details"><summary>Model provenance & limits</summary><div><p>${sourceStatus}</p><p>Model: ${escapeHTML(modelName)} · version ${escapeHTML(modelVersion)}.</p>${contractBlock}${files}${inputBlock}${dataBlock}${unitsBlock}${horizonBlock}${endpointsBlock}${approvalBlock}${equationBlock}${sourceBlock}${limitationBlock}</div></details>`;
  }

  /** Attach complete result metadata to CSV rows without changing scientific row count or cells. */
  export function resultExportRows(
    result: unknown,
    rows: Record<string, unknown>[],
  ): Record<string, unknown>[] {
    const record = provenanceObject(result) ?? {};
    const provenance = provenanceObject(record.provenance) ?? {};
    const input = provenanceObject(provenance.input) ?? {};
    const data = provenanceObject(provenance.data) ?? {};
    const model = provenanceObject(provenance.model) ?? {};
    const warnings = provenanceList(record.warnings);
    const encoded: unknown = JSON.stringify(result);
    const resultJSON = typeof encoded === 'string' ? encoded : 'null';
    const metadata: Record<string, unknown> = {
      metadata_schema: 'helioforge.result-export.v1',
      model_id: displayText(model.id ?? record.study ?? record.model ?? 'legacy/unknown'),
      model_version: displayText(
        model.version ?? record.model_version ?? record.model ?? 'legacy/unknown',
      ),
      run_id: displayText(record.run_id ?? record.bundle_case_id ?? 'legacy/unknown'),
      input_sha256: displayText(input.sha256 ?? record.input_sha256 ?? 'legacy/unknown'),
      request_input_sha256: displayText(record.input_sha256 ?? 'legacy/unknown'),
      source_revision: displayText(
        provenance.source_revision ?? record.source_revision ?? 'legacy/unknown',
      ),
      dataset_revision: displayText(
        data.dataset_revision ?? record.dataset_revision ?? 'legacy/unknown',
      ),
    };
    const metadataJSON = JSON.stringify({
      ...metadata,
      provenance: record.provenance ?? null,
      warnings,
    });
    const firstRowPayload = {
      metadata_json: metadataJSON,
      result_json: resultJSON,
      warnings_json: JSON.stringify(warnings),
    };
    const mergeWithoutLoss = (
      row: Record<string, unknown>,
      addition: Record<string, unknown>,
    ): Record<string, unknown> => {
      const output = { ...row };
      for (const [key, value] of Object.entries(addition)) {
        if (Object.prototype.hasOwnProperty.call(output, key)) {
          let preserved = `original_${key}`;
          while (
            Object.prototype.hasOwnProperty.call(output, preserved) ||
            Object.prototype.hasOwnProperty.call(addition, preserved)
          )
            preserved = `original_${preserved}`;
          output[preserved] = output[key];
        }
        output[key] = value;
      }
      return output;
    };
    if (rows.length === 0) return [mergeWithoutLoss({}, { ...metadata, ...firstRowPayload })];
    return rows.map((row, index) =>
      mergeWithoutLoss(row, { ...metadata, ...(index === 0 ? firstRowPayload : {}) }),
    );
  }
}
