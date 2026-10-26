# Terminal redesign handoff

## Direction

The application uses Hallmark Terminal: a green-cast near-black ground, three green surface levels, phosphor ink, one bright green signal, square corners and 1px rules. Martian Mono is the display and body face. Data uses tabular numerals and slashed zero. The interface keeps the original navigation, routes, actions, fields, accessible names, test hooks, charts and energy-scene canvas.

The stylesheet removes the gradient, glow, shadow and nested-card treatment from the authored interface. It keeps the actual charts and interactive 3D canvas as analytical content. Inputs and action targets are at least 44px high; small labels have a 12px floor, and explanatory body copy uses 15px type. The shell and tables have internal scroll where their content is wider than the viewport.

## Screen compositions

| Screen | Composition |
| --- | --- |
| Overview | Asymmetric research statement and original energy illustration, followed by rule-separated indicators, an analysis/focus split, and the project table. |
| Hybrid systems | The interactive energy scene takes the wider column; configuration occupies the narrower column. Scenario selection, run results and the architecture atlas follow as separate work areas. |
| Learning studio | Progress sits beside the lesson introduction. The lesson index forms a scrollable rail beside lesson content, quiz and evidence links. |
| Scenario compare | Completed runs remain in a horizontal table with a sticky metric column and local horizontal scrolling. Empty-state guidance stays visible. |
| Storage | The model form uses the narrow column; dispatch output and the SOC chart use the wider column. |
| PV economics | Four screening indicators lead into editable assumptions and the generation chart; the diligence note remains below. |
| Research | The four research pillars form one ruled strip, followed by the drift chart and reliability/carbon forms. |
| Market intelligence | Market evidence is arranged as two-column records, followed by a source register. Narrow viewports stack the records. |
| Forecast studio | Scenario controls use the narrow column; quantiles and the seeded price plot use the wider column. |
| Investment desk | Finance indicators precede the project-finance form and DSCR plot; acquisition inputs and valuation output remain paired below. |
| Construction and pilots | The board keeps four independent stage columns in an internally scrollable strip; pilot records use row treatment. |
| Agent council | The review controls and committee output retain their split; role evidence is arranged in two text columns. |
| Parametric workbench | Candidate inputs and completed results use an asymmetric split. Diagnostics, A/B comparison and sweep matrix remain separate ruled sections. |

## Implementation

- `apps/web/src/tokens.css` owns color and font tokens, plus aliases for the legacy palette names.
- `apps/web/src/terminal.css` contains the shared frame, route layouts, responsive rules and parametric-workbench classes.
- The existing stylesheets have been normalized to token-based colors and the shared font; they retain legacy layout rules for the final Terminal layer to override.
- `apps/web/index.html` loads Martian Mono and provides a clearer no-script explanation.

The browser build loads `tokens.css` before the existing CSS and `terminal.css` last. `terminal.css` is the final cascade layer by design. The font link uses Google Fonts, so users without network access receive the declared monospace fallback.

## Verification status

The orchestrator inspected rendered desktop/mobile and sweep captures and corrected nested workbench columns, inherited rounded controls, field edges and compact navigation. Executed measurements and remaining tooling observations are in VERIFICATION.md and HALLMARK_SCORECARD.md. No screen-reader or independent WCAG certification is claimed.
