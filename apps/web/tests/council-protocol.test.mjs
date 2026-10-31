import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const box = vm.createContext({URL, Intl, structuredClone});
vm.runInContext(fs.readFileSync(new URL('../dist/app.js', import.meta.url), 'utf8'), box);
const hf = box.HF;

function councilState(mode='local') {
  const data = structuredClone(hf.SNAPSHOT);
  data.council.mode = mode;
  data.council.protocol_metadata = {
    id: 'helioforge-council/v1', mode,
    external_execution_status: mode === 'local' ? 'not_requested' : 'completed',
    consent_to_external_processing: mode === 'openai',
    limits: {workflow_timeout_seconds: mode === 'local' ? null : 300,
      expected_runner_invocations: mode === 'local' ? 0 : 17,
      completed_runner_invocations: mode === 'local' ? 0 : 17,
      runner_invocation_semantics: 'Runner.run counts do not establish provider requests, token use, or cost.'},
    cost: {potentially_billable: mode === 'openai'},
    cancellation: {status: mode === 'local' ? 'not_applicable' : 'not_triggered', provider_stop_confirmed: null},
    integrity: {reviewer_identity_verified: false, evidence_authenticity_verified: false,
      signature_verified: false, critic_signoff: false, human_approval_recorded: false,
      task_id: null, task_id_semantics: null}
  };
  const hybrid = hf.initialHybridState();
  return {page:'council', hybrid, connected:false, busy:false, data, marketFilter:'ALL', search:'',
    chartMode:'dispatch', forecastYears:20, runs:[], motionOff:true};
}

test('local council describes checklist sections instead of claiming agents ran', () => {
  const html = hf.content(councilState());
  assert.match(html, /No LLM or independent agent is executed in local mode/);
  assert.match(html, /Checklist section/);
  assert.match(html, /Deterministic summary/);
  assert.match(html, /No critic invocation/);
  assert.doesNotMatch(html, /Eight specialists challenge the evidence/);
  assert.doesNotMatch(html, /Specialist review/);
});

test('completed external council exposes protocol and unverified authority fields', () => {
  const html = hf.content(councilState('openai'));
  assert.match(html, /helioforge-council\/v1/);
  assert.match(html, /External status:<\/strong> completed/);
  assert.match(html, /17 completed \/ 17 planned/);
  assert.match(html, /signature, critic signoff and human approval are not verified or recorded/);
});
