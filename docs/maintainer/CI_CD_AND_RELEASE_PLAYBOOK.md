# CI, release and publication playbook

## Existing gates

| Workflow | Source-defined responsibility |
|---|---|
| `ci.yml` | Python 3.11/3.12/3.13 API lint/tests; Node 24 browser build/typecheck/tests; numerical asset checks; publication-script tests; domain/build-receipt checks; actual browser acceptance and retained evidence |
| `hardened-ci.yml` | Separate workflow/secrets/SAST/dependency/Trivy modes and Python/browser lint/type/format/test quality modes; retain execution receipts even on failure |
| `codeql.yml` | Repository CodeQL analysis and report checking; independent of numerical validity |
| `cloudflare.yml` | Build and check the existing browser export and dedicated-domain output; verification workflow is not itself a successful deployment |
| `deploy-dashboard.yml` | Guarded existing GitHub Pages documentation/teaching route; validates and uploads `docs/` |
| `preview-pages.yml` | Existing manual preview route with public-repository/main-branch guards |
| `portfolio-dashboard-check.yml` | Existing portfolio guide/source/SVG checks for its scoped paths |
| `mklab-traceability-sync.yml` | Read/live traceability check and conditionally configured source-observation bridge; an observation is not deployment proof |

Sources: [.github/workflows/ci.yml](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/.github/workflows/ci.yml), [.github/workflows/hardened-ci.yml](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/.github/workflows/hardened-ci.yml), [.github/workflows/codeql.yml](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/.github/workflows/codeql.yml), [.github/workflows/cloudflare.yml](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/.github/workflows/cloudflare.yml), [.github/workflows/deploy-dashboard.yml](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/.github/workflows/deploy-dashboard.yml), [.github/workflows/preview-pages.yml](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/.github/workflows/preview-pages.yml), [.github/workflows/portfolio-dashboard-check.yml](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/.github/workflows/portfolio-dashboard-check.yml), [.github/workflows/mklab-traceability-sync.yml](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/.github/workflows/mklab-traceability-sync.yml).

The author’s local subset is enumerated in the [ledger](VERIFICATION_EVIDENCE_LEDGER.md); it does not replace current PR checks. Historical 24/24 source checks on November 18 are not a candidate merge decision. The protection 403 and visible ruleset list leave effective-policy discovery to the integration owner; do not disable required checks or infer approval from partial metadata.

## Documentation change review

1. Bind the review to the exact source and complete candidate tree. Inspect every changed path; application/scientific/test/workflow/dependency/license/security/media bytes remain preserved in this task.
2. Validate canonical Markdown links, immutable source locators, CFF, required-output mapping, renderer freshness, escaping and source preservation. Inspect readable narrow/mobile layouts in a permitted real browser when available; retain NOT_RUN if the environment prevents it.
3. Obtain independent content/scientific QA on the frozen package. A changed candidate invalidates the prior decision for affected scope.
4. Create/reconcile the PR through the integration owner, discover current head/base/required checks/reviews, and wait for the actual requirements. Merge only against the expected reviewed head.
5. Record the final documentation commit, merge commit and deployment identity outside the self-referential document commit. Then verify publication separately.

## Existing publication routes

The GitHub Pages workflow publishes the established `docs/` tree; the new `docs/reference/index.html` handbook sits within that route. A documentation navigation anchor does not alter the companion’s inline calculation script, styles or CSP. Its declared repository route is [GitHub Pages](https://mohammadrezwankhan.github.io/helioforge-energy-lab/). The provider Pages-metadata endpoint was unavailable to the review connector, so current deployment/content status must be observed later. [.github/workflows/deploy-dashboard.yml](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/.github/workflows/deploy-dashboard.yml).

The existing dedicated browser publication is [MKGrid overview](https://mkgrid.co.technology/) and [runtime](https://mkgrid.co.technology/run/), with project settings in `cloudflare-domain.json`. `build-domain.mjs` produces `.cloudflare/site`; the full verified site and matching response-header policy are the release unit. Existing `docs/CLOUDFLARE.md` describes dedicated/collection separation and header/deployment rollback. This documentation task creates no hosting, domain, project, tag or release. [docs/CLOUDFLARE.md](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/docs/CLOUDFLARE.md), [cloudflare-domain.json](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/cloudflare-domain.json), [scripts/build-domain.mjs](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/scripts/build-domain.mjs).

Do not upload a single-app export over an existing collection root. Do not treat a successful GitHub Pages job as an MKGrid deployment. An existing public introduction or old runtime still being reachable does not establish publication of this documentation candidate.

## Publication evidence checklist

Retain the successful exact-revision workflow/artifact receipt, deployed provider identity and final URL. Inspect distinctive new content such as the model-atlas heading and the dated annual-comparator limit. Verify local stylesheet/script routes, navigation, CSP, content hashes where available and the published source/runtime metadata. For the dedicated site, preserve the generated policy’s exact script hashes and its distinct film route rules; restore the previous successful deployment and matching header snapshot together on rollback. No wildcard/unsafe script permissions are needed for the new handbook. [docs/CLOUDFLARE.md:67–83](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/docs/CLOUDFLARE.md#L67-L83), [apps/web/src/release-provenance.ts](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/web/src/release-provenance.ts).

## Releases and rollback

The source CFF and packages retain the known 2.0.0 release identity; the API health remains 0.3.0. Documentation updates belong under an unreleased change note unless a separately approved release is actually made. Keep prior site artifacts and evidence; reverting documentation must not reset user databases or numerical source. If a live deployment fails, report content/merge/publication outcomes separately and restore the known matching artifact/policy pair rather than weakening checks.
