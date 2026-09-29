> Historical report supplied with the earlier release. For current v0.3.0 evidence, see [Champion verification](champion/VERIFICATION.md). Old counts and readiness claims are not the current release gate.

# HelioForge 0.2.0 — final build audit

**Audited:** 23 September 2026. **Release scope:** local-first hybrid-energy education and research. **Verdict:** deliverable as a tested research/learning release; not approved as a production multi-tenant service, engineering design tool, complete multi-carrier solver or accredited course.

This audit was performed through code inspection, internal numerical checks, API/frontend tests and browser interaction. It is not an external peer review, penetration test or proof that independent live AI reviewers executed. No stars, awards or adoption outcomes are claimed.

## 1. Delivered versus not delivered

| Area | Delivered | Explicit boundary |
|---|---|---|
| Hybrid catalogue | 36 original curated architecture entries, topology/control metadata and technology tags | Not every physically possible hybrid; asset declarations are not physics implementations. |
| Electrical screening | 19 runnable architecture presets and a bounded hourly energy-balance engine | Synthetic, greedy, AC-equivalent, single bus; not economic optimization or dynamic stability. |
| Advanced configurations | 17 study-only architectures with model/evidence requirements | Hydrogen, heat, V2G, marine, storage variants and networks need dedicated models before numerical results. |
| Scenarios | 24 presets: 20 numerical and four control/dynamic studies; applicability filtering | 285 combinations are numerically runnable, not all 864 catalogue pairs. |
| Lessons | 36 original short activities, objectives, experiment configuration, steps and explained self-checks | Self-study, not accreditation; two-question checks do not establish professional competence. |
| Visual interaction | Original 3D meshes, real camera transforms, asset inspector, semantic colors, keyboard controls and smooth/reduced motion | Canvas2D software 3D, not WebGL; objects not to scale; animated connections are conceptual. |
| Comparison/provenance | Three-run comparison, setup/CSV/lesson/progress exports, actual saved inputs and hashes | Session comparison state is not restored after reload; input hashes are not a tamper-evident audit chain. |
| Multi-agent integration | Eight specialist roles plus critic; deterministic local mode and gated OpenAI SDK path | No external model was called in this delivery; no invented “Ultra” model ID or pretend agent execution. |
| Open-source readiness | README, screenshots, CI, issue templates, methodology, coverage matrix, licence, launch plan and goal prompt | Publication, Pages deployment, community validation and live CI have not happened. |

## 2. Observed verification

**404 Python tests passed; 65 frontend tests passed; 32 browser checks passed.** Python statement coverage is **98.49%**. All 285 applicable numerical combinations and 100 seeded parameter perturbations pass conservation, state and direction invariants. A hand-calculable grid-only case checks the arithmetic independently of scenario selection.

Browser checks covered real baseline/outage runs, exact saved input values, JSON round-trip/rejection, CSV output, dirty-result handling, time scrubbing, two-run comparison, the selected saved hybrid review, study-only gating, quiz grading, duplicate-progress prevention, progress/reset/export, offline behavior and narrow layouts. All twelve workspaces fit 390px and 320px after corrections. A packaged wheel included the canonical JSON and successfully imported and simulated from a temporary extracted package location.

See [VALIDATION.md](VALIDATION.md), [release-validation.json](release-validation.json), [hybrid-browser-validation.json](hybrid-browser-validation.json) and [package-validation.txt](package-validation.txt). The browser transport was a real-API host bridge, not direct browser HTTP.

## 3. Issues found and fixed during the build

| Finding | Correction and evidence |
|---|---|
| Unsupported carrier/control cases could be mistaken for implemented solvers | Added explicit screening/study declarations, backend rejection, disabled run controls, evidence requirements and 21 rejection tests for 17 architectures/four study scenarios. |
| An hourly island screen could be misread as stability proof | Added reference/topology gating, GFL island rejection, de-energization behavior, outage critical-load accounting and prominent dynamic-study exclusions. |
| Old numerical results could appear under edited assumptions | Result/input snapshots are separate; dirty output is hidden until a successful current run. Invalid input produces an error state. |
| A pending request could be relabelled by configuration changes | Freeze input controls during the request; guard reset/import/lesson setup; store the submitted snapshot with the returned result. |
| Export could ignore a not-yet-committed form edit | Setup export collects and validates the current form before writing JSON. |
| A review could silently use a default hybrid case | Added an explicit saved `hybrid_run_id`; API validates the model kind and attaches actual inputs/hash/result summary. Missing/wrong-kind evidence is rejected. |
| A global market selector implied hybrid tariff coupling | Hide it in hybrid, lesson and comparison views; hybrid tariffs remain explicit inputs. |
| Intrinsic canvas/select sizes and review forms overflowed 320px | Constrained grid children and form/select sizing rather than hiding page overflow; both mobile widths now pass. |
| Broad `data/` ignore rule risked omitting the canonical catalogue from Git | Root runtime data ignore is now `/data/`; packaged JSON remains source. Docker source-data inclusion is explicit. |
| Generic lesson success could imply credentials | Self-check language, local progress, explicit reset confirmation, duplicate prevention and no accreditation claims. |
| Public demo retained private professional-history metadata | Replaced it with neutral, excluded-context metadata and removed it from front-page/project prompts. No private project archive is bundled into the new repo. |
| Stale inherited test/role/version documentation | Updated role counts, release version, logs, source scope, package checks and validation boundaries. |

