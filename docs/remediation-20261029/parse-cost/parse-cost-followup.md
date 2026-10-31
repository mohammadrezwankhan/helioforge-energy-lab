# Candidate G parser and compilation trace

This is a supplemental local diagnostic, separate from the untraced page-load benchmark. It records one instrumented cold navigation for desktop and one for a constrained phone profile. Browser tracing adds overhead; values here should not be compared directly with untraced load timings.

## Command and artifact

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; & 'C:\Users\MRK\Downloads\misC\helioforge-audit-20261027\repo\.venv\Scripts\python.exe' scripts/acceptance-parse-cost.py --site .cloudflare/acceptance-20261029-g/site --url https://127.0.0.1:4200/run/ --output docs/remediation-20261029/parse-cost
```

- Candidate runtime SHA-256: `8ef56f4df539590392696552c2b10651faf953790d8018c982a949b21e0ccb00`
- Chromium: `156.0.8078.4`; Python: `3.12.14`
- Two runs completed, two passed, zero trace loss, zero page errors.
- Raw traces: [`desktop.trace.json`](desktop.trace.json) and [`constrained_phone.trace.json`](constrained_phone.trace.json)
- Machine-readable results, event inventory, intervals and trace hashes: [`parse-cost-results.json`](parse-cost-results.json)

## Measurements

All durations are main-thread interval unions in milliseconds. Nested and overlapping event intervals are merged. The parse/compile combined column deduplicates overlap; parse and compile values must not be added together.

| Profile | Main-thread JavaScript parse | JavaScript compile | Parse + compile union | HTML parse (separate) | JavaScript execution |
|---|---:|---:|---:|---:|---:|
| Desktop, 1440×1000 | 30.861 | 41.512 | 42.181 | 35.526 | 513.280 |
| Constrained phone, 390×844, CPU 4× | 245.192 | 349.144 | 353.856 | 306.176 | 1,486.959 |

The phone profile also applied 150 ms network latency, 1.6 Mbps download, and 0.75 Mbps upload. Parse and compile event intervals overlap heavily: about 30.192 ms on desktop and 240.480 ms on the phone profile. The combined union is therefore the deduplicated total for those V8 intervals.

The V8 parser events observed were `V8.ParseFunction`, `V8.ParseProgram`, and `V8.PreParse`, all in `disabled-by-default-v8.compile`. Compilation events observed were `V8.Compile`, `V8.CompileCode`, `V8.CompileEval`, `V8.CompileIgnition`, `V8.CompileIgnitionFinalization`, `V8.CompileScript`, and `v8.compile`. Execution events observed were `EvaluateScript` and `FunctionCall` in `devtools.timeline`. `ParseHTML` was observed in `devtools.timeline` and measured separately; it is excluded from JavaScript parser cost. The event names and per-name counts/durations are preserved in the JSON.

## Method and limits

The runner uses the Chrome DevTools Protocol `Tracing` domain with `ReturnAsStream`; it reads the JSON trace using the protocol `IO` stream methods and keeps the original trace bytes. See the [official CDP Tracing](https://chromedevtools.github.io/devtools-protocol/tot/Tracing/) and [IO](https://chromedevtools.github.io/devtools-protocol/tot/IO/) protocol references.

The main thread was selected from `CrRendererMain` thread metadata and matched to trace events tagged with the requested loopback page URL. Each trace contained one URL-matched frame ID; the initial trace pass did not capture `Page.getFrameTree`, so a complete frame count is unavailable. Only explicit V8 parse-named events count as JavaScript parser work. Compile-labeled events may include parsing, so the report does not infer a non-overlapping parse/compile split. `ScriptDuration` is not used as a parser proxy.

These two runs are diagnostic observations, not physical-phone measurements, production p75, field INP, or proof of user-perceived performance. The test host was uncontrolled, and only one cold run was recorded per profile.
