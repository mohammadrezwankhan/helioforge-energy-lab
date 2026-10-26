# MKGrid Terminal forensic audit and remediation

Baseline source: `d14b71f50ef400a50d3ccd4792dcd59238c64f56` (authenticated GitHub API and later a clean Git clone). Live runtime SHA-256: `a47e919e2a631226ce663726f91352ca5dd749c95b9163c1773e37bc48ab5cb4`. The immutable source archive and live document differ by production canonical/indexing injection. Detailed source locations, stable identifiers and hashes are in `docs/terminal-audit/inventory.json`.

## Preserved surface

| Views | Original features retained |
|---|---|
| hybrid | 36 architectures; 24 scenarios; configuration import/export; all numeric fields; asset inspector; pointer/keyboard scene camera; exact bundled results; timeline; hybrid exports |
| lessons | 36 linked lessons; selection; experiment load; quiz grading; mastery; progress storage/import/export/reset |
| compare | Original three-run comparison, exact parameter identities and exports; new reduced-model analysis is a separate region |
| overview | Portfolio filters; dispatch/price charts; methodology; existing evidence actions |
| storage | Original Python optimizer inputs/results; time scrubber; charge/discharge and SOC displays; CSV exports |
| pv | Original PV assumptions, lifetime results and study selection |
| research | Original residual, Weibull, sustainability and research studies |
| markets | Country/source evidence; tariff and regulatory workflows |
| forecast | Seeded model parameters; quantiles; studies and missing values |
| investment | Project-finance and acquisition models; null DSCR and IRR distinctions |
| pilots | Fictional pilot board; workflow updates and register export |
| council | Eight roles and critic; deterministic versus external-mode distinction; explicit consent/provider boundary |

The audit records 30 API routes, 49 DOM event hooks, 67 markup data attributes, 128 selector data attributes, 59 studies, 296 declared study inputs, and 84 study data fields. The hybrid boundary remains 19 numerical / 17 study-only architectures. No original research-engine arithmetic or API request contract is replaced.

## Findings

Line references below describe the immutable baseline; subsequent formatting can move lines. Reproduce visual findings by opening the stated view at 1440px or 320px and inspecting its computed style/source.

| ID / Page or component | Issue | Root cause and baseline location | Fix applied | Verification |
|---|---|---|---|---|
| T01 / every view | Generic display/body face and very small metadata | `apps/web/src/styles.css:2-3`, Inter/system face; 8-11px labels in legacy sheets | Martian Mono token system; readable text floors | Source lint and browser review |
| T02 / every view | Literal colors and unrelated accent hues | `styles.css:3-14`, `champion.css`, chart/scene source literals | One green lightness ramp; named root tokens; Canvas resolves the same tokens | Token scan; chart/browser tests |
| T03 / panels and controls | Rounded cards, shadows, nested panel treatment | `styles.css:4-14`, `champion.css:37` | Square hairline architecture; row and region treatment; asymmetric work areas | Source lint; viewport checks |
| T04 / headings | Emphasis fragments in otherwise upright headings | `styles.css:5,14`, `champion.css:37` | Uniform roman headings | Source gate 38 checks |
| T05 / shell and status | Decorative status dots and tracked uppercase metadata | `views.ts:131-133`, `champion-views.ts:6` and legacy CSS | Real textual statuses; sentence-case metadata; decorative beacons suppressed | Source and rendered checks |
| T06 / narrow screens | Intrinsic sizing risk in dense tables, actions, charts and selects | Legacy route-specific grid and tiny controls | Internal table scrollers; minmax tracks; no wrapping controls; capped shell | Eight-width browser matrix |
| T07 / browser capability | Hosted preview cannot compute changed research-model inputs | `app.ts:91,102`, `cloudflare.json` | Original API boundary preserved; a separately labelled tested daily browser recurrence added | Numerical parity and browser tests |
| T08 / comparison depth | Original comparison has no configurable sweep or normalized local ranking | `hybrid-views.ts` compare view | Bounded 1D/2D sweep; conditional sampled Pareto frontier; local finite differences | New TS/Python tests |
| T09 / reproducibility | No hashed full reduced-model output manifest or query reproduction | Original exports are preserved but serve different schemas | Canonical SHA-256 payload; verified JSON import; URL state; CSV/Markdown reports | Tamper and round-trip tests |
| T10 / diagnostics | No browser recurrence conservation drawer or run-regime delta | Existing views expose the retained models' own metadata | Explicit equations, exact bounds, measured residuals, elapsed time, active flags and regime shifts | Conservation tests and browser checks |
| E01 / initial workspace | Local Git and delete permissions blocked under `misC` | OS filesystem denied `.git/config` writes | User-designated `Unclassified` passed write/Git proof; clean clone used for release | Git status and revision verified |
| E02 / audit tooling | Requested 58-gate reference absent | Current Hallmark has `references/gates.md` with 90 rows; no `slop-test.md` | Audit actual upstream specification, preserving raw reports | Report actual results, never inferred pass |
| E03 / baseline linter | Generated monolith stresses one linter check; render dependency absent initially | Upstream check30 maximum-call-stack error; no puppeteer-core | Source-target lint plus browser runtime tests; render tooling installed separately | Raw baseline evidence retained |

