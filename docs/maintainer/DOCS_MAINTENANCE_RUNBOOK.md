# Documentation maintenance runbook

> Inspected source: [`fb42eb4d9b0c87e692710e8e867ab5190ea831a7`](https://github.com/mohammadrezwankhan/helioforge-energy-lab/tree/fb42eb4d9b0c87e692710e8e867ab5190ea831a7), 20 November 2026. This is a source and documentation snapshot, not a new test run, scientific certification, release or cloud publication.

Keep the existing [model registry](../MODEL_REGISTRY.md), [capabilities](../CAPABILITIES.md), [hybrid methodology](../HYBRID_METHODOLOGY.md), [roadmap evidence](../roadmap/COMPLETION.md), [quality report](../../QUALITY_REPORT.md) and [launcher](../../START_HERE.md) as their own canonical sources.

| When changed | Documentation and checks to update together |
| --- | --- |
| Hybrid equations, SOC order or outage rule | [Equations](../math-and-physics/EQUATIONS_AND_DERIVATIONS.md), [units](../math-and-physics/PARAMETERS_AND_SYMBOLS.md), methodological conservation tests |
| Storage MILP objective, price or terminal SOC | [Equation guide](../math-and-physics/EQUATIONS_AND_DERIVATIONS.md), solver/baseline tests and example |
| Study definition or delivery mode | [Capability contract](../CAPABILITIES.md), [model registry](../MODEL_REGISTRY.md), original generated public statements |
| Local API routes or consent gate | [Interfaces](../developer/API_CLI_AND_INTERFACES.md), [security](../../SECURITY.md), relevant endpoint tests |
| Dependency pin or Python/Node floor | [Toolchain](TOOLCHAIN_AND_DEPENDENCY_MATRIX.md), lockfiles, CI and launcher |
| Public output and CSP | [Cloudflare source](../CLOUDFLARE.md), complete build/check and true provider receipt |
| Recovery/release | [Evidence ledger](VERIFICATION_EVIDENCE_LEDGER.md), historical changelog, correct commit/artifact |

Never “update” a historical test count, audit, science validation or external review by inventing a new date. Record source, tool versions, exact command, output, omissions and runtime identity. Preserve private SQLite data and API keys outside Git.
