import math

import pytest

from helioforge.engines import toolkit_studies
from helioforge.engines.toolkit_studies import Annual, annual, run
from tests.study_contract_assertions import number, text


def test_annual_schedule_has_8760_distinct_hours_and_closes_soc() -> None:
    r = run("storage-annual", {})
    rows = r["table"]
    assert len(rows) == 8760
    assert len({x["timestamp"] for x in rows}) == 8760
    assert number(rows[-1]["soc_end_kwh"]) == pytest.approx(number(rows[0]["soc_start_kwh"]), abs=1e-6)
    for row in rows:
        assert number(row["grid_import_kw"]) + number(row["pv_kw"]) + number(
            row["discharge_kw"]
        ) == pytest.approx(
            number(row["load_kw"]) + number(row["charge_kw"]) + number(row["grid_export_kw"]), abs=1e-6
        )
        assert number(row["soc_end_kwh"]) == pytest.approx(
            number(row["soc_start_kwh"])
            + math.sqrt(0.9) * number(row["charge_kw"])
            - number(row["discharge_kw"]) / math.sqrt(0.9),
            abs=1e-6,
        )
        assert number(row["charge_kw"]) * number(row["discharge_kw"]) == 0
        assert 1000 - 1e-6 <= number(row["soc_end_kwh"]) <= 9000 + 1e-6
    assert sum(number(x["pv_kw"]) for x in rows[:24]) != sum(number(x["pv_kw"]) for x in rows[24:48])


@pytest.mark.parametrize(
    "inputs",
    [
        {},
        {"efficiency": 1, "monthly_peak": 3.5},
        {"capacity_kwh": 123.456, "power_kw": 1.23, "efficiency": 0.5},
    ],
)
def test_annual_nonnegative_flows_losses_limits_and_independent_cost_ledger(inputs: dict[str, float]) -> None:
    p = Annual.model_validate(inputs)
    result = annual(p)
    eta = math.sqrt(p.efficiency)
    monthly_peaks = [0.0] * 12
    monthly_energy_cost = [0.0] * 12
    for row in result["table"]:
        charge, discharge = number(row["charge_kw"]), number(row["discharge_kw"])
        assert 0 <= charge <= p.power_kw + 1e-8
        assert 0 <= discharge <= p.power_kw + 1e-8
        assert charge * discharge == 0
        assert charge * (1 - eta) + discharge * (1 / eta - 1) >= 0
        assert number(row["soc_end_kwh"]) == pytest.approx(
            number(row["soc_start_kwh"]) + eta * charge - discharge / eta, abs=1e-8
        )
        assert 0.1 * p.capacity_kwh - 1e-8 <= number(row["soc_end_kwh"]) <= 0.9 * p.capacity_kwh + 1e-8
        assert number(row["grid_import_kw"]) + number(row["pv_kw"]) + discharge == pytest.approx(
            number(row["load_kw"]) + charge + number(row["grid_export_kw"]), abs=1e-8
        )
        cost = (
            number(row["grid_import_kw"]) * number(row["tariff_eur_kwh"])
            - number(row["grid_export_kw"]) * p.export_price
            + discharge * p.wear
        )
        assert number(row["cost_eur"]) == pytest.approx(cost)
        month = int(text(row["timestamp"])[5:7]) - 1
        monthly_peaks[month] = max(monthly_peaks[month], number(row["grid_import_kw"]))
        monthly_energy_cost[month] += cost
    monthly_costs = [
        energy + peak * p.monthly_peak
        for energy, peak in zip(monthly_energy_cost, monthly_peaks, strict=True)
    ]
    assert result["series"][0]["y"] == pytest.approx(monthly_costs)
    assert number(result["metrics"][0]["value"]) == pytest.approx(sum(monthly_costs))
    assert number(result["metrics"][2]["value"]) == pytest.approx(
        number(result["metrics"][1]["value"]) - sum(monthly_costs)
    )
    assert number(result["table"][-1]["soc_end_kwh"]) == pytest.approx(p.capacity_kwh / 2, abs=1e-8)


@pytest.mark.parametrize("upper", [False, True])
def test_soc_roundoff_projection_does_not_reverse_the_selected_flow(upper: bool) -> None:
    eta, floor, ceiling = math.sqrt(0.9), 1000.0, 9000.0
    soc = ceiling - 0.01 if upper else floor + 0.01
    charge = (ceiling - soc) / eta + 1e-9 if upper else 0.0
    discharge = 0.0 if upper else (soc - floor) * eta + 1e-9
    charge, discharge, end = toolkit_studies._bounded_battery_step(
        soc, charge, discharge, eta, floor, ceiling
    )
    assert charge >= 0 and discharge >= 0
    assert charge * discharge == 0
    assert end == (ceiling if upper else floor)
    assert end == pytest.approx(soc + eta * charge - discharge / eta)
    assert (charge > 0) == upper
    assert (discharge > 0) != upper


def test_reserve_zero_interest_hand_case() -> None:
    r = run("pv-reserve", {"cost_eur": 1000, "inflation": 0, "fund_return": 0, "years": 10})
    assert number(r["metrics"][1]["value"]) == pytest.approx(100)


@pytest.mark.parametrize("rate", [1e-300, 1e-16, 1e-10, 0.2])
def test_reserve_tiny_positive_return_and_terminal_target(rate: float) -> None:
    r = run("pv-reserve", {"cost_eur": 1000, "inflation": 0, "fund_return": rate, "years": 10})
    assert r["table"][-1]["balance_eur"] == pytest.approx(1000)
    assert math.isfinite(number(r["metrics"][1]["value"]))


def test_lcoe_sensitivity_increases_with_capex_and_decreases_with_yield() -> None:
    r = run("pv-sensitivity", {})
    rows = r["table"]
    assert number(rows[0]["lcoe_eur_mwh"]) < number(rows[-1]["lcoe_eur_mwh"])
    same_cost = [x for x in rows if number(x["capex_eur_kwp"]) == number(rows[0]["capex_eur_kwp"])]
    assert number(same_cost[0]["lcoe_eur_mwh"]) > number(same_cost[-1]["lcoe_eur_mwh"])
