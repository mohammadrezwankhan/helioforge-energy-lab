# Remaining roadmap implementation — 17 October 2026

User authorization: implement the remaining items in every view, identify real-data/credential/external-validation requirements, then merge, commit and publish. This supersedes the prior no-publication boundary. No claim of certification, field truth, signer identity or executed paid agents may be manufactured.

## Architecture and shared interfaces

Extend the existing study catalogue with executable advanced models. Retain original screens and their provenance. Advanced models are implemented software with explicit assumptions; calibration and validation are distinct evidence states. All new study modules follow `CONTRACT.md`, export `STUDIES` and `run(id, inputs)`, accept bounded strict schemas, return finite JSON and primary-source references. IDs are two lowercase tokens separated by one hyphen. Pages use actual navigation IDs: overview, hybrid, lessons, compare, storage, pv, research, markets, forecast, investment, pilots, council.

New independent write sets:

| Task | Files owned | Interface / pre-flight ruling |
|---|---|---|
| Physical models | engines/physical_studies.py; tests/test_physical_studies.py; docs/roadmap/PHYSICAL_MODELS.md | Existing study contract; parent owns registration, dependency installation and generation. No existing engine edits. |
| Planning/calibration models | engines/planning_studies.py; tests/test_planning_studies.py; docs/roadmap/PLANNING_MODELS.md | Same study contract; annual storage has explicit directions, full horizon and solver status. No shared numerical module writes. |
| Remaining interaction layer | web/src/completion-ui.ts, completion-ui.css; web/tests/completion-ui.test.mjs | Namespace HF controller refresh, existing app state. Parent owns app/tsconfig/build wiring. Data-dependent features must read actual result properties or report missing. |
| Connectors/evidence/council | Parent-owned new integrations modules/tests; main/council/schema and integration changes | Bounded local imports; allow-listed upstreams; configured credentials stay server side; no arbitrary URL fetching; external execution requires consent and explicit provider/model. |
| Integration/review/release | Parent-owned registration, browser tests, build config and documentation | Each feature mapped to source/proof or named external prerequisite. Fresh independent review; fix meaningful findings; signed commits, merge, push, Pages publication, live verification. |

Ruling: external validation cannot be replaced by test fixtures. Implement ingestion, fitting, backtesting, signed-evidence verification and actionable readiness gates; mark real-world calibration/certification pending when source evidence is absent. Cost if wrong: a visible unmet external prerequisite rather than false approval.

Ruling: keep the 17 specialized hybrid architectures study-only unless their specialized science is implemented and tested. Generalized carrier balances and explicit technical readiness records may support them without misrepresenting EMT/chemistry/network validation.

## Completion ledger

- [x] Advanced physical models and numerical tests.
- [x] Annual optimization, reliability ensembles, cointegration/calibration, multizone markets and contract/tax finance.
- [x] Remaining visual interactions, prerequisite gating, tariff drag/drop, dual scenes and accessibility controls.
- [x] Real-data imports, configured provider connectors, pilot ingestion, document extraction and authenticity evidence workflow.
- [x] Live external council cross-examination implementation and tested failure/cancellation/provenance behavior (provider execution remains credential-dependent).
- [x] Integrate all views and actual data/status displays, offline bundle and credential-free examples.
- [x] Independent review, numerical/browser/accessibility/performance tests and screenshot inspection.
- [x] Updated item-level completion/external-prerequisite ledger and release verification procedure.

Release execution (signed merge, push, deployment, live digest verification and signed receipt) is recorded separately by the public app manifest and delivery receipt, so this source document does not pretend to know its own future commit hash.

Prior release baseline: `8a43aa04d2c14aa45e0f7da1711428c931bed219`, 521 Python tests, 130 frontend tests, 74 browser checks. These counts are historical until rerun for this release.
