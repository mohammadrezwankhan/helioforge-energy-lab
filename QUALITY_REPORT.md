# HelioForge Energy Lab: verification and limits

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
