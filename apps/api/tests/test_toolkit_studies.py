import math

import pytest

from helioforge.engines.toolkit_studies import run


def test_annual_schedule_has_8760_distinct_hours_and_closes_soc():
    r = run("storage-annual", {})
    rows = r["table"]
    assert len(rows) == 8760
    assert len({x["timestamp"] for x in rows}) == 8760
    assert rows[-1]["soc_end_kwh"] == pytest.approx(rows[0]["soc_start_kwh"], abs=1e-6)
    for row in rows:
        assert row["grid_import_kw"] + row["pv_kw"] + row["discharge_kw"] == pytest.approx(
            row["load_kw"] + row["charge_kw"] + row["grid_export_kw"], abs=1e-6
        )
        assert row["soc_end_kwh"] == pytest.approx(
            row["soc_start_kwh"] + math.sqrt(0.9) * row["charge_kw"] - row["discharge_kw"] / math.sqrt(0.9),
            abs=1e-6,
        )
        assert row["charge_kw"] * row["discharge_kw"] == 0
        assert 1000 - 1e-6 <= row["soc_end_kwh"] <= 9000 + 1e-6
    assert sum(x["pv_kw"] for x in rows[:24]) != sum(x["pv_kw"] for x in rows[24:48])


def test_reserve_zero_interest_hand_case():
    r = run("pv-reserve", {"cost_eur": 1000, "inflation": 0, "fund_return": 0, "years": 10})
    assert r["metrics"][1]["value"] == pytest.approx(100)


@pytest.mark.parametrize('rate',[1e-300,1e-16,1e-10,.2])
def test_reserve_tiny_positive_return_and_terminal_target(rate):
    r=run('pv-reserve',{'cost_eur':1000,'inflation':0,'fund_return':rate,'years':10})
    assert r['table'][-1]['balance_eur']==pytest.approx(1000)
    assert math.isfinite(r['metrics'][1]['value'])


def test_lcoe_sensitivity_increases_with_capex_and_decreases_with_yield():
    r = run("pv-sensitivity", {})
    rows = r["table"]
    assert rows[0]["lcoe_eur_mwh"] < rows[-1]["lcoe_eur_mwh"]
    same_cost = [x for x in rows if x["capex_eur_kwp"] == rows[0]["capex_eur_kwp"]]
    assert same_cost[0]["lcoe_eur_mwh"] > same_cost[-1]["lcoe_eur_mwh"]
