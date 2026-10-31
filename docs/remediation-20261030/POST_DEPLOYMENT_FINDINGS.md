# Post-deployment findings and rollback

Main commit `d7e977085c00e1967d6cb55fdeffa417bc7b22c0` passed remote release CI `40982137917` and was uploaded as an exact 364-file CI artifact to Cloudflare deployment `66dbd147-86eb-4c1e-a46c-5df8c539c691`. Its runtime was the previously reviewed `8ef56f4df539590392696552c2b10651faf953790d8018c982a949b21e0ccb00`. Public verification then found a reproducible loading race, so the deployment and matching security policy were rolled back to deployment `777ff5d5-be6d-4018-a0a4-392167601a7e`. This candidate is historical evidence, not the final accepted release.

## Deferred example race

Selecting `utility-pv-dc/baseline` starts a verified data download. Clicking the already-selected baseline scenario before that download completes advances the view's state revision without changing its full configuration key. The completion callback rejected its captured revision and left a loading notice and placeholder result. The asset arrived with HTTP 200, exactly 19,409 bytes, and SHA-256 `f2551a2e2949b4ddb7eaeacdf7a8eab0db1ec6bc306762f6453fbc34f3ddf7fd`.

The preceding injected 503 and retry had completed; the failure occurred on the next architecture selection. The historical runner's stage label had not yet advanced, so it initially pointed at the earlier retry. The raw failed report and focused reproduction remain retained. CI now includes the hosted-data/export runner against the exact generated static site, in addition to API-backed and ordinary browser suites.

## Public HTTP client identification

The original Python urllib request received Cloudflare HTTP 403/error 1010 and stopped. Cloudflare's [official error 1010 documentation](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-1xxx-errors/error-1010/) explicitly describes this Pages restriction and recommends a descriptive application User-Agent instead of the library default. The verifier now identifies itself as `HelioForge-Release-Verification/1.0` with the public repository URL. It does not impersonate a browser, bypass TLS, continue after denial or change bot protections. Its boundary test verifies both the honest header and the stop after one denied request.

## Existing robots Worker

Public HTTP checks found 360 files byte-identical to CI and one deliberate edge transformation: the existing `ecosystem-robots-policy` Worker appends explicit crawler permissions to `robots.txt`. Applying its retrieved source to the CI origin text reconstructed the live 617-byte body exactly, SHA-256 `70d283d4d0da3d12fa1874814d65bdf405ef533388b143a778bea34d6201a008`. The body also matches the dated October 28 observation. This establishes unchanged response content, not an independently recorded historical Worker source revision. The Worker was not modified. The raw static-file equality failure remains retained and is reconciled separately with the control-plane source.

The rolled-back candidate also passed 18 public migration checks and five production captures; these remain bound to that candidate and must be repeated for the corrected runtime. No paid provider, physical-device, native assistive-technology or participant acceptance is claimed.

## CI export cadence

Linux CI reached the third study and timed out during its exports after the preceding downloads succeeded. Chromium explicitly limits download bursts to ten within one second (`LocalFrame::ShouldThrottleDownload` in [Chromium source](https://raw.githubusercontent.com/chromium/chromium/main/third_party/blink/renderer/core/frame/local_frame.cc)). The acceptance runner now spaces real export clicks by at least 250 ms and records that cadence. It retains real downloaded-file byte/provenance comparisons and does not alter browser protections. Failed executions remain preserved; the next CI result tests this diagnosis.
