# Follow-up findings and corrections

These findings arose during this repair pass and are distinct from the appraisal's F01–F14 IDs. No P0 finding was inferred from missing evidence.

| Finding | Correction | Proof |
|---|---|---|
| Offline v1 migration could discard a saved-run pointer before its result was hydrated. | Preserve the pointer when the stored configuration and in-memory pointer still match; edits clear it and record a loss. | `workspace-migration.test.mjs`, independent review, workspace browser report. |
| Migration refreshed `saved_at` without listing that change. | The migration receipt now discloses timestamp refresh. | Migration tests and independent source re-review. |
| Default storage provenance described submitted empty vectors as the effective solver input. | Materialize the existing synthetic profile, hash effective model inputs and dataset identity, and retain the separate Store request digest. | API/dashboard storage provenance regressions and independent source re-review. |
| Flattened hybrid CSV metadata confused model ID with model version; empty generic CSV exports omitted the full original result. | Keep model ID/version separate and include full result JSON in the first or metadata-only row while retaining colliding observation keys. | `result-provenance.test.mjs`. |
| A later stylesheet hid the new tablet navigation toggle. | Place the tablet drawer rule after the overriding stylesheet rules. | Real browser drawer checks at 820, 1024, 1100 and 1101 CSS pixels; responsive suite. |
| HTML string substitution interpreted dollar tokens inside minified JavaScript and emitted a broken script reference. | Share callback-based literal insertion between standalone and hosted editions; escape closing script strings. | `inline-html.test.mjs`, startup checks, exact built HTML with no missing external script. The broken candidate D remains a failed attempt. |
| Added council integration controls escaped the initial frozen-preview disabling step. | Apply the read-only gate after integration refresh and after lazy-example hydration. | All 63 public council fixture-label checks; zero API/provider calls and invariant frozen exports. |
| Platform-default line endings could vary compiled release bytes. | Pin TypeScript output and generated text to LF; normalize text inputs before assembling release HTML. | Frozen-data replay and repeated build identity checks. This does not retrospectively prove the historical remote CI/deployment chain. |
| CI's full lint gate found two unsorted import blocks. | Sort the imports without changing numerical or UI behavior, then regenerate source-bound study provenance and repeat affected acceptance on candidate G. | `ruff-verified.log`, regenerated study contracts and final browser reports. Candidate F evidence is retained. |

Retained harness errors include the initial duplicated `/run/run/` Terminal URL, initial API startup/origin configuration failures, an unsupported API-runner screenshot flag, missing expected study-provenance metadata in export comparisons, isolated-test compilation dependencies and a cross-VM array assertion. Each is distinguished from product failures in the logs; none was converted to a passing product observation.

The final candidate G presentation run recorded 156 passes and one Firefox focus timeout (PAIR-002, 360px, constrained network, keyboard, valid saved state). Its case took 177 seconds while independent shell commands also stalled. A single retry on the unchanged artifact passed in 6.1 seconds with no overflow or page errors. The original report and retry remain separate; the timeout's root cause is not established and no timeout was increased.

The initial parsing-trace analysis matched broad event names, which included `ParseHTML`. The final analysis uses explicit V8 parse events, reports HTML parsing separately, links the renderer thread to the target frame, and unions nested intervals. Raw traces are retained. These instrumented diagnostics are separate from the untraced load benchmark.
