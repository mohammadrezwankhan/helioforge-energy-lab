# Full responsive and release audit — 27 October 2026

Production target: <https://mkgrid.co.technology/run/>. Source base:
`7a5560303f77c8e6118c2dfce0b3c03e5de6c5a2`. Integration branch:
`fix/full-responsive-audit-20261027`. The earlier live publication identified
`c1c67652e0b27c807ddfbcaaa9f987d37ca0f992`, runtime SHA-256
`fa69fa49e6d97ca75713334aefffd31ead1ec0861e5a39f2aee98bf5c1527d71`.

This report describes the tested candidate. The PR checks and deployment receipt
identify the eventual merge and production deployment; a local pass alone is not
a publication claim. See [machine-readable verification](full-audit/verification.json).

## Scope and execution

The orchestrator integrated fixes and performed final proof. Actual isolated
subagents performed responsive implementation (`worker`, GPT-6 Luna), functional
QA (`explorer`, GPT-6 Luna), security/scientific review (`explorer`, GPT-6 Luna),
and independent source review (`deep-read`, GPT-6 Luna). They did not inherit chat
history. QA/review roles were read-only. Four agents ran concurrently at most;
the requested specialist workstreams were grouped within that limit.

All twelve workspaces were inspected: hybrid, lessons, compare, overview,
storage, PV, research, markets, forecast, investment, pilots and council.
The distinction between the local Python models and the separate browser
Terminal model is preserved. No numerical engines or catalogue contracts changed.

## Findings and repairs

Twelve reproducible findings: **0 P0, 3 P1, 9 P2, 0 P3**. All twelve are repaired.
The rows below describe expected behavior, the observed failure, its cause,
implementation and regression evidence. Repeated failures at multiple widths
are counted as one defect per root cause, not as separate bugs.

| ID / severity | Reproduction and expected versus actual behavior | Root cause and change | Verified evidence |
|---|---|---|---|
| HF-AUD-001 / P1 | `/run/#hybrid`, Chromium at 390, 700 and 820px: title and the three count labels should remain readable; the title broke mid-word and counts overlapped. | Desktop hero columns left insufficient label width. Stack the hero below 1120px, use two count columns on phones, reclaim unused stat padding. | Before/after images below; actual label-width checks in `browser-full-audit.py`. |
| HF-AUD-002 / P1 | All twelve routes at 320–768px: document and body should fit. At 320px the body was 402px wide although root clipping concealed overflow. | Non-wrapping section badges competed with headings. Wrap badges and stack headings. No new global overflow suppression was added. | Baseline 101 body-reflow failures; final three-engine checks assert both body and root width and critical control bounds. |
| HF-AUD-003 / P2 | Research forms and Market Intelligence at 820px, PV/Investment headings at 1024px: readable columns/actions; baseline metadata and headings overflowed by up to 45px in WebKit. | Fixed column/heading composition remained too dense. Stack compact research/experience panels below 900px and wrap market metadata. | All route/width and orientation checks; existing research and study workflows retained. |
| HF-AUD-004 / P2 | At 390px focus Solar PV, then press Escape with navigation closed: focus should remain in the field; it moved to the menu toggle. | Global Escape always called the menu-close function. Close only an actually open navigation drawer. | Reproduced before; actual keyboard regression passes in Chromium, Firefox and WebKit. |
| HF-AUD-005 / P2 | In WebKit open command palette or tariff comparison and Tab/Shift+Tab: focus should remain in the dialog and return to its opener on close. Native focus moved to BODY; tariff close did not return to the clicked trigger. | Reliance on differing native focus behavior. Wrap only dialog boundary focus and restore the tariff trigger explicitly. | Every forward/reverse Tab is checked for both dialogs, followed by Escape and focus restoration, in all three engines. |
| HF-AUD-006 / P2 | Reduce motion or scroll the hybrid diagram out of view: idle scenes should stop scheduling frames; baseline retained a permanent RAF callback. | Unconditional rescheduling. Suspend on reduced motion, offscreen or hidden document; resume once and remove listeners on disposal. | Lifecycle tests failed before and pass after; interactions/telemetry still redraw on demand. |
| HF-AUD-007 / P2 | Render the hybrid scene: theme reads should be bounded per frame; baseline made 256 computed-style reads per draw. | Each face resolved its theme separately. Reuse one current computed-style object per draw, including its font. | Measured unit harness: 256 → 1 style lookup per draw; scene/render tests pass. |
| HF-AUD-008 / P2 | Open standalone preview/network log: self-contained UI should not fetch fonts; baseline requested Google Fonts CSS and a font binary. | Three remote font tags contradicted offline/privacy claims. Remove them and use the existing installed monospace fallback stack. | Before network observations; direct asset-tag regression; final browser network evidence. No fonts were downloaded into the repository. |
| HF-AUD-009 / P1 | Install `apps/api[dev]`, then `python launch.py --check`: a documented clean install should launch; preflight rejected five current pinned dependencies. | A duplicate stale version list in the launcher. Read all eight runtime pins from the canonical pyproject file. | Two new launcher contract tests failed before and pass after; actual installed-environment preflight passes. |
| HF-AUD-010 / P2 | Build dedicated Pages export: release security should be reproducible; global CSP existed only in Cloudflare control-plane state and the checker expected none. | Generate exact inline-script hashes from all four HTML routes into `_headers`; check the generated policy and document host-rule transition/rollback. | Old export fails the new CSP assertion; rebuilt export passes; two policy unit tests pass. Live effective headers remain a separate publication gate. |
| HF-AUD-011 / P2 | Read current README: hosted capability should agree with `/methodology/`, `app.json` and runtime; it said all new calculations required Python and retained an old study count. | Stale overview copy. Describe the bounded browser Terminal separately from advanced Python studies and use the current 59-study count. | Cross-check against executable study catalogue and public metadata; unchanged 19/17 boundary. |
| HF-AUD-012 / P2 | Read earlier Terminal verification: exact artifact identity should be clear; it named a base revision differing from live `app.json`. | Clarify historical recorded base versus verified published identity; current verification is separate and the release manifest accepts actual current counts. | Passive runtime SHA matched the earlier live manifest; new release hashes cover current sources/assets/report. |

