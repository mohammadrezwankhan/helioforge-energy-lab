# Hybrid coverage matrix

36 curated architectures, not every physically possible hybrid. Screening and study-only capabilities are explicitly separated.

## Architecture catalogue

| ID | Architecture | Family / topology | Coupling / reference | Numerical capability |
|---|---|---|---|---|
| `remote-triad` | Remote renewable microgrid | Microgrids / Off-grid | AC / GFM | Hourly AC-equivalent screen |
| `utility-pv-ac` | Utility solar + storage · AC | Solar / FTM | AC / GFL | Hourly AC-equivalent screen |
| `utility-pv-dc` | Utility solar + storage · DC | Solar / FTM | DC / GFL | Hourly AC-equivalent screen |
| `industrial-btm` | Industrial solar + storage | Solar / BTM | AC / GFL | Hourly AC-equivalent screen |
| `wind-firming` | Wind + battery firming | Wind / FTM | AC / GFL | Hourly AC-equivalent screen |
| `hospital-island` | Hospital islanding microgrid | Microgrids / Islandable | AC / Dual | Hourly AC-equivalent screen |
| `home-resilience` | Home solar + battery | Solar / Islandable | AC / Dual | Hourly AC-equivalent screen |
| `community-energy` | Community energy hub | Solar / BTM | AC / GFL | Hourly AC-equivalent screen |
| `telecom-dc` | Off-grid DC telecom station | Microgrids / Off-grid | DC / GFM | Hourly AC-equivalent screen |
| `solar-diesel` | Solar + diesel + battery | Microgrids / Off-grid | AC / Synchronous | Hourly AC-equivalent screen |
| `wind-diesel` | Wind + diesel + battery | Microgrids / Off-grid | AC / Synchronous | Hourly AC-equivalent screen |
| `hydro-triad` | Solar + wind + small hydro | Hydro / Off-grid | AC / Synchronous | Hourly AC-equivalent screen |
| `hydro-battery` | Run-of-river + battery | Hydro / FTM | AC / Synchronous | Hourly AC-equivalent screen |
| `floating-solar` | Floating solar + hydro + battery | Hydro / FTM | AC / Synchronous | Hourly AC-equivalent screen |
| `biomass-chp` | Biomass CHP + solar + battery | Thermal / BTM | Multi-carrier / Synchronous | Study only; dedicated model needed |
| `geothermal-hub` | Geothermal + solar energy hub | Thermal / FTM | Multi-carrier / Synchronous | Study only; dedicated model needed |
| `solar-hydrogen` | Solar + hydrogen + battery | Hydrogen / Off-grid | Multi-carrier / GFM | Study only; dedicated model needed |
| `wind-hydrogen` | Wind + hydrogen export hub | Hydrogen / FTM | Multi-carrier / GFL | Study only; dedicated model needed |
| `csp-storage` | Concentrated solar + thermal storage | Thermal / FTM | Multi-carrier / Synchronous | Study only; dedicated model needed |
| `heatpump-hub` | PV + heat pump + thermal store | Thermal / BTM | Multi-carrier / GFL | Study only; dedicated model needed |
| `district-chp` | District CHP + thermal storage | Thermal / BTM | Multi-carrier / Synchronous | Study only; dedicated model needed |
| `ev-depot` | Solar + battery EV depot | Mobility / BTM | AC / GFL | Hourly AC-equivalent screen |
| `v2g-fleet` | Bidirectional fleet + solar | Mobility / BTM | AC / Dual | Study only; dedicated model needed |
| `port-microgrid` | Port shore-power microgrid | Mobility / Islandable | AC / Dual | Hourly AC-equivalent screen |
| `data-centre` | Data-centre hybrid backup | Microgrids / Islandable | AC / Dual | Hourly AC-equivalent screen |
| `agrivoltaics` | Agrivoltaics + irrigation storage | Solar / BTM | AC / GFL | Hourly AC-equivalent screen |
| `desalination` | Renewable desalination microgrid | Microgrids / Off-grid | AC / GFM | Hourly AC-equivalent screen |
| `pumped-hydro` | Wind + PV + pumped storage | Hydro / FTM | AC / Synchronous | Study only; dedicated model needed |
| `flywheel-hybrid` | Battery + flywheel microgrid | Advanced / Islandable | AC / Dual | Study only; dedicated model needed |
| `supercapacitor` | PV + battery + supercapacitor | Advanced / Off-grid | DC / GFM | Study only; dedicated model needed |
| `marine-hybrid` | Tidal + wave + battery | Advanced / Off-grid | AC / GFM | Study only; dedicated model needed |
| `offshore-island` | Offshore wind + hydrogen island | Hydrogen / FTM | Multi-carrier / GFM | Study only; dedicated model needed |
| `nuclear-hydrogen` | Nuclear + hydrogen + heat | Hydrogen / FTM | Multi-carrier / Synchronous | Study only; dedicated model needed |
| `waste-energy` | Waste-to-energy district hub | Thermal / BTM | Multi-carrier / Synchronous | Study only; dedicated model needed |
| `virtual-plant` | Virtual power plant portfolio | Networks / Virtual | AC / GFL | Study only; dedicated model needed |
| `networked-microgrids` | Networked community microgrids | Networks / Networked | AC / Dual | Study only; dedicated model needed |

