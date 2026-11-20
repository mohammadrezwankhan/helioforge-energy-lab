# CI, browser export and release verification

> Inspected source: [`fb42eb4d9b0c87e692710e8e867ab5190ea831a7`](https://github.com/mohammadrezwankhan/helioforge-energy-lab/tree/fb42eb4d9b0c87e692710e8e867ab5190ea831a7), 20 November 2026. This is a source and documentation snapshot, not a new test run, scientific certification, release or cloud publication.

## Original pipeline

The [original research CI](../../.github/workflows/ci.yml) runs backend checks across Python 3.11–3.13, and separately tests browser source, exports and the numeric dependencies declared in [apps/api/pyproject.toml](../../apps/api/pyproject.toml) and [apps/web/package.json](../../apps/web/package.json). Other configured GitHub workflows cover hardened CI, CodeQL, Cloudflare, preview and traceability. Required status contexts and runner labels are repository-specific. A queued or skipped job is not interchangeable with a successful original check.

## Review before merge

1. Re-read exact candidate and base SHAs and complete changed-file list; inspect app code and any generated files.
2. Run targeted Python/Node checks on the candidate where possible, and require original GitHub workflows on its head/merge-queue ref.
3. Review branch ruleset/protection, human approvals, merge queue and signature requirements. Never weaken any gate to accelerate merging.
4. Merge only after gates pass with an expected-head guard, then verify new main revision.
5. Separately capture site artifact identity, protected CSP/headers, deployment ID and deployed content hash before saying publication succeeded.

## Separate Cloudflare builds

The dedicated site uses `node scripts/build-domain.mjs` and `node scripts/check-domain.mjs` to publish complete `.cloudflare/site` to the dedicated project. The `mklab-apps` collection instead requires a separately assembled aggregate artifact; **do not replace a collection with one app output**. [docs/CLOUDFLARE.md](../CLOUDFLARE.md) details the exact source/CSP/hash and rollback sequence. GitHub Pages success is not a Cloudflare deployment receipt.

This documentation PR modifies no CI workflow, no release manifest, no site artifact and no remote deployment.
