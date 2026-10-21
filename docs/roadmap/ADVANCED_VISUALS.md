# Advanced study visuals

`HF.advancedStudyVisual(def: StudyDefinition, result: StudyResult, slice: number): string | null` supplies geometry-specific SVG for four roadmap study IDs: `hybrid-powerflow`, `markets-network`, `pv-raytrace`, and `pilots-registration`. It returns `null` for every other study so the established study renderer can continue to handle those views. The current renderers are static and use the result and input contract already bundled for the study; they do not start a timer, fetch data, or run calculations.

## Data used by each view

- **Hybrid power flow:** `details.buses[].voltage_pu` and `details.branches[].from_p_mw` / `loss_p_mw`. The topology is placed on a schematic circle because the model supplies no bus coordinates. The colored backdrop uses a bounded inverse-distance interpolation of the solved bus voltage samples over that schematic. It is visual interpolation only: it is neither a solved voltage spatial field nor a geographic map.
- **Six-zone market network:** `table[].zone`, `nodal_price_eur_mwh`, and `net_import_mw`, plus `details.line_flows[]` (`from_zone`, `to_zone`, signed `flow_mw`, and `limit_mw`). The six-node ring is a topology diagram, not a map. Arrow direction and width use the signed model flow; line labels retain the MW values.
- **PV ray trace:** input `panel_samples`, `sun_vectors`, and `occluder_triangles`, combined with result-table `shaded` and `energy_wh` records indexed by `panel_index` and `sun_index`. Panel markers show the returned shade count for the plotted samples; directional rays show the result rows for the first panel. Coordinates are projected from the supplied XYZ data. Rays and normal indicators are length-scaled for legibility; their drawn lengths do not represent measured distance. No obstacle triangle is marked as the intersection unless the result schema identifies it (it currently does not).
- **Pilot registration:** input `design_points_xyz` and `survey_points_xyz` transformed with the returned `details.rotation_matrix` and `translation_m`, plus the actual correspondence indices and `retained_inlier` flags in the result table. The relative XYZ view has no georeferencing. It does not claim photo reconstruction or survey accuracy.

Every figure exposes an SVG title and description and repeats a visible data-kind label. The generated catalogue's `synthetic_or_user_supplied_unverified` label remains visible as “Synthetic or user-supplied data · unverified.” Missing arrays or non-finite values are shown as missing; no fabricated coordinates, values, or sample results are filled in. The geometry displays are bounded: the power-flow graph uses at most 24 buses, market network at most six zones and 100 line rows, PV geometry draws at most 20 triangles / 10 panels / 10 sun directions (100 plotted geometry points at most), and registration draws at most 50 design and 50 survey points.

## Integration and build

The existing `studyVisual` dispatch now calls `HF.advancedStudyVisual(def, result, slice)` first and preserves its fallback for other studies. TypeScript and CSS are included in the canonical build and generated standalone preview. Contract tests and `scripts/browser-completion.py` check all four integrated visuals; generated artifacts are not hand-edited.

Run the focused contract tests with:

```powershell
cd apps/web
node --test tests/advanced-visuals.test.mjs
```

Then run the regular strict typecheck, build, and web tests. The focused tests compile the new TypeScript and use the bundled Python-produced study results to verify the data projections, accessible markup, missing-value behavior, bounds and escaping.

## Manual/browser proof

After wiring and rebuilding, run `npm run build` and `npm test` from `apps/web`, then open the generated preview in a browser. Check all four studies at desktop width and at 390 px: SVG titles/descriptions and visible captions should be present; synthetic status should remain visible; network layouts should read as schematic rather than geographic; absent PV terrain should remain absent; and registration should show design points, transformed survey points and inlier/excluded correspondence styling. With system reduced motion enabled and with the app motion control set to off, conductor particles should remain static. Keyboard inspection should reach the surrounding study controls without requiring pointer hover; verify text/captions provide the same essential context as color and motion.

These graphics do not add model validation. Their inputs remain research screens with synthetic or user-supplied unverified data; they do not establish engineering certification, scientific validation, market observations, geographic placement, survey certification, or identity certification.