## Scenario catalogue

| ID | Scenario | Mode | Explicit modifiers |
|---|---|---|---|
| `baseline` | Reference day | screening | `{}` |
| `cloud-cover` | Cloud cover | screening | `{"solar_factor":0.25}` |
| `wind-lull` | Wind lull | screening | `{"wind_factor":0.15}` |
| `renewable-drought` | Renewable drought | screening | `{"solar_factor":0.15,"wind_factor":0.12}` |
| `heatwave` | Heatwave demand | screening | `{"load_factor":1.4,"solar_factor":0.9}` |
| `winter-peak` | Winter peak | screening | `{"load_factor":1.3,"solar_factor":0.35}` |
| `load-step` | Evening load step | screening | `{"step_factor":1.6}` |
| `outage-4h` | Four-hour outage | screening | `{"outage_start":17,"outage_hours":4}` |
| `outage-24h` | 24-hour outage | screening | `{"outage_start":0,"outage_hours":24}` |
| `outage-72h` | 72-hour outage | screening | `{"outage_start":0,"outage_hours":72,"hours":72}` |
| `black-start` | Black-start sequence | study | `{}` |
| `reconnection` | Grid reconnection | study | `{}` |
| `weak-grid` | Weak-grid stability | study | `{}` |
| `ramp-limit` | Ramp-rate compliance | study | `{}` |
| `zero-export` | Zero-export constraint | screening | `{"export_factor":0}` |
| `export-cap` | Export bottleneck | screening | `{"export_factor":0.15}` |
| `import-cap` | Import bottleneck | screening | `{"import_factor":0.2}` |
| `negative-prices` | Negative midday prices | screening | `{"negative_prices":true}` |
| `price-spike` | Evening tariff spike | screening | `{"price_factor":3}` |
| `aged-battery` | Aged battery | screening | `{"capacity_factor":0.7}` |
| `battery-trip` | Battery converter outage | screening | `{"battery_factor":0}` |
| `generator-outage` | Generator unavailable | screening | `{"generator_factor":0}` |
| `low-river` | Low river flow | screening | `{"hydro_factor":0.2}` |
| `reserve-floor` | Higher reserve floor | screening | `{"reserve_floor":0.5}` |

## Applicability and runnable pairs

A = applicable numerical screen; S = applicable study configuration/scenario; — = inapplicable. Study cells cannot be submitted as solved results. The complete machine-readable matrix is [hybrid-matrix.json](../examples/hybrid-matrix.json). There are 285 A cells.

