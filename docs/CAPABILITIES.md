# Capability contract

Contract version: `1.0.0` · Content revision: 2026-10-29.

This is the shared product-copy and evidence contract used by the generated public overview, About, Methodology, Help and app facts. Application version, catalogue identity, data identity and model versions are recorded separately in [the model registry](MODEL_REGISTRY.md).

## Delivery modes

| Mode | Capability | New calculations |
|---|---|---:|
| Bundled synthetic examples | Bundled synthetic examples are precomputed outputs; the public browser edition does not calculate new study-model results from edited inputs. | No |
| Bounded browser Terminal | The Terminal runs new deterministic, bounded 24-hour energy-balance cases in the browser; it uses a greedy policy and is not an optimizer. | Yes |
| Advanced local Python | The separate local Python application runs new calculations for the advanced study models and optimization. | Yes |
| Opt-in local external providers | Optional local external providers are separate, opt-in integrations; credentials and explicit consent are required where applicable. The public static preview makes no provider calls. | Provider-specific |

## Task-led starts

- **Explore a bundled example.** Open the public preview and inspect a labeled synthetic result. [Open](/run/#hybrid).
- **Calculate a bounded Terminal case.** Open Scenario compare and use the Parametric energy workbench. [Open](/run/#compare).
- **Set up advanced local calculations.** Use the source setup guide to run the Python application on your machine. [Open](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/main/START_HERE.md).

## Public copy (shared verbatim)

> Bundled synthetic examples are precomputed outputs; the public browser edition does not calculate new study-model results from edited inputs.
> The Terminal runs new deterministic, bounded 24-hour energy-balance cases in the browser; it uses a greedy policy and is not an optimizer.
> The separate local Python application runs new calculations for the advanced study models and optimization.
> Optional local external providers are separate, opt-in integrations; credentials and explicit consent are required where applicable. The public static preview makes no provider calls.

The external-provider description is a scope boundary, not a claim that any paid, live or device provider was exercised. External integrations remain provider-specific and consent-gated.

## Scope

The current source inventory has **12 workspaces** and **59 study IDs**. The Terminal is a separate browser energy-balance model. The 59 study models use the local Python API for new calculations; the public preview carries their generated sample outputs.

This implementation does not establish publication, deployment state, calibration, independent scientific validation, professional approval, or production readiness.
