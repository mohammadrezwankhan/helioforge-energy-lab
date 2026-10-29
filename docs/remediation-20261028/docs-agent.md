# Capability and model-documentation work record

Date: 2026-10-28  
Scope: F02 capability truth, F10 study-model provenance, F13 useful indexable learning content; implementation evidence only.

## Findings and evidence

Evidence labels: **O** observed directly in this checkout or command output; **R** reported by the parent from a separate capture; **I** inference from the listed evidence; **P** pending work; **U** unknown or not represented in source.

- **O — Shared capability contract:** `scripts/capability-contract.mjs` is the common source for delivery-mode statements, three task-led starts, version facts, and generated registry content. It distinguishes bundled synthetic examples, bounded browser Terminal calculations, advanced local Python calculations, and opt-in local external providers. Overview/About/Methodology/Help and app facts are checked against the contract; README and `cloudflare.json` carry its public wording.
- **O — Study inventory:** the generated registry contains 12 workspaces and 59 study IDs, with one acceptance card per study. Cards link to implementation and tests and record catalogue fields/bounds, only-declared units, equations, limits, default fixture/evidence digests, and export references where available. Registry identities separate browser application, API package, hybrid catalogue, study catalogue, example data, model association, and result schema.
- **U — Missing version/schema evidence:** the source has no standalone study result `schema_version` or semantic study-catalogue version. Study example data has no declared dataset version. These are labelled `U`, with digests identifying current source objects; a digest is not a version or validation claim.
- **O — Acceptance evidence labels:** every study card marks independent hand checking `NOT RUN`; fixture presence/digests are not presented as hand validation. Invalid/boundary reruns, seeded determinism, convergence/feasibility and export execution remain `NOT RUN` where not evidenced by this documentation task.
- **O — Learning content:** original static page sources add a capability guide, a glossary, a directory, and a worked Terminal noon-row arithmetic example. The worked example states its synthetic inputs, equations, units, arithmetic, scope, source/test links, author, revision date, and related internal links. It checks one row only and explicitly does not claim an independent model comparison.
- **O — Generated local candidate:** an isolated build was produced earlier in this task under `.cloudflare/capability-docs-check-2`, with baseline source revision `74d6730e38323b69c180d7f4b4945d11010203f3` and a dirty-tree flag. Its generated domain runtime digest was `35c1e204735fa022c6e2132c053fdfbbfec3914ecc2ba210ca7e1977c61b1b85`. This is a local candidate, not a release receipt.
- **R — Separate deployed capture:** parent reported that the previously deployed static runtime matched its manifest at digest `a12384067a75ab7a3449c9b49936e923058bd7e92585f5a08f9c00ae735b203e` and an ordinary Chromium session succeeded. Parent also reported urllib receiving Cloudflare 403 code 1010. This evidence predates and does not validate publication of this task's local candidate pages.
- **I — What the local passes establish:** the contract test and output checkers establish internal consistency for the checked source and generated candidate. They do not establish publication, scientific calibration, independent validation, professional approval, or operational readiness.
- **P — Remaining closure:** deploy/publication receipt, live crawl of the new pages, user-session usability evidence, study-by-study independent calculation checks, and provider-specific execution evidence remain pending. Overall F02/F10/F13 deployment closure remains gated.

## Verification record

| Check | Expected | Actual |
|---|---|---|
| `node scripts/capability-contract.test.mjs` | 4 delivery modes, 3 task starts, separated version identities, complete 12-workspace/59-study map, and truthful unknown/not-run labels | **PASS** — JSON reports `status: passed`, `workspaces: 12`, `studies: 59`. |
| `node --check` on the capability contract, build scripts, and output checkers | All edited JavaScript parses | **PASS** — all five files (`capability-contract.mjs`, `build-cloudflare.mjs`, `build-domain.mjs`, `check-cloudflare.mjs`, `check-domain.mjs`) passed syntax checks. |
| `CLOUDFLARE_OUTPUT_ROOT=.cloudflare/capability-docs-check-2 node scripts/check-domain.mjs` (PowerShell environment assignment used) | Generated candidate has the required indexable pages, links, CSP, contract facts, registry links, and sitemap; no forbidden files | **PASS** — 9 pages, 12 workspaces, 59 studies, 65 files; runtime SHA-256 `35c1e204735fa022c6e2132c053fdfbbfec3914ecc2ba210ca7e1977c61b1b85`. |
| Same output root with `node scripts/check-cloudflare.mjs` | Generated app has canonical/structured facts, runtime hash, assets, and excludes source/config/database files | **PASS** — 11 app files; checker reports all listed checks passed. |
| Independent scientific validation / complete per-study acceptance | Every study has independent hand, boundary, determinism, convergence/feasibility, and export evidence | **NOT RUN** — do not infer this from the local consistency checks. |
| Deployment and public crawl of this candidate | New content is served at the canonical domain with a release/manifest receipt | **NOT RUN** — no deployment was performed or authorized in this task. |

## Changed files in this scope

- `scripts/capability-contract.mjs`, `scripts/capability-contract.test.mjs`
- `scripts/build-cloudflare.mjs`, `scripts/build-domain.mjs`, `scripts/check-cloudflare.mjs`, `scripts/check-domain.mjs`
- `cloudflare.json`, `README.md`
- `docs/CAPABILITIES.md`, `docs/MODEL_REGISTRY.md`, `docs/MODEL_REGISTRY.json`, `docs/learning-pages/`
- `apps/web/src/roadmap-data.ts` was regenerated after the parent added source references to two study definitions; no arithmetic change was part of this documentation work.

No deploy, paid provider request, commit, or push was performed. Parent-owned concurrent changes are not attributed to this scope.
