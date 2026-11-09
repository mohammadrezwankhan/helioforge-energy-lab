# Hybrid terminology and units: draft for review

Source review: automated, 9 November 2026, against commit
`0b38f449611333e52b913b62c1d48d7d85495b82`. An independent energy-systems
reviewer and review date are **pending**. The suggestions below are not
agreed decisions and should not be treated as expert sign-off.

| Displayed term | Unit and screen context | Source and proposed review point |
| --- | --- | --- |
| Solar PV; Battery energy; Battery power | kW; kWh; kW in the configuration form | [Input labels](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/0b38f449611333e52b913b62c1d48d7d85495b82/apps/web/src/hybrid-views.ts#L189). Propose retaining the energy/power distinction; battery energy is capacity, not current stored energy. |
| Base site demand | kW configuration input | [Input label](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/0b38f449611333e52b913b62c1d48d7d85495b82/apps/web/src/hybrid-views.ts#L189). It scales a synthetic hourly profile, rather than setting a constant measured load; consider whether “base” conveys this clearly. |
| Demand; Solar; Wind; Battery discharge; Grid import | kW on the hourly chart | [Series and unit](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/0b38f449611333e52b913b62c1d48d7d85495b82/apps/web/src/hybrid-views.ts#L101). Propose retaining kW and the synthetic-policy caption; these are modeled interval values, not measured dispatch. |
| Critical load served; Total load served | Percent, with kWh shortfall, in result cards | [Result labels](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/0b38f449611333e52b913b62c1d48d7d85495b82/apps/web/src/hybrid-views.ts#L68). Review whether users understand that total shortfall includes planned shedding. |
| Grid energy imported | MWh over the modeled horizon | [Result card and kWh-to-MWh conversion](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/0b38f449611333e52b913b62c1d48d7d85495b82/apps/web/src/hybrid-views.ts#L82). Propose retaining “not annual” and the period boundary. |
| Terminal battery energy | MWh, with initial energy and non-cyclic boundary | [Result card](https://github.com/mohammadrezwankhan/helioforge-energy-lab/blob/0b38f449611333e52b913b62c1d48d7d85495b82/apps/web/src/hybrid-views.ts#L89). Propose retaining both endpoints so depletion is visible. |

The hybrid screen uses prescribed synthetic profiles and a greedy hourly
policy, not a measured dataset or operational forecast. Its [numerical
contract](../HYBRID_METHODOLOGY.md) defines the one-hour intervals and model
limits. No UI wording was changed in this draft. An expert should record a
reviewer/date and an agreed alternative or “no change” for each row.
