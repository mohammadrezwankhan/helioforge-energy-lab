# HelioForge documentation map

This guide describes the code at `fb42eb4d9b0c87e692710e8e867ab5190ea831a7`, reviewed on **2026-11-19**. HelioForge is a synthetic energy and investment teaching workbench with several distinct calculation engines. Choose an engine before interpreting a result: a daily browser recurrence, a constrained storage MILP, a hybrid energy screen and a research study answer different questions.

| Your task | Start here | Continue with |
|---|---|---|
| Run the packaged app or build it | [Setup and reproducibility](developer/SETUP_AND_REPRODUCIBILITY.md) | [Troubleshooting](developer/TROUBLESHOOTING.md) |
| Understand which engine produced a number | [Architecture](developer/ARCHITECTURE.md) | [Equations](math-and-physics/EQUATIONS_AND_DERIVATIONS.md), [limits](math-and-physics/ASSUMPTIONS_AND_LIMITS.md) |
| Use the API, Terminal or imports | [Interfaces](developer/API_CLI_AND_INTERFACES.md) | [Worked labs](developer/WORKED_EXAMPLES_AND_LABS.md) |
| Investigate any of the 59 studies | [Study model atlas](math-and-physics/STUDY_MODEL_ATLAS.md) | [Parameters and symbols](math-and-physics/PARAMETERS_AND_SYMBOLS.md) |
| Assess evidence and change risk | [Verification ledger](maintainer/VERIFICATION_EVIDENCE_LEDGER.md) | [Known debt](maintainer/FAILURE_MODES_AND_TECH_DEBT.md), [toolchains](maintainer/TOOLCHAIN_AND_DEPENDENCY_MATRIX.md) |
| Review, release or recover | [CI and release](maintainer/CI_CD_AND_RELEASE_PLAYBOOK.md) | [Documentation maintenance](maintainer/DOCS_MAINTENANCE_RUNBOOK.md), [recovery](owner/BUS_FACTOR_RECOVERY_RUNBOOK.md) |
| Own the next year of work | [Roadmap](../ROADMAP.md) | [Governance](owner/GOVERNANCE_AND_SCOPE.md), [decisions](owner/ADR/ADR-0000-INDEX.md), [portfolio context](owner/PORTFOLIO_INTEGRATION.md) |

The [reference handbook](reference/index.html) presents these canonical files through the existing documentation site. [The teaching companion](index.html) remains a separate interactive illustration. Its fixed battery power contribution is not an energy-storage dispatch model. The full application starts from the packaged preview or local launcher; see [the original README](../README.md).

Established methodology remains useful: [METHODOLOGY](METHODOLOGY.md), [HYBRID_METHODOLOGY](HYBRID_METHODOLOGY.md), [HYBRID_COVERAGE](HYBRID_COVERAGE.md), [VALIDATION](VALIDATION.md), [LESSON_AUTHORING](LESSON_AUTHORING.md). Historical [START_HERE](../START_HERE.md) and [architecture notes](ARCHITECTURE.md) retain their original text with a dated scope notice. The current source adds browser Terminal calculations and guarded workspace imports beyond those earlier descriptions.

## Project policies and history

Use the preserved [contribution guide](../CONTRIBUTING.md), [changelog](../CHANGELOG.md), [citation metadata](../CITATION.cff) and [security policy](../SECURITY.md) for their canonical project contracts. The [primary-source register](SOURCES.md) is historical: its earlier no-live-feed wording predates the current optional connector implementations. Current connector capabilities and their unexecuted external boundaries are described in [interfaces](developer/API_CLI_AND_INTERFACES.md); a source link or configured credential is not evidence of a successful live request.

## Evidence vocabulary

**Implemented** means a source path exists. **Executed locally** means a dated command completed on this pinned source. **Source CI** identifies historical GitHub checks on that source commit. **Candidate QA**, **candidate CI**, **merge**, and **live publication** are separate identities and gates. A source digest, successful test, local signature or polished chart does not establish calibration, provider access, professional approval or real-world accuracy. See the [ledger](maintainer/VERIFICATION_EVIDENCE_LEDGER.md).

The source inventory accounts for all 927 tree entries, including 819 file payloads. Static parsing covers 141 Python files, 131 JavaScript/TypeScript files and 14 HTML files; the export inventory is deliberately conservative and includes internal helpers. Generated bundles, images, videos and historical receipts are identified without claiming their contents received the same semantic review as the numerical engines. Complete machine-readable coverage accompanies the review handoff rather than the published application.
