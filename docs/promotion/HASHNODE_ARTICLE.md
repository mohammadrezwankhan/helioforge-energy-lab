# Tracing a HelioForge Energy Lab demo result back to source

Interactive hybrid-energy research and learning workbench with auditable numerical screens and a local Python API.

## The engineering problem

For energy researchers and engineering educators, a screen is useful only when its displayed result can be traced to a rule and a source. In this project the supplied records and examples are synthetic. That choice makes exploration possible without pretending a provider is connected or a current fact is verified.

## Follow the implementation

- `apps/api/helioforge/`
- `apps/web/src/`

Begin at the first source entry, identify one visible output, then follow the calculation or state transition to its fixture. Change one synthetic input and rerun the smallest relevant check. The architecture document shows the delivered demo path rather than an imagined production stack.

## A deliberate boundary

Local state is useful for trying a workflow; it is not proof of remote receipt, clinical safety, official guidance or multi-user synchronization. The interface's demo language is part of the contract. Preserve unknown/stale states rather than filling them with a plausible answer.

## Reproduce it

```sh
git clone https://github.com/mohammadrezwankhan/helioforge-energy-lab.git
cd helioforge-energy-lab
node scripts/preview-demo.mjs
```

The current quality report separates executed checks from historical reports and unavailable environments. It also identifies remaining release blockers; no performance improvement is inferred from a new screenshot.

## What would improve it

Review one native-origin persistence journey, one keyboard interaction, or one bilingual explanation using the contribution guide. Bring a small reproduction and a specific invariant. Repository: https://github.com/mohammadrezwankhan/helioforge-energy-lab.

Draft article, not published. Technical evidence must be refreshed at the release commit before external publication.
