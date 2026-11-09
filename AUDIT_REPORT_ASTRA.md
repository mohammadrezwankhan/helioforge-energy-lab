# ASTRA — HelioForge source and responsive release audit

**Date:** 9 November 2026 · **Base SHA:** `92c9f44b69186ee92919f5e60ce14d25ce64beeb` · **Repository:** `mohammadrezwankhan/helioforge-energy-lab`

## Scope and evidence boundary

This source audit examined the main-branch file tree, publication generator, TypeScript workbench shell and responsive styles, model catalogue, current scripts and CI. The user-provided multi-agent phases are used as a work breakdown; this report does not claim independently executed external engineering agents. The live `https://mkgrid.co.technology/` website was not available for direct browser verification in this environment. Emulated-browser results come only from the generated artifact once GitHub CI executes, not from device hardware or a live release.

## Source findings and remediations

| Severity | Base location | Viewport | Root cause, observed source impact | Remediation in this branch |
|---|---|---|---|---|
| P2 | `scripts/build-domain.mjs:69` | Desktop, tablet, mobile | The capabilities list is followed immediately by a limitations list that repeats four identical sentences, wasting space and impairing scanability. | One ordered deduplicated list, with source-contract assertions that each shared claim appears exactly once. |
| P2 | `apps/web/index.html:21` | All, worse on slow mobile CPUs | Empty app root before JavaScript boot produces a blank initial interface. | Instant HTML loading shell, existing no-JavaScript notice preserved, adaptive three/two/one-column structure. |
| P2 | `scripts/build-domain.mjs:98-103` | All | The 59 detailed model contracts are preceded by a long workspace directory and have no interactive filtering. | Collapsible workspace index, search, workspace filter, 44px+ controls, visible count, clear action, no-results state. Unfiltered contents remain visible without JavaScript. |
| P2 | `scripts/cloudflare-site.css:3` | All | Fixed publication spacing makes dense pages unnecessarily tall; navigation risks awkward wraps on small screens. | Compact fluid spacing, wrapped nav, mobile content reflow, preserved links and scientific caveats. |
| P2 | `apps/web/src/terminal.css` | 360–600px | Default single-column Terminal input stack increases distance between inputs and results. | Two-column mobile input grouping, field shrink constraints and 44px minimum numeric touch-target heights. |
| P2 | `.github/workflows/ci.yml:98-115` | 390, 820, 1440px | Existing automated browser suites target app flows but do not enforce public static route responsiveness at all three requested viewport classes. | Add `scripts/browser-site-audit.py` to the hosted CI job and archive its JSON observations. |
| P3 | `scripts/build-domain.mjs:69` | Desktop and mobile | Priority-loaded screenshot did not explicitly allow asynchronous decoding. | Add `decoding="async"` while preserving its existing `fetchpriority="high"` and dimensions. |

## Route coverage and intended verification

| Route / feature | Evidence source | Automated candidate check |
|---|---|---|
| `/` | `scripts/build-domain.mjs` | Generated page, unique capabilities, reflow, page errors |
| `/run/#hybrid` | `apps/web/src/hybrid-*` | Existing hybrid tests plus hosted reflow |
| `/run/#compare` and Terminal | `apps/web/src/terminal-*` | Existing deterministic/terminal tests plus hosted reflow |
| `/models/` | `scripts/capability-contract.mjs`, `build-domain.mjs` | 59 contract cards, empty state, search, clear, workspace filtering, reflow |
| `/learning/` and three `/learning/*/` guides | Static source-linked guides | Response, visible content and reflow |
| `/help/`, `/methodology/`, `/about/` | Static publication generator | Response, visible content and reflow |
| `/app.json`, `/llms.txt`, `/downloads/HelioForge-Offline.html` | Existing release/export scripts | Existing `check-domain`, hosted-acceptance and integrity contracts |

The generated-site script tests **11 route states × 3 viewport classes** (1440×900, 820×1180, 390×844), checks HTML document scroll overflow, clipped controls and JavaScript errors, and interacts with registry filters. These checks cannot establish no possible regressions across every state and browser engine. Existing Playwright tests cover many app flows and engines separately.

## Scientific integrity retained

- 36 architectures (19 local Python electrical screens; 17 study-only), 24 scenarios, 36 lessons, 59 named study models across 12 workspaces.
- The browser Terminal is a deterministic bounded 24-hour **greedy** energy-balance screen, not an optimizer or an investment-grade annual case.
- Bundled example outputs are synthetic and precomputed. New advanced study calculations require the separate local Python API; optional external integrations remain explicitly opt-in.
- No numerical engines, financial assumptions, generated model fixtures, third-party assets, authentication or deployment secrets are changed in this branch.

## Verification and release gates

The baseline `main` Verify research release run [42641635068](https://github.com/mohammadrezwankhan/helioforge-energy-lab/actions/runs/42641635068) and Cloudflare export run [42641635124](https://github.com/mohammadrezwankhan/helioforge-energy-lab/actions/runs/42641635124) were reported successful for the **base commit** by GitHub. These historical checks do not establish candidate status.

Candidate checks should include Python pytest, lint, frontend `npm ci`, typecheck, build, node tests, `node scripts/check-domain.mjs`, existing workbench browser suites, and `python scripts/browser-site-audit.py --url http://127.0.0.1:4190 --report docs/site-audit/browser-site-ci.json`, as exercised in the PR workflow. Do not call the branch verified or publish-ready until those checks actually succeed. Deployment to the live Cloudflare domain additionally requires the separate deployment process and published artifact inspection. Full WCAG 2.2 AA, Core Web Vitals, all physical device classes, cross-browser equivalence, scientific validation, and live site state are not certified by this source audit.
