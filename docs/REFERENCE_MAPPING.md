# Mapping the supplied reference archive

The supplied `hybrid_power_systems_archive.zip` contains a Markdown overview, PDF and two diagrams. Its Markdown describes five conceptual configurations. These were used to identify topology, assets and lesson goals; the new UI uses original software-3D geometry and does not embed the supplied diagrams. No third-party licence is inferred for those reference images.

| Reference configuration | Implemented catalogue ID | Treatment |
|---|---|---|
| Standalone PV + wind + BESS | `remote-triad` | Off-grid electricity screen; declared battery reference; explicit no-grid condition. |
| Utility PV + BESS, AC/DC variants | `utility-pv-ac`, `utility-pv-dc` | Separate configurations and lessons. DC numerical output remains AC-equivalent; shared-inverter/DC physics excluded. |
| C&I behind-the-meter PV + BESS | `industrial-btm` | BTM energy screen and grid/export limits. Demand-charge optimization is not represented by the hybrid policy. |
| Wind + BESS | `wind-firming` | Wind availability and battery screen. Ramp-limit/control dynamics remain study-only. |
| Islanding hospital/data centre | `hospital-island`, `data-centre` | Explicitly islandable topology; outage service accounting with GFL/GFM/Dual assumptions, not transfer-transient validation. |

All five reference families are represented, including their important unsupported objectives. The expansion to 36 curated architectures is not a claim to enumerate every physically possible hybrid. It adds an extensible catalogue, capability gating and authoring rules so future models can be added without disguising missing science.
