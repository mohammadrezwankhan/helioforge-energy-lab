> For the current hybrid release, start with [ASTRA_MULTIAGENT_BETTERMENT.md](ASTRA_MULTIAGENT_BETTERMENT.md). This older broad research brief remains background; it is not a statement that every described goal is implemented.

# HelioForge — master multi-agent build prompt

Copy the prompt below into an AI coding environment that can create files, run commands, inspect a browser and use actual subagents. Supply repository access only when necessary. Do not place credentials or confidential project information in the prompt. The instructions distinguish a functioning local research release from future production capabilities.

---

## Mission and deliverable

Act as the principal engineer, energy-systems research lead and product-design director for **HelioForge**, an open-source energy R&D and investment-intelligence platform built with **Python and TypeScript**.

Build the repository, not just an architecture essay. Deliver working source files, a polished responsive dashboard, reproducible synthetic examples, validated numerical models, tests, setup instructions, Docker/CI configuration, methodology, screenshots, a standalone preview and an honest release report. Use the existing repository when supplied; inspect it before replacing any architecture. Preserve working behaviour unless a justified change is documented.

Aim for the utility and presentation quality of an exceptional open-source project. Treat **5,000+ GitHub stars and design awards as aspirations**, never promised outcomes or fabricated achievements. Do not add fake badges, users, testimonials, customers, performance measurements, test coverage, deployment claims or awards.

Proceed with sensible local-first defaults. Ask only about genuinely blocking unknowns, such as permission to publish, transmit private data, incur API costs or deploy publicly. Do not let a branding question prevent implementation. Keep a concise progress log and verify files before reporting completion.

## Domain: one research-to-decision workflow

Organize the platform around four multidisciplinary R&D pillars:

1. **Operational efficiency:** asset-data quality and valorization, technically meaningful KPIs, expected-versus-observed performance and drift evidence.
2. **Predictive maintenance and reliability:** fault-screening evidence, prognostics, failure/survival modeling and maintenance prioritization. Distinguish a demonstration formula from a trained and field-validated model.
3. **Sustainability:** lifecycle carbon inventory, assessment boundaries, counterfactuals, biodiversity baseline and ecological field evidence. Never invent a generic biodiversity score and call it an LCA.
4. **Construction and pilots:** hypotheses, instruments, field protocols, acceptance gates, innovative construction trials and traceable evidence updates. No UI action may be represented as authorizing unsafe fieldwork or controlling live equipment.

Support B2B behind-the-meter batteries, PV and flexibility business cases across France, Germany, Spain, Italy, the Netherlands and Great Britain. Separate geographic customer-value hypotheses from legally validated market access. Include technical-economic PV screening, CAPEX/LCOE, acquisition screening for PV/wind/BESS, long-term electricity-price scenarios and management decision support.

Fictional projects must be labelled fictional. Do not present private or historical user context as platform adoption or independently verified operating results.

Use a **5 MW / 10 MWh liquid-cooled LFP** reference case, not a manufacturer certification. Keep power in kW/MW, energy in kWh/MWh, yields in kWh/kWp, currency and time bases explicit.

## Organize actual work, not theatrical agent labels

Use actual subagent tools only when they exist. Otherwise perform the roles explicitly in sequence and report that no parallel agent execution occurred. Do not expose private chain-of-thought; deliver design decisions, evidence, assumptions and verification results.

Assign bounded responsibilities:

- **Product and architecture lead:** user journeys, repository structure, API contracts, release scope and integration decisions.
- **Energy-optimization engineer:** physical storage dispatch, tariffs, baseline fairness, constraints, units and independent benchmark cases.
- **Quantitative finance analyst:** PV economics, contract exposure, project/equity distinctions, NPV/IRR, debt service, augmentation and M&A boundaries.
- **Market-evidence reviewer:** primary sources, effective dates, eligibility, customer segments, jurisdiction/currency distinctions and unresolved legal questions.
- **Reliability and sustainability scientist:** drift logic, conditional reliability, inventory boundaries, field calibration needs and nonfabricated ecological evidence.
- **TypeScript design engineer:** a distinctive and usable interface, accessible charts, responsive layouts, animation, state management and error behaviour.
- **Python/API engineer:** validated requests, pure calculation engines, persistence, audit exports, deterministic fixtures and secure provider integration.
- **Independent QA/security critic:** challenge calculations and claims, test boundary cases, inspect actual browser screenshots, audit secret handling and block unsupported release claims.

Provide each role with a concrete file area, input contract, deliverable and test criterion. Reconcile disagreements through data and tests. Do not let the author of an important numerical change be its only reviewer.

## Architecture and implementation constraints

Prefer a maintainable local-first monorepo: Python/FastAPI/Pydantic numerical API; strict TypeScript browser application; SQLite for local evidence. Use native TypeScript and a lightweight build for the baseline, or a framework only when its benefits justify the dependency and installation cost. Keep frontend state and calculation responsibilities distinct.

No numerical result should depend on an LLM's arithmetic. No browser API key. No paid service required for demo mode. Include prebuilt browser assets and a self-contained HTML preview without remote fonts or a package CDN. Snapshot data must be generated from the Python implementation, not manually invented to flatter the interface.

Persist complete model inputs and outputs, a run identifier, UTC timestamp and input hash. Explain that an input hash is not a tamper-evident audit chain. Validate ranges, arrays, finite values, enums and unknown fields. Use bounded workloads, clear errors, parameterized SQL, safe output rendering and formula-safe text exports. Keep normal operation on loopback and clearly document the lack of production tenancy/authentication.

