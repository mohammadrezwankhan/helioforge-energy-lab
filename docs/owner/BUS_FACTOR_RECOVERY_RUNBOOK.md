# Bus-factor and recovery runbook

## Recover the code and its evidence

Start from the exact recorded Git commit or complete release package, including binary/media/generated files and original notices. Confirm the commit/tree identity and retained payload hashes before running it. Restore the declared Python and web toolchain from the existing manifests/locks, run `python launch.py --check`, then the applicable numerical/build checks. Keep an initial failing environment receipt if restoration is incomplete. [Setup](../developer/SETUP_AND_REPRODUCIBILITY.md), [toolchain](../maintainer/TOOLCHAIN_AND_DEPENDENCY_MATRIX.md).

The documentation source snapshot is `fb42eb4d9b0c87e692710e8e867ab5190ea831a7`, tree `63c94b36fee39030b87065495d6151111d916969`. Final documentation commit/merge/deployment identities belong to the later integration records. Never substitute this source hash for a newer approved release.

## Recover local calculations

1. Identify the actual `HELIOFORGE_DB` path. Default launcher storage is `data/helioforge.sqlite3`, but a configured absolute path takes precedence.
2. Stop writers before a simple file-copy backup. SQLite WAL mode can involve sidecar files; use a consistent SQLite backup operation or a safely quiesced database, rather than assuming the main file alone is current.
3. Preserve the original backup and restore a copy into an isolated synthetic rehearsal path. Start the matching source/environment against that path.
4. Check known run IDs, their kinds, input hashes and stored results. A source digest or UUID does not prove authenticity; compare against retained original records.
5. Reconnect browser workspace references only after the matching database is restored. Record missing runs explicitly and recalculate only as a new run with a new receipt.

The store uses SQLite WAL and serialized input hashes, without an authenticated multi-user audit/signature mechanism. These recovery steps are operational guidance; a complete restore drill was not executed by this documentation review. [apps/api/helioforge/store.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/store.py), [launch.py:119–130](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/launch.py#L119-L130).

## Recover browser work

| State | Recovery path |
|---|---|
|Current workspace/setup|Export workspace JSON before clearing browser data; key `hf-workspace-v3` stores schema `helioforge.workspace.v2` |
|Supported v1 workspace|Use migration preview and confirm; retain exact previous raw bytes in `hf-workspace-import-backup-v1` |
|Unreadable cache|Export recovery text first, then explicitly confirm reset; do not erase raw evidence while diagnosing |
|Import replaced earlier cache|Preview the retained backup and restore it; the replaced cache becomes the next backup |
|Storage quota/permission failure|Keep the in-memory state and export before closing; a failed backup write cancels import |
|Saved API IDs|Restore the matching database; browser setup JSON contains references, not saved numerical result objects |
|Learning progress|Retain exported self-check/mastery record; it is self-reported practice, not credentials |
|Terminal calculation|Export its validated manifest/CSV/Markdown; import recomputes with the current Terminal contract |

Browser storage is origin-scoped, so a new domain or browser profile does not automatically inherit the old cache. Configuration imports are at most 100 KB; name/setup/pin limits still apply. Do not paste credentials or sensitive measurements into a public recovery issue. [apps/web/src/champion-core.ts](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/web/src/champion-core.ts), [apps/web/src/champion-controller.ts](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/web/src/champion-controller.ts), [apps/web/src/completion-ui.ts](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/web/src/completion-ui.ts), [apps/web/src/terminal-manifest.ts](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/web/src/terminal-manifest.ts), [docs/CLOUDFLARE.md](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/docs/CLOUDFLARE.md).

## Recover documentation and publication

Regenerate the handbook from canonical Markdown/CFF with local Pandoc, then run `--check` and review links/CSP/image fallback. Original companion script/style bytes must remain unchanged. For an existing site rollback, retain the prior successful artifact/deployment and matching header policy. The dedicated-domain guide requires restoring those together; GitHub Pages and the dedicated browser host are separate outcomes. [docs/CLOUDFLARE.md:67–83](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/docs/CLOUDFLARE.md#L67-L83), [.github/workflows/deploy-dashboard.yml](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/.github/workflows/deploy-dashboard.yml).

## Transfer packet for a new maintainer

Provide source/candidate/merge/deployment identities, complete diff and coverage dispositions, raw check logs, known failures,24 canonical outputs,59-study registry/schema map, roadmap decisions, backup locations and access ownership without revealing secrets. Explain the two numerical counterexamples before handing over result claims. Give the recipient a small reproducible lab and an isolated recovery drill with explicit success criteria; a written runbook is not itself proof that recovery succeeded.
