# Portfolio integration boundary

HelioForge contributes a public synthetic energy/finance workbench with explicit model, unit, provenance and verification boundaries. Its useful cross-project contracts are general: comparable inputs and service, complete result metadata, traceable source/data identity, readable limits and reproducible bounded examples. This chapter makes no claim about unrelated repositories, private work or organization-wide completion.

## Safe reusable concepts

| Concept | What may be shared | Boundary to preserve |
|---|---|---|
|Energy balance|kW/kWh/h conventions, explicit charge/discharge losses and inventory endpoints|A different engine/profile/objective is a different model |
|Financial screening|NPV/project/equity/CFADS distinctions and undefined DSCR/IRR semantics|No inferred legal/tax jurisdiction or investment approval |
|Result provenance|Source/data/input digests, model/schema versions, units and limitations|A content digest does not authenticate a person or prove factual accuracy |
|Research registry|ID→schema→handler→example→limits mapping|59 current studies are individually bounded, not a generic full-physics simulator |
|Recovery|Separate browser configurations, run references and database backups|Origin/cache/DB identity and migration rules remain application-specific |
|Verification|Source CI, current command evidence, independent QA and live publication as separate records|No borrowing another project's green check or private finding to support public claims |

Sources: [apps/api/helioforge/provenance.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/provenance.py), [apps/api/helioforge/studies.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/studies.py), [apps/web/src/result-provenance.ts](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/web/src/result-provenance.ts), [apps/web/src/champion-core.ts](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/web/src/champion-core.ts), [apps/api/helioforge/store.py](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/api/helioforge/store.py).

## Existing publication and traceability

The repository retains its established documentation site and dedicated browser publication configuration. The existing traceability workflow can publish a configured source observation; it is not proof that a hosted artifact was rebuilt or deployed. Preserve complete-site deployment boundaries and verify the actual source/runtime manifest before announcing a live update. [.github/workflows/mklab-traceability-sync.yml](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/.github/workflows/mklab-traceability-sync.yml), [docs/CLOUDFLARE.md](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/docs/CLOUDFLARE.md), [apps/web/src/release-provenance.ts](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/fb42eb4d9b0c87e692710e8e867ab5190ea831a7/apps/web/src/release-provenance.ts).

## Public summary discipline

A public portfolio summary may say that the reviewed source includes a bounded browser Terminal, local Python models,59 registered studies and source-linked reproducibility documentation. Pair any local test count with its date/revision and scope. Keep the 19 runnable/17 study-only architecture split, known comparator/IRR limitations and absent real-world/provider validation visible where relevant. Do not report the documentation candidate as merged or published until its own exact records establish that outcome.
