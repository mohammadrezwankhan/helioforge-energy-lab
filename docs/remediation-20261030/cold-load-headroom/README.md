# Additional cold-load headroom and accessibility repair

The earlier canvas/number-formatting repair passed its paired local run, but the full public run retained two LCP misses. The public record is preserved in [performance-prior-public.json](performance-prior-public.json), bound to runtime bc89a858062e414ab7c5c0e1ca6d3af0714b062c2856af8731704937bf9044d9. It is not relabeled as passing. One desktop sample had a 2705 ms delay before domain lookup; one constrained-phone sample reached 2536 ms.

The next repair removes full study definitions from the initial hosted document. The bootstrap retains each study's id, page and title. Existing content-addressed workspace assets carry the complete definitions and unchanged results. Before exposing results, the loader verifies the asset digest and size, validates the exact definition/result sets, hydrates the existing definition objects, then announces readiness. Prototype-sensitive study IDs are rejected at planning and runtime boundaries. The complete offline edition retains all data. No scientific values or model equations change.

The hosted HTML is 845394 bytes, down from 1103431 bytes (258037 fewer bytes). The research dossier waits for every research result before enabling download and also checks readiness in its action handler. Simultaneous study charts now use distinct accessible SVG title/description IDs, and named control containers use valid group or navigation semantics.

## Candidate verification

Runtime SHA-256: 2152500db86e3327e4636b24fab7ed460742ecec5e66e94ef631f0a51325322b.

All 233 frontend tests, TypeScript checking, source/generated-preview identity and domain build checks passed. Focused regressions failed before their implementation and passed afterward. The capture/onboarding suite passed 63 checks; fresh desktop/tablet/mobile/social screenshots are in ../screenshots/headroom/. Their report is [capture-results.json](capture-results.json).

The unchanged strict performance harness passed all 12 loads and 96 interactions, with zero functional errors or LCP-budget failures. The constrained profile uses 390 × 844 CSS pixels, 4× CPU slowdown, 150 ms latency and 1.6 Mbps download throughput. All responses matched the expected runtime. This is a local HTTPS/gzip laboratory measurement on Windows; other host workloads are uncontrolled.

| Profile | Cache | LCP samples, ms |
|---|---|---|
| desktop | cold | 316, 216, 200 |
| desktop | warm | 128, 180, 124 |
| phone_viewport_constrained_emulation | cold | 1928, 2100, 1892 |
| phone_viewport_constrained_emulation | warm | 1492, 1452, 1464 |

See [performance-final-local.json](performance-final-local.json). The pre-hardening local run is retained in [performance-local.json](performance-local.json). The limit remains 2500 ms. The hosted acceptance checker now compares each deferred definition and result against the complete frozen source; its prior failure on the old result-only schema is retained. Remote CI, production identity and final public checks are recorded separately in the publication receipt; this local evidence does not establish them.

## Open acceptance gates

The user has no physical Apple/Android devices, experienced screen-reader users or eight uncoached participants available. Viewport emulation and engineer desktop checks do not replace those sessions. Field p75 LCP/INP, independent scientific/calibration review and physical-device acceptance remain open. All 63 live-provider cases remain deferred by instruction; no paid provider calls or paid services were added. Earlier failed and diagnostic attempts remain in the delivery evidence.