## 4. Remaining limitations and prioritized recommendations

### P0 — before an unrestricted public API deployment

**Do not expose the local API as-is.** It has no production identity, tenant isolation or comprehensive authorization on saved runs and pilot edits. A single per-process AI gate is not distributed rate limiting. Add an explicit host/origin/CSRF threat model, authentication, authorization, tenancy, request rate/compute limits, provider budgets, secret management, TLS, retention and backup/restore tests. Obtain an independent security review. Existing origin checks, request limits, SQL parameterization and credential gating do not substitute for these controls.

A static, no-backend preview has a different threat model and is the intended public demo path. The included Pages workflow is manual and was not executed. A production API is not needed to publish the read-only preview.

### P0 — before claiming independent numerical validation

Add three independently reproduced hybrid benchmarks, preferably with licensed measured resource/load inputs. Review critical-demand prioritization, initial/terminal energy accounting, outages and generator behavior with an independent energy specialist. Internal conservation tests can pass for an internally consistent but incomplete policy.

### P1 — before broad usability claims

Run direct-browser HTTP/CSP and ordinary file-launch tests outside the restriction bridge. Test cross-reload localStorage, clean Windows/macOS/Linux setup, Safari/Firefox, keyboard-only workflows, screen readers, zoom and contrast. Measure frame timing/CPU use on a low-end device; do not claim a frame-rate or performance score from the visual design. Conduct five consenting educator/practitioner task reviews. The documented 320px/390px checks are not a full accessibility certification.

### P1 — highest-value next modeling work

Add licensed timestamped CSV inputs with units/timezone/missing-data checks. Add an explicit cyclic/target terminal-energy option and constrained hybrid optimization, keeping the transparent greedy policy as a teaching comparison. Model demand charges and multiple services jointly before making revenue-stacking claims. Link only reconciled annual dispatch to finance; do not annualize the demonstration day.

Implement **one** advanced hydrogen chain fully before adding more numerical technology labels: electricity and hydrogen mass balances, efficiency basis, startup/minimum-load/ramp constraints, storage bounds, terminal states and independent tests. Until then, hydrogen entries stay study-only. Thermal, water, mobility and network models deserve similarly explicit contracts.

### P1 — before claiming live multi-agent compatibility

With explicit authorization and a small provider budget, run the actual eight-specialist-plus-critic workflow using a model permitted in the owner's API project. Record real model/SDK, usage, latency, structured-output behavior, failures and cancellation. The current fake-SDK tests verify orchestration behavior, not live model compatibility or the quality of scientific judgments. The build audit did not run autonomous external agents.

### P2 — maintainability and useful community growth

Refactor dense namespace/template source into documented components or ES modules through a reviewed architecture decision, without introducing a second controller. Add restoreable comparison records, schema migrations, catalogue localization and educator-reviewed progression. Add independent benchmark issues, a short walkthrough, two technical case studies and newcomer contribution guidance. Track real use and returning contributors after publication.

A 5,000-star target is plausible only as an ambition to test through sustained usefulness and outreach; no analysis here estimates its probability. See [OPEN_SOURCE_LAUNCH.md](OPEN_SOURCE_LAUNCH.md). Do not manufacture stars, awards, users or endorsements.

## 5. Three next measurable goals

1. **Reproducibility:** five independent clean installations, three independent numerical benchmarks and direct-browser security/behavior checks, with no unclassified failures.
2. **Learning and interaction:** five consenting target-user reviews; fix every blocking keyboard/zoom/motion issue; document observed task outcomes and measured low-end performance.
3. **Model depth:** ship one validated advanced carrier chain plus licensed time-series input and explicit terminal-energy policies before increasing the catalogue count.

These are recommended acceptance targets, not completed milestones. The reusable [next-release multi-agent goal prompt](../prompts/ASTRA_MULTIAGENT_BETTERMENT.md) turns them into bounded implementation tasks and a critic's final evidence gate.
