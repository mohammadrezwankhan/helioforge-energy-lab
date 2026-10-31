# Cold-load repair and remaining acceptance

Subsequent public validation found two LCP misses. The additional payload repair,
complete retained public run and new local measurements are recorded in
[cold-load headroom](../cold-load-headroom/README.md). The results below retain
their original artifact identity and laboratory scope.

The constrained-phone laboratory miss was reproduced on the published runtime
`07f2411611c2efd1ea9a3e7290391d3b80728d76a5b25a1820ef1630c371d8d6`.
The corrected runtime is
`bc89a858062e414ab7c5c0e1ca6d3af0714b062c2856af8731704937bf9044d9`.
These identities describe exact UTF-8 HTML response bytes, including inline CSS
and JavaScript. CI and deployed identities belong to the subsequent publication
receipt; local results alone do not prove publication.

## Cause and repair

A retained public cold-load trace observed 498 ms of synchronous layout and
109 ms of style calculation beneath `mountEnergyScene` → `resize` →
`getBoundingClientRect`. The canvas was below the viewport. The same trace
sampled 132 ms in repeated number formatting. Tracing adds overhead and is
supplemental evidence, not the primary load benchmark.

Canvas mounting now uses dimensions delivered by ResizeObserver and waits for
IntersectionObserver visibility before drawing or starting animation. Repeated
number formatting reuses an Intl.NumberFormat for each precision, preserving
rounding, null, negative and invalid-precision behavior. Keyboard controls,
textual asset alternatives, reduced motion and disposal remain available.

The two targeted regressions failed before the fix and passed afterward. The
complete frontend suite passed 227 tests; type checking and the build passed.
A separate agent reviewed the application diff and found no actionable defect.

An additional card-containment experiment showed no material benefit and was
removed. Its raw trace is retained in the delivery evidence; it is not shipped.

## Paired laboratory evidence

The same strict harness tested the old and corrected artifacts sequentially on
this Windows host using loopback HTTPS/gzip. Each artifact had 12 navigations
and 96 interactions. The phone profile used 390 × 844 CSS pixels, 4× CPU
throttling, 150 ms network latency and 1.6 Mbps download throughput. Other host
workloads were not controlled. No physical-device or field claim is made.

| Artifact | Cold phone LCP, ms | Warm phone LCP, ms | Budget failures | Functional failures |
|---|---|---|---:|---:|
| Published baseline | 2536, 2516, 2572 | 2060, 1936, 1980 | 3 | 0 |
| Corrected candidate | 2360, 2388, 2444 | 1888, 1924, 1880 | 0 | 0 |

The unchanged laboratory limit is 2500 ms. The baseline exited 1; the candidate
exited 0. Every navigated response matched its expected runtime SHA-256. See
[baseline](performance-baseline.json) and [candidate](performance-candidate.json).
These are all runs in the paired experiment, not a selection of passing runs.
Earlier public and diagnostic observations remain in the delivery archive.

The harness now fails on LCP-budget, interaction, page-error, response-identity
or incomplete-coverage failures. It reads each document's own CDP duration
snapshot; subtracting the previous document's counters had incorrectly produced
zero warm-run CPU totals. Page-error listeners are removed between runs so a warm
error cannot modify cold-run evidence. Eight lightweight harness regressions
passed and are included in remote CI. Automation-to-two-frame latency remains
distinct from field INP.

Fresh local desktop, tablet, mobile and social captures are bound to the corrected
runtime. The accompanying layout/onboarding capture suite passed 63 checks.
Published screenshots are selected from `../screenshots/cold-load/`; the raw
capture report and its original relative image paths are retained in the archive.

## Numerical follow-up

[Actual solver diagnostics](dunkelflaute-solver.json) record both unchanged
SciPy/HiGHS calls for the frozen `compare-dunkelflaute` default. Both reported
status 0, optimal termination, zero MIP gap, matching objective/dual bound and one
node. Stage two preserves the engine's minimum-shortfall + 1e-7 kWh constraint.
No options or solver tolerances were changed. Source, fixture and test hashes
were checked before and after. Two study acceptance tests and three targeted
dunkelflaute tests passed. This is solver evidence for one synthetic fixture,
not field calibration, scientific certification or proof for every possible
input. The application result contract was not changed.

## Remaining gates

The user confirmed that physical devices, experienced screen-reader users and
eight uncoached participants are unavailable. Required physical Apple/Android,
VoiceOver/TalkBack, participant and field-p75/INP evidence therefore remains
BLOCKED. Available desktop native checks are recorded separately against their
actual artifact and environment; they cannot substitute for those gates.
Independent scientific/calibration review remains unavailable. No telemetry
was introduced to create field data. All 63 live-provider cases remain deferred
under the instruction not to make paid provider calls.

F14 is a traceability requirement: blocked and unexecuted cases must remain
visible. Old ledgers retain their original artifact identities; the new receipt
lists exact current evidence instead of relabeling historical tests as reruns.