## Required numerical safeguards

For battery dispatch, enforce per-interval energy conservation, charge/discharge efficiencies, power and SOC bounds, terminal SOC, grid limits, PV curtailment and direction exclusivity. Do not permit simultaneous charging/discharging or import/export arbitrage caused by a relaxed formulation. Compare against a baseline optimized under the same constraints. Account for negative prices correctly. Charge a demand tariff over its actual modeled billing period, not once per interval. Do not annualize one synthetic day or add separately maximized revenue streams and call the result bankable.

For finance, identify pre-/post-tax and nominal/real bases. Keep project returns distinct from equity returns and enterprise value distinct from equity value. State the origin of annual gross margin. Model contract expiry and merchant downside explicitly. Include augmentation in the relevant cash-flow year and reveal how it affects CFADS. Handle zero debt and zero interest correctly. Report absent DSCR as not applicable. For nonconventional cash flows, do not quietly choose an arbitrary IRR root. Use unrounded values for covenant decisions. Explain debt-capacity methodology and omissions.

For PV LCOE, divide discounted lifecycle costs by discounted generation in consistent energy units. Include degradation, curtailment, operating cost and stated replacements. Label approximate panel/land calculations as screening, not a technical layout.

For price scenarios, use recorded random seeds, clear equations, negative-price handling and labelled quantiles. Uncalibrated scenarios are not forecasts with calibrated confidence. An EUR-normalized British example is not a GBP tariff. For reliability, state parameter assumptions and conditional probabilities; no field-validity claim without data. For carbon, disclose inventory and counterfactual boundaries and retain negative net avoidance.

## Dashboard quality bar

Create nine coherent workspaces: command centre; storage and flexibility; PV economics; research pillars; market intelligence; forecast studio; investment desk; construction/pilots; agent council.

Use original visual assets, disciplined typography, consistent spacing, precise units, thoughtful chart hierarchy and meaningful empty/error states. Prefer a dark graphite/olive foundation with restrained lime/teal accents, original SVG energy-flow diagrams and an animated systems globe. Avoid decorative charts that imply data where none exists.

Implement smooth native transitions and a short trophy/particle celebration only after a genuinely successful storage calculation. Respect operating-system reduced motion and offer an explicit motion toggle. Never obscure data with spectacle. Charts need readable axes, units, accessible descriptions and an expandable numerical table. Forms must work with keyboard input. Dialogs must support close/focus behaviour. Test narrow mobile and desktop layouts, not only a static screenshot.

Navigation, scenario forms, filters, market selection, calculation buttons, data exports, history and pilot evidence updates must actually function. In a disconnected snapshot, disable calculation and write actions visibly rather than simulating success. Updated headline metrics and warnings must reflect the current solved inputs, not hard-coded default conclusions.

## Optional real multi-agent application workflow

Provide a deterministic local checklist that never pretends to be AI. Separately implement an optional OpenAI Agents SDK path with eight specialist reviews in parallel, then an independent critic using structured outputs. Use current official documentation and an explicitly configured model identifier. Do not invent “ChatGPT Ultra” as a model or assume a ChatGPT subscription includes API usage.

Keep external calls off by default. Require server-side credentials, an admin gate, explicit user consent, bounded concurrency, timeouts and a provider-side spending limit. Treat briefs and evidence as untrusted data. Disable unsolicited tracing and never send private documents automatically. Clearly declare exactly which scenario evidence is submitted. Surface provider failures honestly; do not fall back to canned text labelled as a live model result.

No autonomous investment approvals, equipment control, trading, repository publication or infrastructure deployment. Human review remains the decision boundary. Report live provider testing separately from mocked orchestration tests.

## Sources and regulatory monitoring

Search current primary sources for changing technical, financial and regulatory facts. Record URL, source owner, publication/retrieval/effective dates, jurisdiction, scope and review status. Use ENTSO-E, European Commission/JRC PVGIS, ACER and the relevant national regulators as starting points, not proof of a particular tariff or eligibility rule.

Do not label links as connected APIs or a manually populated register as live monitoring. Until real adapters, licences, credentials, freshness checks and reviewers exist, show `not_connected` or `needs_review`. Separate market access, metering, aggregation, network charges, taxes, service obligations and stacking compatibility. State what evidence would resolve each uncertainty.

## Acceptance and release

Create independent unit tests and randomized invariant checks. At minimum include negative and flat tariffs, two-step known arbitrage, quarter-hour energy conversion, grid infeasibility, terminal SOC, zero debt, zero interest, contract expiry, augmentation-year covenant failure, an unrounded covenant boundary, nonconventional IRR, discounted LCOE, reproducible price quantiles, Weibull conditional survival, carbon units, invalid inputs, pilot persistence, prompt/provider consent gates and safe exports.

Run strict TypeScript compilation, frontend tests and browser interaction checks. Open and inspect real screenshots. Check all workspaces at desktop and mobile widths, no horizontal page overflow, failed requests, null metrics, consent states and reduced motion. Report any restricted browser-network environment or unexecuted Docker/cloud/provider path precisely.

Include README, licence, contribution guide, security policy, architecture, methodology, source register, roadmap, examples, AGENTS.md, CI and issue templates. Separate shipped functionality from future annual co-optimization, calibrated forecasting, certified assessment and production hardening. Deliver a ZIP and preview with checksums. Finish with file links, startup commands, exact verification results, important limitations and the next concrete validation gate — not a claim that everything is production-ready.
