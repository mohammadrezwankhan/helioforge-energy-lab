# HelioForge Energy Lab: verification and limits

## Current source snapshot — 31 October 2026

The reviewed `main` source is [`a071652ab2b59bafd9a43245cd4620103dcf6eba`](https://github.com/mohammadrezwankhan/helioforge-energy-lab/commit/a071652ab2b59bafd9a43245cd4620103dcf6eba). The [Verify research release CI run](https://github.com/mohammadrezwankhan/helioforge-energy-lab/actions/runs/41049149199) passed at this exact revision. Its [Python 3.12 backend job](https://github.com/mohammadrezwankhan/helioforge-energy-lab/actions/runs/41049149199/job/124040589567) reports **679 passed and one deprecation warning**; the Python 3.11, Python 3.13, browser and browser-export jobs also succeeded. These are existing remote software checks, not a new local test run or independent scientific validation.

The current source inventory lists **59 distinct study IDs across 12 workspaces** in [CAPABILITIES.md](docs/CAPABILITIES.md) and [MODEL_REGISTRY.md](docs/MODEL_REGISTRY.md); the [experiment index](docs/roadmap/INDEX.md) reconciles the listed studies. The older 39-study statement belongs to a dated record and is not the current inventory.

Results come from **bundled synthetic examples**, which are precomputed; the **bounded browser Terminal**, which runs a deterministic 24-hour energy balance with a greedy policy and is not an optimizer; and the **local Python application**, which runs new advanced-study calculations and storage optimization. Opt-in external providers are separate integrations that require their own consent and execution evidence.

## Separate publication evidence — 30 October 2026

The [`appraisal-remediation-20261030` prerelease](https://github.com/mohammadrezwankhan/helioforge-energy-lab/releases/tag/appraisal-remediation-20261030) identifies source [`7de688b40650a629375ca37b372eaf109a15d5f9`](https://github.com/mohammadrezwankhan/helioforge-energy-lab/commit/7de688b40650a629375ca37b372eaf109a15d5f9) and Cloudflare deployment `29c56999-bba9-48c5-a498-a6995a6c9277`. That record applies to its named source and deployment; it does not establish a Cloudflare deployment of the newer `a071652` snapshot or exclude later out-of-band deployments.

The newer source's [successful deployment run](https://github.com/mohammadrezwankhan/helioforge-energy-lab/actions/runs/41049149373) reports a GitHub Pages destination. That is separate from the Cloudflare publication record. No current Cloudflare source identity is inferred from the newer source's CI or Pages result.

## Published v2.0.0 release — 26 October 2026

The [`v2.0.0` release](https://github.com/mohammadrezwankhan/helioforge-energy-lab/releases/tag/v2.0.0) resolves to tag commit [`c1c67652e0b27c807ddfbcaaa9f987d37ca0f992`](https://github.com/mohammadrezwankhan/helioforge-energy-lab/commit/c1c67652e0b27c807ddfbcaaa9f987d37ca0f992), and its release record reports **653 Python tests**. That count and its deployment receipt apply to the tagged release, not either newer source snapshot above.

## Historical report — 30 September 2026

The checks below are historical evidence for the named September commit, not current test counts or publication status. The [18 October full-spectrum verification](docs/roadmap/VERIFICATION.md) and [roadmap completion / external prerequisites](docs/roadmap/COMPLETION.md) are retained as dated records and do not supersede the 31 October source evidence above.

Recorded 2026-09-30. **Eligible for source-demo publication under the first-party MIT grant, with upstream notices retained. This does not authorize a live domain service or relicense third-party content.**

## Executed source checks

The [GitHub Actions run](https://github.com/mohammadrezwankhan/helioforge-energy-lab/actions/runs/36642930805) completed successfully for `ed0436e7ec19eecb8075ea493271ee18730d2fa5`. Its [workflow](.github/workflows/ci.yml) is the executable check definition. The final branch badge and release record may reference later documentation or merge commits; the evidence below names what was actually exercised.

- `python -m ruff check apps/api`
- `python -m pytest apps/api/tests (Python 3.11, 3.12, 3.13)`
- `npm ci, npm audit, typecheck, build and tests in apps/web`
- `Three Playwright scripts against the local Python API`

Build and test success establishes only the contracts asserted by these suites. Tests were not replaced with success stubs, and environment-dependent failures were resolved or verified on Linux CI.

## Clean-clone demo checks

The documented `node scripts/preview-demo.mjs` launcher passed from a remote clone at `ed0436e7ec19eecb8075ea493271ee18730d2fa5` on `2026-09-29T23:24:03.496Z`. See the [machine-readable record](docs/repository/quickstart-verification.json).

- Initial render at 1440 px and 390 px, with visible content, no uncaught page errors and no horizontal overflow.
- Requests for `.git/config`, `.env`, `server.mjs`, `package.json` and a traversal-shaped path were rejected; HEAD returned an empty body.
- Navigation: one visible action exercised: Learning studio.
- [Desktop screenshot](docs/repository/demo-desktop.png) and [mobile screenshot](docs/repository/demo-mobile.png) capture the actual app.

Timing values are single local observations including automation overhead. They are not a performance benchmark. These checks do not establish complete user journeys, offline/PWA correctness, keyboard/screen-reader accessibility, or Firefox/WebKit compatibility.

## Security and provenance

Gitleaks 8.30.1 scanned all local Git revisions at `ed0436e7ec19eecb8075ea493271ee18730d2fa5` with zero unresolved findings. Any reported matches were checked against exact, individually reviewed nonsecret lines; no blanket suppression was used. The final publication process repeats the history scan after the merge.

Python and applicable npm audit runs reported no known vulnerabilities in the evaluated installed dependencies. The Python reports are date-bound; dependency changes require a new audit. Audit snapshots can become stale. GitHub dependency alerts and update proposals are enabled where supported. Use [SECURITY.md](SECURITY.md) for reporting; these checks do not certify security.

Local Windows HTTP filtering by AdGuard affected some raw header assertions. Tests retain server-generated policy/metadata checks, and actual HTTP behavior was also checked on Linux CI. No host security control was disabled.

## Independent review and promotion

Separate principal-engineering, maintainer, security and DevRel reviews informed the release gate. The repository-factory ledger records each finding and its resolution; this is not third-party certification.

Internal [readiness score](docs/CHAMPION_SCORE.md): **86/100**. Major promotion remains held below 90 and until editorial fit is confirmed. Outreach files are drafts; no email, community post, or external-list submission is implied.
