# Experimental study contract

The roadmap adds separately named experimental studies without changing the capability declarations of the existing hybrid engine. All numerical calculations execute in tested Python. Public static pages show Python-generated example outputs; new calculations require the local API. No new runtime JavaScript dependencies.

## Python modules

Each module exports `STUDIES: list[dict]` and `run(study_id: str, inputs: dict) -> dict`. IDs are globally unique kebab-case strings. Each entry has:

```text
id, page, title, summary, kind (visual theme),
fields: [{name, label, default, min, max, step, unit}],
data_fields: [{name, label, default}],
equations: [string], limitations: [string], sources: [{title, url}]
```

`fields` are bounded numeric parameters; `data_fields` are JSON arrays or objects edited/uploaded explicitly. Each study uses a strict Pydantic model (extra=forbid, finite numbers, bounded array sizes and magnitudes, validate defaults), rejecting invalid combinations. Defaults must be present in the catalogue and accepted by the model. Numeric fields requiring integers reject fractions. `run` must not mutate inputs or use global random state. Use a seeded NumPy generator for random experiments.

Result schema:

```text
metrics: [{label, value: number|string|null, unit: string}],
series: [{name, x_label, y_unit, x: number[]|string[], y: (number|null)[]}],
table: [{column_name: primitive value}],
details: object (optional: full raw paths, schedules, evidence etc),
warnings: [string]
```

Series arrays have matching lengths; no NaN/Infinity; all results serialize with `json.dumps(..., allow_nan=False)`. The registry adds study, model_version, inputs, data_kind, equations, limitations, sources, and a deterministic SHA-256 evidence hash. A hash is not a signature or proof of factual truth. No external calls, regulatory assertions, operational permissions, paid providers, scientific validation or credential claims.

## Mathematical honesty

Every simplified physical proxy names its assumptions. Do not label deterministic outage shortfall as statistical LOLE; use an explicitly sampled ensemble for that. Synthetic inertia uses a documented reduced-order swing model and is not an EMT simulator. SSR proxies are not grid-code compliance. Battery loss factors are not fitted electrochemical predictions. Negative CFADS cannot be concealed by zero debt service. Debt sculpting must reconcile debt balances and disclose infeasibility/negative amortization. Annual dispatch requires an explicitly generated full-year scenario or supplied 8760-hour inputs with stated billing assumptions; never repeat/annualize the existing demonstration day.

## Evidence

Write meaningful pytest tests in the module's assigned test file: independent hand cases, invariants, null/zero boundaries, rejection of unknown/nonfinite/extreme inputs, deterministic seed where relevant. Test every default study and JSON finiteness. Scientific sources must be primary references and may justify equations, not claim a calibrated model or legal effective status. Report unimplemented or data-dependent requirements explicitly.