## Visual evidence

| Device | Before | After |
|---|---|---|
| Mobile, 390px | [Before](full-audit/before-390.png) | [After](full-audit/after-390.png) |
| Tablet, 820px | [Before](full-audit/before-820.png) | [After](full-audit/after-820.png) |
| Desktop, 1440px | [Before](full-audit/before-1440.png) | [After](full-audit/after-1440.png) |

Full-page before/after captures cover every workspace at mobile, tablet and
desktop sizes in the local audit evidence directory. The reviewer inspected
actual screenshots, not only process exit codes. Intentional table and pilot-lane
horizontal scrolling remains local; core functionality was not removed on phones.
Default browser safe-area behavior is retained; `viewport-fit=cover` was rejected
during review because the existing header does not consume inset variables.

## Verification

Environment: Windows, Node 24.22.1, Python 3.12.14, TypeScript 7.0.2,
Playwright 1.64.1, axe-core 4.14.0, Ruff 0.17.3. Exact browser versions and counts
are recorded in the verification JSON. npm audit found zero vulnerabilities.
pip-audit initially found advisory records only in the audit environment's bundled
pip 25.0.1; upgrading that isolated environment to 26.2.2 yielded zero known
vulnerabilities. Runtime dependency pins did not change.

| Gate | Result |
|---|---|
| Baseline Python / frontend | 653 / 186 passed |
| Final Python / frontend | 655 / 190 passed; zero failed or skipped; one upstream TestClient deprecation warning retained |
| Build helpers | 6 passed (engineering media and CSP) |
| Existing API browser journeys | Smoke 18, hybrid 14, Champion 18, roadmap 24, completion 10 passed |
| Terminal standalone suite | 251 passed, 0 failed; 24 axe scans, 0 violations or execution errors |
| Full matrix | 12 views × 13 widths × 3 engines, plus keyboard, zoom-equivalent, label and accessibility assertions; see current verification JSON |
| Extra responsive worker samples | 228 Chromium view/orientation cases passed, plus all 12 at 640×450 |
| Architecture / lesson coverage | All 36 architecture gates and all 36 tier-ordered self-checks passed in an independent Chromium audit |
| Scientific preservation | All 285 bundled cases regenerate exactly; 16 original model/contract files unchanged; 19 runnable / 17 study-only architectures preserved |
| Static / dependencies | Ruff, typecheck, build, preview agreement, domain checks, npm and Python dependency audit passed |
| Secret-pattern review | No high-confidence token/private-key pattern found in added lines across 65 reachable commits; this is a bounded scan, not a proof of absence |
| Independent review | Source findings addressed; no remaining source blocker reported |

