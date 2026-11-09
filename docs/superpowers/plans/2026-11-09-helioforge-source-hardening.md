# HelioForge source hardening implementation plan — 2026-11-09

**Goal:** Source-truthful, compact, accessible responsive static documentation and workbench; no numerical-engine changes. Preserve dark workbench/light public-site identity, zero added runtime dependencies, original license and security boundaries.

## Implementation sequence
1. **Static capability deduplication** — In `scripts/build-domain.mjs`, build one ordered, deduplicated list from the four shared mode statements and unique limitations. Assert the result in `scripts/check-domain.mjs` to prevent regression.
2. **Pre-boot experience** — In `apps/web/index.html`, provide a visible HTML shell replacing the empty app root. Implement responsive three/two/one-pane loading geometry in `apps/web/src/terminal.css`. Existing `HF.boot()` must replace it on first render and preserve no-JS explanatory text.
3. **Model registry navigation** — Render searchable attributes for the 59 source-linked cards; collapsible workspace index, search and workspace filter controls in `build-domain.mjs`; publish `scripts/model-registry-filter.js` at `/models/filter.js`. The full registry must be visible without JavaScript.
4. **Viewport density** — Tighten page gaps and nav wrapping in `scripts/cloudflare-site.css`; create a 2-column phone Terminal input form with 44px control targets while retaining units and input validation.
5. **Regression gate** — Execute existing backend/frontend/hosted validation; add `scripts/browser-site-audit.py` to hosted Chromium CI and archive a JSON report for 9 static and 2 workbench route states at 390/820/1440 widths. Fail on overflow, offscreen controls, console errors, or nonfunctional search.
6. **Source and release reporting** — Record evidence and limits in `AUDIT_REPORT_ASTRA.md` and `QUALITY_REPORT.md`; create a PR; merge only when required GitHub checks and protection allow it.

## Honest delivery
The baseline Actions runs cannot substitute for new PR checks. No unobserved before/after scores, live deployment, independent agents, hardware testing, security certification or scientific validation should be asserted.
