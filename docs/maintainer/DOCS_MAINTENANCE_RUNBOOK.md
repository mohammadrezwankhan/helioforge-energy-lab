# Documentation maintenance runbook

## Source of truth

Canonical Markdown lives under `docs/developer`, `docs/math-and-physics`, `docs/maintainer` and `docs/owner`, with root entry files and the complete study atlas. `docs/reference/index.html` is a generated reading view; edit its canonical inputs and regenerate. Its fixed `chapters.json` selects documents, source revision and navigation groups. The renderer uses Python and local Pandoc with MathML output, no network-loaded fonts/scripts/math assets and no application execution.

```sh
python docs/reference/build_reference.py
python docs/reference/build_reference.py --check
```

The default command generates HTML; `--check` compares the exact generated HTML without writing. Inherited `-h` / `--help` displays usage and exits before rendering. The separate worked-example helper uses a positional output directory and does not implement argparse help. See the [CLI inventory](../developer/API_CLI_AND_INTERFACES.md) for all 27 source-parser help groups and both documentation helpers. The embedded input manifest includes hashes of every canonical chapter, chapter manifest, renderer and stylesheet plus the Pandoc version. A renderer/tool-version change can require an intentional regenerated HTML diff. Preserve complete failures and source identities in external review receipts.

## Update when an implementation changes

For a numerical change, update equations, units, defaults, endpoint rules, convergence/tolerance statements and the affected atlas/schema rows. Re-run the smallest relevant worked example plus applicable existing checks. Keep source-linked claims pinned to the reviewed commit; do not substitute a moving branch URL where a precise implementation claim needs identity. When a catalogue changes, reconcile all registered IDs, inputs, example provenance and limits before changing a count. [apps/api/helioforge/studies.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/studies.py), [scripts/check-study-assets.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/scripts/check-study-assets.py), [scripts/check-hybrid-assets.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/scripts/check-hybrid-assets.py).

For an interface change, update HTTP routes, CLI flags, schema versions, import size/type rules, storage keys, error semantics and recovery instructions. Preserve stale-response guards and explicit trust boundaries in the explanation. For a provider or release change, state actual observed status and date separately from configured capability. [apps/api/helioforge/main.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/main.py), [apps/web/src/champion-controller.ts](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/web/src/champion-controller.ts), [apps/web/src/terminal-manifest.ts](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/web/src/terminal-manifest.ts).

## Rendering and link rules

Use headings, paragraphs, accessible tables and descriptive links. MathML comes from the canonical TeX equations; code/Mermaid fences remain readable source where no local diagram renderer is supplied. A chart must name units, input provenance and method limits. Tables scroll within a labeled focusable region on narrow screens. Keep all essential information readable without scripting.

The renderer rejects active chapter elements and event attributes, strips inline presentation and namespaces anchors. External/unpublished images become readable source links or alternative text; an image already inside a link must not create a nested anchor. Existing canonical image bytes are preserved. Do not weaken CSP to make a remote badge load. For directory links, keep a local published route only when its directory has a real `index.html`; otherwise link to the immutable source repository tree. File existence alone does not establish a published directory landing page. Test the missing-index remediation directory and the published `docs/portfolio` directory alongside standalone/linked image fallbacks, escaping, traversal/unsafe schemes, duplicate anchors and exact freshness. Preserve the root README and existing application navigation when regenerating the handbook.

## Review and freeze

Check all 24 requested canonical outputs and any additional atlas/example/handbook files. Compare the complete source and candidate trees to ensure only authorized documentation paths changed. Validate CFF and link/fragment resolution; distinguish historical source references from candidate-local targets. Review public text for unrelated/private identities and data. Freeze the exact candidate/report/diff identities before independent QA. Later fixes get a preserved previous package and a new identity; remote commit/merge/publication remains the integration owner's separately recorded responsibility.

No automatic schedule or new CI workflow is created here. Use the roadmap's monthly checkpoints and existing contributor review process; do not silently broaden executable checks, permissions or deployment routes for a documentation refresh.
