# Retained performance baseline

Windows desktop laboratory, Chromium, exact local HTTPS artifact. Phone profile is a 390px viewport, 4x CPU slowdown and CDP 150ms / 1.6 Mbps down / 0.75 Mbps up. This is not a physical phone or field p75/INP. Host background workloads are uncontrolled. All runs and failed harness attempts remain available.

| Profile / cache | Runs | LCP min / median / max (ms) | Maximum CLS |
|---|---:|---|---:|
| desktop / cold | 3 | 1216 / 1248 / 1300 | 0 |
| desktop / warm | 3 | 1056 / 1140 / 1152 | 0 |
| phone_viewport_constrained_emulation / cold | 3 | 11648 / 11972 / 12336 | 0 |
| phone_viewport_constrained_emulation / warm | 3 | 10028 / 10072 / 10124 | 0 |

LCP <=2500ms, INP <=200ms and CLS <=0.1 are appraisal targets. Constrained profile loading exceeds the LCP target. Measurement execution PASS does not mean the target passed. Automation interaction latency includes scrolling, waiting and two frames, and is not INP. Navigation timing, encoded/decoded/transfer bytes, long tasks, heap and idle animation callbacks are retained in the raw JSON. Pure JavaScript parse cost is NOT_MEASURED separately from load/main-thread work.

Proposed next-release guardrails (P, not implemented): preserve all numerical replay checks and standalone offline behavior; do not exceed the current 13,630,124 decoded-byte runtime without explicit review; establish a separately measured hosted-shell/on-demand-data design against this baseline; rerun three cold and three warm real-device measurements before setting a compressed-byte or interaction budget. No improvement or scientifically meaningful latency threshold is inferred from these lab runs.