Representative commands (run from the repository root):

```sh
python -m ruff check apps/api
python -m pytest apps/api/tests -o addopts='' -q
npm --prefix apps/web ci --ignore-scripts
npm --prefix apps/web run typecheck
npm --prefix apps/web run build
npm --prefix apps/web test
python launch.py --check
python scripts/check-hybrid-assets.py
python scripts/check-terminal-preservation.py
python scripts/browser-smoke.py --screenshots
python scripts/browser-hybrid.py --screenshots
python scripts/browser-champion.py --screenshots
python scripts/browser-roadmap.py
python scripts/browser-completion.py --url http://127.0.0.1:8000
python scripts/browser-accessibility.py --url http://127.0.0.1:8000
node scripts/build-domain.mjs
node scripts/check-domain.mjs
node scripts/check-preview.mjs
node --test scripts/domain-security.test.mjs scripts/engineering-hero.test.mjs
python scripts/browser-terminal.py --report path/to/terminal.json
python scripts/browser-full-audit.py --url http://127.0.0.1:4182/run/ --report path/to/audit.json
python scripts/generate-release-manifest.py --verification docs/full-audit/verification.json
python scripts/verify-release.py
```

The CI browser job now installs Chromium, Firefox and WebKit and runs the full
matrix. Remote CI must succeed on the integrated PR before merge/publication.
The first CI run caught an unstaged launcher fix and a CodeQL finding in the new
CSP extractor's closing-tag handling. The launcher source is now included, and
a failing-then-passing regression covers whitespace, mixed case, ignored end-tag
attributes and script-like text. This extractor processes generated HTML only;
it is not an HTML sanitizer. Neither failed candidate was merged or deployed.

## Performance and limits

Baseline public Chromium lab sample: 1,512,966 transferred bytes, LCP 1,248ms,
CLS 0.0223. Baseline local uncompressed HTML was approximately 13.60MB; LCP
880–960ms, CLS 0.0223. These were unthrottled loopback/public desktop samples,
1440×1000 with reduced motion, not field Core Web Vitals or a slow-mobile claim.
Current comparable local measurements and bytes are in the verification JSON.
Removing the webfont removes its requests and font-swap dependency; canvas
callbacks/theme lookups are separately measured improvements. The full offline
dataset remains bundled rather than replacing scientific results for a score.

Unavailable/unverified: physical phones/tablets, iOS Safari itself (WebKit engine
was tested), assistive-technology speech output, OS/native 200% text settings,
real network/CPU-constrained mobile field data, field INP, paid provider execution,
real hardware connectors, Docker and independent scientific calibration.
640px and 320px widths model 200%/400% layout reflow from a 1280px viewport; they
are not native browser zoom tests. Automated axe scans include manual-review
items and do not certify WCAG conformance. No external AI was enabled.

## Release contract

Publish only the complete `.cloudflare/site` export to the existing
`mkgrid-helioforge` Pages project, after required PR CI and source review pass.
Preserve the engineering-film policy and media. Confirm merge SHA on `main`,
deployment success, the live manifest/runtime digest, effective CSP and a fresh
browser smoke test. The independent GitHub Pages dashboard is not this release.
The final deployment receipt records the actual outcome and rollback identity.
