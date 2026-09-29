# Separating a numerical model from its explanation

HelioForge connects a browsable energy-learning interface to an optional local Python calculation API. The standalone preview preserves a reproducible starting point; new numerical runs use the backend and its explicit scenario assumptions.

## Trace the implementation

Start with `apps/api/helioforge/`. The input side is **scenario assumptions**; the rule boundary is **local python calculations**; the displayed result is **research and learning views**. Keep these three concerns distinct when changing a screen or fixture. Follow [the source map](../../PROJECT_ANALYSIS.md) for the remaining modules.

The following are actual test names in the supplied source, selected as starting points for review rather than a coverage claim:

- [`apps/api/tests/test_hybrid.py`](../../apps/api/tests/test_hybrid.py) checks scenario applicability, configuration validation, energy balance, state-of-charge bounds and API provenance. Its `invariant` helper checks each simulated schedule row.
- [`apps/web/tests/hybrid.test.mjs`](../../apps/web/tests/hybrid.test.mjs) exercises configuration round trips, rejects unknown/nonfinite fields, and checks catalogue/scenario behavior against the built browser code.

Trace one hybrid configuration from `apps/web/src/` into the API's `HybridRequest`, then through `apps/api/helioforge/engines/hybrid.py::simulate_hybrid`. Compare the returned schedule with the explicit balance and storage assertions. These are synthetic numerical checks; no field-validation claim follows from them.

## A useful first investigation

Run the README demo with fictional inputs. Choose one displayed record or calculation and locate its source. Trace the rule that decides the visible state, then follow any local save or export. Record the actual value before and after a single input change. If the interface cannot explain that transition, submit a small reproduction linked to the responsible rule.

Use [QUALITY_REPORT.md](../../QUALITY_REPORT.md) for executed checks and limits. A green unit suite, a responsive initial screen and a validated domain service are different kinds of evidence; only the first two are within this repository-factory evaluation.

## Try the local workflow

```sh
git clone https://github.com/mohammadrezwankhan/helioforge-energy-lab.git
cd helioforge-energy-lab
node scripts/preview-demo.mjs
```

Draft for technical publication. Verify the cited release checks before posting. [Repository](https://github.com/mohammadrezwankhan/helioforge-energy-lab).
