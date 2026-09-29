# Contributing

Contributions should make a model easier to verify, a decision harder to misread, or an interface easier to use.

Discuss new regulated-data integrations and financial-model changes in an issue before implementation. Include source provenance, customer eligibility boundaries and numerical assumptions. Share only synthetic or explicitly licensed data; remove client names and meter identifiers.

Use small pull requests. Explain the problem, implementation, alternatives and model-boundary changes. Add a hand-checkable regression for numerical changes, API validation tests for new fields, and mobile/keyboard checks for interface changes. Regenerate the snapshot and browser assets when their sources change. Record exact tests run; do not say “all tests pass” when only a subset ran.

```bash
python -m pip install -e "apps/api[dev]"
python -m pytest apps/api/tests
cd apps/web && npm ci && npm run build && npm test
```

Run `python scripts/generate-snapshot.py` from the root after intentional default/model changes, then rebuild the frontend. Inspect changes to generated data and screenshots; never silently update a benchmark to hide a bug.

LLM-generated contributions require human ownership, provenance review and the same tests as any other contribution. Do not request or publish private chain-of-thought; concise design rationale, equations, evidence and test results are the relevant record. Read AGENTS.md for assistant-specific constraints.

## Hybrid and lesson contributions

Use [LESSON_AUTHORING](docs/LESSON_AUTHORING.md) and the hybrid-model issue template. Edit the canonical packaged catalogue, regenerate browser/matrix assets and add a hand-verifiable case. Every architecture needs an explicit numerical/study capability. Test all applicable pairs and the setup import contract. Reference-source figures must not be copied without permission. The root runtime `/data/` store must never be committed.