The baseline API suite passed 624 tests. No reproducible existing numerical/functional bug was confirmed by the forensic agent. Visual violations and missing requested capabilities are not represented as arithmetic bugs.

## Baseline Hallmark evidence

`docs/terminal-audit/before-lint.json`: 989 FAIL, 590 REFLEX, 19 WARN on the standalone monolith. These counts are incomplete static evidence: check30 overflowed and rendering did not run. `docs/terminal-audit/.hallmark/before.json` records the initial wiring inventory. Final reports must state source versus rendered scope and preserve any unresolved results.

Export supplement: preserve `helioforge-configuration.json`, dynamic per-lesson `helioforge-${lesson.id}.json`, and both learning-progress export handlers in addition to the 27 patterns originally recorded.

## Integration defects found and repaired during browser/code review

| ID / component | Reproduction and root cause | Fix | Proof |
|---|---|---|---|
| T11 / Overview CAPEX highlight | Highlight a project; child text retained accent on accent background (`experiences.css`) | Token accent-ink inherited by highlighted text | Axe contrast scan |
| T12 / shell and Learning names | Mobile command text is hidden; runtime lesson/wire labels replace visible names (`views.ts`, `completion-ui.ts`, `experiences.ts`) | Explicit command name; lesson/wire native visible names and descriptive titles | All-route axe and final-quiz regression |
| T13 / narrow controls | Council signing action exceeds320px; inherited wide typography | Narrow technical text, compact actions and reachable scroll regions | Eight-width control checks |
| T14 / scene Canvas | Canvas2D accepts concrete colours rather than CSS custom-property strings (`scene.ts`) | Resolve theme tokens before painting/stroking | Scene route and browser error checks |
| T15 / sweep state | Run valid matrix then invalid bounds; previous results survive a thrown call (`terminal-ui.ts`) | Clear matrix, sensitivity and selected point before calculating | 49cells→0 invalid-sweep browser regression |
| T16 / CSV context | Standalone CSV omitted synthetic label, flags and explanations (`terminal-manifest.ts`) | Repeat dataKind/status/flags/warnings in each row | Unit and browser CSV parsing |
| T17 / model copy | Markdown asserted every SOC endpoint differs; chart implied one unconditional frontier | Use may differ and service-equivalent conditional-frontier description | Markdown regression and code review |
| T18 / closed content | Collapsed details/offcanvas navigation still produced descendant geometry | Explicit closed-details display and mobile-nav visibility | Root/visible-control checks and render sweep |
| T19 / non-text contrast | Field boundaries fell below3:1; muted text below requested APCA floor | Explicit field borders and78%L muted token | Render floor and measured min WCAG9.10:1 / abs Lc63.61 |
| T20 / tall selection rows | Architecture descriptions lived inside75px buttons | Semantic rows preserve all descriptions beside compact selection buttons | Preservation/unit/browser checks |

| T21 / connection status | API-backed CI expected full connection wording; compact copy reduced the accessible status to API or Preview (`views.ts`) | Restore API connected and Snapshot preview wording; visually hide detail only at narrow widths | Original API smoke/hybrid/Champion journeys and 248-check Terminal matrix |
| T22 / drag automation | Dense pilot row centre lands on descendant text; default geometric drag origin fails (`scripts/browser-roadmap.py`) | Drag the exposed native article edge to the target stage heading; retain unsaved-stage and fresh-note assertions | Real Chromium native drag opens the unchanged evidence form |
