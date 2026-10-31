# Architecture-atlas startup headroom

The catalogue payload repair and storage diagram semantics fix produced runtime 5cdab66f1f6ebe35a8723809c46f45a6fccdb9a5dcf0da941d4e53c692fbe860. Its full retained local run had phone cold LCP samples of 2136, 2268 and 2520 ms: the last sample exceeded the unchanged 2500 ms limit by 20 ms. Layout time increased across that run while response-end timing remained near 1.3 seconds. Host workloads are uncontrolled; this observation does not prove the later role attribute caused the slowdown. See [the entire prior attempt](performance-prior-attempt.json).

The hybrid page now keeps its atlas heading, search/filter controls and native architecture selector available, while rendering the 36 card results when the atlas approaches the viewport or a user focuses/uses its controls. This updates the results container without remounting the canvas. Readiness stays in the current tab and is omitted from workspace storage/exports. The observer rebinds after root replacement, rejects stale callbacks, disconnects on pagehide and has an immediate fallback when IntersectionObserver is unavailable. Busy card selections remain disabled and guarded.

The storage dispatch diagram also receives a valid named group role. The earlier PR38 CI artifact confirms no duplicate-ID or aria-prohibited-attr review items remain. Its contrast review items and native assistive-technology acceptance remain open; zero automated violations is not a WCAG certification.

## Current candidate

Runtime SHA-256: c0f3240a9a278f17c82ffef1d5dec8fda19ab34e6edc3b264298f040442cd2d1.

Six initial regressions failed before the fix; the expanded focused suite passed eight checks. The full frontend suite passed 241 tests, and build/source-preview/domain checks passed. Independent read-only review found no blocking lifecycle, state, busy-selection or keyboard-loading defect. The capture/onboarding suite passed 63 checks; fresh images are in ../screenshots/atlas/ and [capture-results.json](capture-results.json).

The strict performance harness passed all 12 loads and 96 interactions, with no functional errors or LCP-budget failures. Every response matched this runtime. The phone profile uses 390 × 844 CSS pixels, 4× CPU slowdown, 150 ms latency and 1.6 Mbps throughput. These are local HTTPS/gzip measurements on Windows, not physical-device or field results.

| Profile | Cache | LCP samples, ms |
|---|---|---|
| desktop | cold | 392, 204, 232 |
| desktop | warm | 120, 124, 108 |
| phone_viewport_constrained_emulation | cold | 2052, 2024, 2048 |
| phone_viewport_constrained_emulation | warm | 1412, 1456, 1472 |

The full raw run is [performance-candidate.json](performance-candidate.json). All earlier attempts remain retained. Remote CI and public deployment are evidenced separately by the final publication receipt.

## Remaining acceptance

Chrome Rezwan completed desktop/laptop/mobile/tablet viewport checks against the earlier 2152500d runtime, then native control stopped because the tool could not verify the active browser URL. Those observations are not relabeled as this candidate. Native 200%/400% zoom, NVDA and native file-picker checks remain unexecuted. Physical Apple/Android devices, experienced screen-reader users and eight uncoached participants are unavailable, as confirmed by the user. Field p75/INP and independent scientific/calibration acceptance remain open. All 63 live-provider cases remain deferred; no paid provider calls or paid services were added.
