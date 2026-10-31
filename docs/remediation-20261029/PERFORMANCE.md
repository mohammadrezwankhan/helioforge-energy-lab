# Retained laboratory performance

Final runtime: `8ef56f4df539590392696552c2b10651faf953790d8018c982a949b21e0ccb00`. No physical-device or field claim.

| Profile | Cache | Runs | Median LCP ms | LCP range ms | Runs over 2500 ms |
|---|---|---:|---:|---:|---:|
| desktop | cold | 3 | 308 | 280–480 | 0 |
| desktop | warm | 3 | 168 | 164–200 | 0 |
| phone_viewport_constrained_emulation | cold | 3 | 2744 | 2708–2748 | 3 |
| phone_viewport_constrained_emulation | warm | 3 | 1968 | 1956–1992 | 0 |

The prior monolithic phone emulation measured approximately 10–12.3 seconds. Earlier split/minified attempts, including candidate F with one LCP target miss, remain retained. The final untraced load results include CDP main-thread execution/layout deltas, long tasks, heap observations and interaction measurements. Those measurements are not field INP.

Two separate instrumented cold traces measure the observed V8 parser/compiler intervals on the frame-linked renderer main thread. They are diagnostics, not additional load-budget or field samples; tracing and other host activity affect cost. Compile intervals include overlapping parser work; the union column deduplicates overlap. Do not add the parse and compile columns.

| Trace profile | JS parse ms | JS compile ms | Parse/compile union ms | HTML parse ms | JS execution ms |
|---|---:|---:|---:|---:|---:|
| desktop | 30.861 | 41.512 | 42.181 | 35.526 | 513.28 |
| constrained_phone | 245.192 | 349.144 | 353.856 | 306.176 | 1486.959 |

The complete offline HTML remains self-contained. The hosted entry loads selected exact-data JSON chunks only as needed; hashes and byte counts must match before display. esbuild 0.28.2 is a pinned build-only dependency ([official transform/minification API](https://esbuild.github.io/api/#minify)). No analytics or runtime dependency was added.
