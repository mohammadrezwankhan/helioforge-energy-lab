# Handover, backup and recovery procedure

> Inspected source: [`fb42eb4d9b0c87e692710e8e867ab5190ea831a7`](https://github.com/mohammadrezwankhan/helioforge-energy-lab/tree/fb42eb4d9b0c87e692710e8e867ab5190ea831a7), 20 November 2026. This is a source and documentation snapshot, not a new test run, scientific certification, release or cloud publication.

This is a **recommended** future recovery procedure. It is not a fresh restoration test or an appointed second maintainer.

1. Recover authorized source and full exact commit SHA; verify the original Git tree, license, source/workflows and referenced released tag.
2. Recreate Python 3.11–3.13 packaged runtime per [START_HERE](../../START_HERE.md), and retain the original pinned package manifest. Never disable local Host/Origin checks to “fix” access.
3. Retain and separately back up local `data/helioforge.sqlite3` with the server stopped; restore in a separate copy, then verify run IDs and input/result records.
4. Check that browser saved setups are *inputs* rather than trusted numerical results. Export configuration/workspace state separately; reconnect to existing API history after recovery.
5. Run original Python and web tests, confirm hybrid conservation, storage MILP constraints, and provenance metadata. Record exact versions and output.
6. If publishing, build complete dedicated-domain or collection output, validate CSP hashes, and restore provider deployment ID plus matching header policy in rollback.
7. Record access gaps, undecided model validation, provider consent, pending review and evidence owners; never copy local credentials or client data into repository docs.

The existing [launcher backup notes](../../START_HERE.md) include a small synthetic SQLite restore rehearsal, but this does not establish disaster recovery of any live operational environment.
