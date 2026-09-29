# Champion design and journey notes

## Brief and constraints

Audience assumptions: researchers, teachers and engineering students exploring synthetic hybrid-energy configurations on a personal computer. These are inferred from the app's existing capabilities, not new stakeholder interviews. Primary success is an inspectable baseline/stress comparison with intact inputs and clear model boundaries. New human-user evidence has not been collected.

The original dark energy-lab identity and low-poly software-3D scene are preserved. Ink/navy surfaces, mint emphasis and technology-specific named labels emphasize configuration → result → evidence. Shared additions are centralized in `champion.css`; no font downloads, stock-image services or new runtime JavaScript dependencies were introduced. Existing MIT source and original geometry/icons are retained; the new code/styles use that project license. There are no claimed awards or borrowed commercial interface assets.

## Before / after

| Journey | Earlier friction | Implemented sequence | Recovery / acceptance |
|---|---|---|---|
| Find a model | Navigate between architecture/lesson lists | Ctrl/Cmd+K → type → arrows → Enter | No-results state; Escape closes; study-only mode remains visible |
| Begin a comparison | User had to infer a useful first experiment | Quick start → hospital reference → calculate → pin → outage → calculate → compare | API-offline guidance; no fabricated result |
| Keep a useful setup | Export-only/manual reconstruction | Saved setups → name validated inputs → save → reopen | Max 20; export; memory-only notice if storage fails |
| Revisit a solved run | Inspect exported JSON | History → filter → Open run | Retrieve actual API record; validate; retain newer input intent; missing-run error |
| Return after restart | Tab state lost | Recover last valid inputs → retrieve prior result and pinned IDs | Corrupt cache retained until explicit recovery reset; absent API data reported |
| Type invalid values | Old metrics stayed visible until blur | Immediate input validation → hide stale output → correction → run | Raw draft survives navigation; unsafe export refused |
| Navigate while editing | Generic inputs returned to last defaults | Keep safe in-memory draft → annotate displayed old result | Passwords/consent excluded; reload persistence not claimed |
| Reconnect | Completed results were replaced by defaults | Same-market reconnect → refresh connectivity/pilots → retain calculations | Deliberate market change loads that market's defaults |

## States and accessibility

Controls have hover, visible focus, selected, disabled and loading states. Input errors suppress invalid result presentation. Empty histories/shelves and search results have actionable text. Save failures state memory-only status. Deletion and damaged-cache reset require explicit confirmation. Offline state disables new Python calculations. Response loss after a write is reported as ambiguous, directing users to history before a retry.

Mobile navigation makes background content inert while open and the hidden sidebar inert while closed; Escape returns focus. Shared tokens control transitions, with a user toggle and system reduced-motion support. Non-color text conveys study-only, synthetic, busy, saved and memory-only status. Keyboard tests and emulated widths are evidence of those specific behaviours, not full WCAG conformance. Human UAT, screen readers and native-device coverage remain outstanding.

## Deliberate limits

There is no wholesale framework migration, new cloud database, sign-in screen, pretend collaboration, new numerical physics or generalized multi-carrier solver. Workspace export is inspectable backup; individual setup exports are the supported import path. Comparisons are limited to three runs. Generic model drafts survive navigation within the tab, not tab closure. The interface does not award engineering approval or rank a cheaper, less-served scenario as automatically better.
