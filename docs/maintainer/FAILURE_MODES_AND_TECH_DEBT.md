# Verification risks and technical-debt boundaries

> Inspected source: [`fb42eb4d9b0c87e692710e8e867ab5190ea831a7`](https://github.com/mohammadrezwankhan/helioforge-energy-lab/tree/fb42eb4d9b0c87e692710e8e867ab5190ea831a7), 20 November 2026. This is a source and documentation snapshot, not a new test run, scientific certification, release or cloud publication.

These rows identify risks and acceptance work rather than claiming a newly observed failure.

| ID | Risk / known limitation | Source-backed next evidence |
| --- | --- | --- |
| HF-01 | Bundled examples can be misread as new numerical runs | [Capabilities](../CAPABILITIES.md): preserve labels and prohibit edited-study “run” claims without Python |
| HF-02 | Hybrid SOC depletion can inflate service estimates | [hybrid](../../apps/api/helioforge/engines/hybrid.py): show both energy endpoints and model limits |
| HF-03 | Greedy adequacy and optimised dispatch may be conflated | [storage](../../apps/api/helioforge/engines/storage.py): compare different goals and constraints explicitly |
| HF-04 | GFM/island labels can be mistaken for fault/black-start qualification | [Methodology](../HYBRID_METHODOLOGY.md): require external power-system/HIL/site evidence |
| HF-05 | Local SQLite research history is not tamper-evident | [Security](../../SECURITY.md): back up/restore and review retention |
| HF-06 | Optional connector/device access needs real consent, licensing and secrets | [Connector prerequisites](../roadmap/CONNECTORS.md) |
| HF-07 | Public site CSP/artifact could drift from the checked source | [Cloudflare](../CLOUDFLARE.md): exact hashes, origins and provider receipt |
| HF-08 | Dated historical CI may be mistaken for current head verification | [Quality report](../../QUALITY_REPORT.md): observe fresh original required checks |
| HF-09 | UI accessibility audits may leave manual review gaps | [Quality report](../../QUALITY_REPORT.md): preserve incomplete axe/manual items |

No new test execution, technical closure or changed scientific acceptance is asserted.
