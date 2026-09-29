# Optional OpenAI council

The numerical application and local checklist need no AI service. Actual multi-agent mode is optional, external and potentially billable. It has **not been run against a live provider as part of this delivery**.

## Install and configure

From the repository root, with the virtual environment activated:

```bash
python -m pip install -e "apps/api[ai]"
export ENABLE_OPENAI=true
export OPENAI_API_KEY="your-own-project-api-key"
export OPENAI_MODEL="an-available-model-id-for-your-api-project"
export ADMIN_API_KEY="a-long-random-local-admin-secret"
python scripts/dev.py
```

Windows PowerShell uses `$env:NAME="value"` instead of `export NAME="value"`. Use an actual permitted API model identifier, not a subscription name. ChatGPT and API billing are managed separately; see the primary sources document. Do not paste secrets into repository files, chat logs, screenshots or prompts.

Select **OpenAI** in Agent council, enter the local admin key and explicitly consent to sending the research brief and synthetic evidence. The server refuses external execution unless all gates pass. Keep the application bound to loopback. Configure a provider-side project spending limit; output-token and turn limits are not a monetary budget.

`.env.example` is a template only. `scripts/dev.py` does not automatically load it: export variables in the shell or configure them in your container/orchestrator. The default Compose configuration disables AI.

## Actual execution structure

Eight `Agent` instances run through `asyncio.gather`: storage engineering, investment analysis, market evidence, sustainability, hybrid architecture, learning design, accessibility and reproducibility. Their Pydantic-structured findings feed a ninth, independent critic. Each specialist is limited to two turns and 1,800 output tokens; the critic to two turns and 2,200 output tokens. The workflow has a 120-second timeout and a per-process concurrency gate. No external tools are given to these agents. SDK tracing is disabled.

The selected model must support the structured-output workflow and compatible token settings. Provider or schema incompatibility is surfaced as an error, not silently replaced with a canned “AI” answer. The optional dependency is pinned to the documented package version in `pyproject.toml`; live compatibility must still be verified in the user's project.

## Privacy and authority

The brief and supplied evidence are transmitted to OpenAI only after opt-in. The API key stays server-side. The local admin key is not stored in browser storage; it is still visible to that local browser process while entered. Completed output is stored in local SQLite.

The council reviews default synthetic storage, finance and carbon evidence for its selected market, plus an explicitly selected saved hybrid run when attached. That hybrid run includes its actual validated inputs, input hash and numerical summary; it is never silently replaced by the default configuration. Edited storage, finance and PV views are not silently submitted. Agents do not browse regulations, read private documents, trade, change site controls or provide approval. Their outputs are untrusted text, escaped in the UI and subject to human review. Treat source documents and briefs as untrusted data, not executable instructions.

## Required live-provider acceptance test

Run a small nonconfidential brief with a tightly limited project budget. Confirm eight actual specialist results and the independent critic decision, structured schemas, selected model, timeout behaviour, failure handling and usage in the provider dashboard. Verify that no trace or prompt includes confidential deal data. Record the package/model versions and result date. Do not announce a successful integration based only on mocked tests.