| Architecture | baseline | cloud-cover | wind-lull | renewable-drought | heatwave | winter-peak | load-step | outage-4h | outage-24h | outage-72h | black-start | reconnection | weak-grid | ramp-limit | zero-export | export-cap | import-cap | negative-prices | price-spike | aged-battery | battery-trip | generator-outage | low-river | reserve-floor |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| remote-triad | A | A | A | A | A | A | A | — | — | — | S | — | — | S | — | — | — | — | — | A | A | — | — | A |
| utility-pv-ac | A | A | — | A | A | A | A | A | A | A | — | S | S | S | A | A | A | A | A | A | A | — | — | A |
| utility-pv-dc | A | A | — | A | A | A | A | A | A | A | — | S | S | S | A | A | A | A | A | A | A | — | — | A |
| industrial-btm | A | A | — | A | A | A | A | A | A | A | — | S | S | S | A | A | A | A | A | A | A | — | — | A |
| wind-firming | A | — | A | A | A | A | A | A | A | A | — | S | S | S | A | A | A | A | A | A | A | — | — | A |
| hospital-island | A | A | — | A | A | A | A | A | A | A | S | S | S | S | A | A | A | A | A | A | A | A | — | A |
| home-resilience | A | A | — | A | A | A | A | A | A | A | S | S | S | S | A | A | A | A | A | A | A | — | — | A |
| community-energy | A | A | — | A | A | A | A | A | A | A | — | S | S | S | A | A | A | A | A | A | A | — | — | A |
| telecom-dc | A | A | — | A | A | A | A | — | — | — | S | — | — | S | — | — | — | — | — | A | A | — | — | A |
| solar-diesel | A | A | — | A | A | A | A | — | — | — | S | — | — | S | — | — | — | — | — | A | A | A | — | A |
| wind-diesel | A | — | A | A | A | A | A | — | — | — | S | — | — | S | — | — | — | — | — | A | A | A | — | A |
| hydro-triad | A | A | A | A | A | A | A | — | — | — | S | — | — | S | — | — | — | — | — | A | A | — | A | A |
| hydro-battery | A | — | — | — | A | A | A | A | A | A | — | S | S | S | A | A | A | A | A | A | A | — | A | A |
| floating-solar | A | A | — | A | A | A | A | A | A | A | — | S | S | S | A | A | A | A | A | A | A | — | A | A |
| biomass-chp | S | S | — | S | S | S | S | S | S | S | — | S | S | S | S | S | S | S | S | S | S | — | — | S |
| geothermal-hub | S | S | — | S | S | S | S | S | S | S | — | S | S | S | S | S | S | S | S | S | S | — | — | S |
| solar-hydrogen | S | S | — | S | S | S | S | — | — | — | S | — | — | S | — | — | — | — | — | S | S | — | — | S |
| wind-hydrogen | S | — | S | S | S | S | S | S | S | S | — | S | S | S | S | S | S | S | S | — | — | — | — | — |
| csp-storage | S | — | — | — | S | S | S | S | S | S | — | S | S | S | S | S | S | S | S | — | — | — | — | — |
| heatpump-hub | S | S | — | S | S | S | S | S | S | S | — | S | S | S | S | S | S | S | S | S | S | — | — | S |
| district-chp | S | — | — | — | S | S | S | S | S | S | — | S | S | S | S | S | S | S | S | — | — | S | — | — |
| ev-depot | A | A | — | A | A | A | A | A | A | A | — | S | S | S | A | A | A | A | A | A | A | — | — | A |
| v2g-fleet | S | S | — | S | S | S | S | S | S | S | — | S | S | S | S | S | S | S | S | S | S | — | — | S |
| port-microgrid | A | A | A | A | A | A | A | A | A | A | S | S | S | S | A | A | A | A | A | A | A | A | — | A |
| data-centre | A | A | — | A | A | A | A | A | A | A | S | S | S | S | A | A | A | A | A | A | A | A | — | A |
| agrivoltaics | A | A | — | A | A | A | A | A | A | A | — | S | S | S | A | A | A | A | A | A | A | — | — | A |
| desalination | A | A | A | A | A | A | A | — | — | — | S | — | — | S | — | — | — | — | — | A | A | — | — | A |
| pumped-hydro | S | S | S | S | S | S | S | S | S | S | — | S | S | S | S | S | S | S | S | — | — | — | — | — |
| flywheel-hybrid | S | S | — | S | S | S | S | S | S | S | S | S | S | S | S | S | S | S | S | S | S | — | — | S |
| supercapacitor | S | S | — | S | S | S | S | — | — | — | S | — | — | S | — | — | — | — | — | S | S | — | — | S |
| marine-hybrid | S | — | — | — | S | S | S | — | — | — | S | — | — | S | — | — | — | — | — | S | S | — | — | S |
| offshore-island | S | — | S | S | S | S | S | S | S | S | — | S | S | S | S | S | S | S | S | S | S | — | — | S |
| nuclear-hydrogen | S | — | — | — | S | S | S | S | S | S | — | S | S | S | S | S | S | S | S | — | — | — | — | — |
| waste-energy | S | S | — | S | S | S | S | S | S | S | — | S | S | S | S | S | S | S | S | — | — | — | — | — |
| virtual-plant | S | S | S | S | S | S | S | S | S | S | — | S | S | S | S | S | S | S | S | S | S | — | — | S |
| networked-microgrids | S | S | S | S | S | S | S | S | S | S | S | S | S | S | S | S | S | S | S | S | S | S | — | S |
