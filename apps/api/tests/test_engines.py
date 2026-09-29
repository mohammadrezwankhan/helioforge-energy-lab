import math

import numpy as np
import pytest
from pydantic import ValidationError

from helioforge.engines.finance import annuity, calculate_finance, calculate_pv, conventional_irr, npv, screen_acquisition
from helioforge.engines.forecast import forecast_prices
from helioforge.engines.research import detect_drift, reliability, sustainability
from helioforge.engines.storage import optimize_storage
from helioforge.schemas import (DriftRequest, FinanceRequest, ForecastRequest, MARequest, PVRequest,
                               ReliabilityRequest, StorageRequest, SustainabilityRequest)


def flat_storage(**updates):
    values = dict(capacity_kwh=10, power_kw=5, grid_import_limit_kw=30, grid_export_limit_kw=30,
                  load_kw=[10.]*8, pv_kw=[0.]*8, import_eur_per_kwh=[.15]*8, export_eur_per_kwh=[.05]*8)
    values.update(updates)
    return StorageRequest(**values)


def assert_dispatch_invariants(p, result):
    for row in result['schedule']:
        assert row['charge_kw']*row['discharge_kw'] < .05
        assert row['grid_import_kw']*row['grid_export_kw'] < .05
        assert p.min_soc_fraction*p.capacity_kwh-.002 <= row['soc_end_kwh'] <= p.max_soc_fraction*p.capacity_kwh+.002
        lhs = row['pv_kw']-row['curtailed_kw']+row['grid_import_kw']+row['discharge_kw']
        rhs = row['load_kw']+row['charge_kw']+row['grid_export_kw']
        assert lhs == pytest.approx(rhs, abs=.003)
        eta = math.sqrt(p.round_trip_efficiency)
        next_soc = row['soc_start_kwh']+row['charge_kw']*eta*p.interval_hours-row['discharge_kw']/eta*p.interval_hours
        assert row['soc_end_kwh'] == pytest.approx(next_soc, abs=.004)
    assert result['terminal_soc_kwh'] == pytest.approx(p.capacity_kwh*p.initial_soc_fraction, abs=.002)
    assert result['savings_eur'] >= -.02


@pytest.mark.parametrize('market', ['FR','DE','ES','IT','NL','GB'])
def test_demo_dispatch_is_feasible_and_auditable(market):
    p = StorageRequest(market=market)
    result = optimize_storage(p)
    assert result['solver_status'] == 'optimal'
    assert result['duration_hours'] == 24
    assert result['data_kind'] == 'synthetic'
    assert_dispatch_invariants(p, result)
    assert result['savings_eur'] == pytest.approx(result['energy_savings_eur']+result['peak_savings_eur']-result['wear_cost_eur'], abs=.02)


def test_flat_tariff_does_not_invent_savings():
    r = optimize_storage(flat_storage())
    assert r['savings_eur'] == 0
    assert r['discharged_kwh'] == 0


def test_zero_load_zero_pv_no_op():
    r = optimize_storage(flat_storage(load_kw=[0.]*8))
    assert r['savings_eur'] == 0
    assert r['savings_pct'] is None


def test_known_two_interval_arbitrage():
    p = StorageRequest(capacity_kwh=2, power_kw=1, round_trip_efficiency=1, min_soc_fraction=0,
                       max_soc_fraction=1, initial_soc_fraction=0, wear_eur_per_kwh=0,
                       load_kw=[1,1], pv_kw=[0,0], import_eur_per_kwh=[.1,.3], export_eur_per_kwh=[0,0])
    r = optimize_storage(p)
    assert r['savings_eur'] == pytest.approx(.2)
    assert r['schedule'][0]['charge_kw'] == 1
    assert r['schedule'][1]['discharge_kw'] == 1


def test_quarter_hour_energy_accounting():
    p = flat_storage(interval_hours=.25, import_eur_per_kwh=[.05]*4+[.5]*4, round_trip_efficiency=.81)
    r = optimize_storage(p)
    assert r['duration_hours'] == 2
    assert_dispatch_invariants(p, r)


def test_export_above_import_does_not_create_grid_loop():
    p = flat_storage(export_eur_per_kwh=[1]*8, pv_kw=[20]*8)
    assert_dispatch_invariants(p, optimize_storage(p))


def test_negative_imports_baseline_can_curtail_pv():
    p = flat_storage(import_eur_per_kwh=[-.1]*8, export_eur_per_kwh=[-.2]*8, pv_kw=[10]*8)
    r = optimize_storage(p)
    # Baseline can curtail PV and import 10 kW into actual demand, but not fabricate demand.
    assert r['baseline_cost_eur'] == pytest.approx(-8)
    assert_dispatch_invariants(p, r)


def test_negative_export_uses_curtailment():
    p = flat_storage(load_kw=[0.]*8, pv_kw=[20.]*8, export_eur_per_kwh=[-.2]*8)
    r = optimize_storage(p)
    assert r['baseline_cost_eur'] == 0
    assert all(row['grid_export_kw'] == 0 for row in r['schedule'])
    assert r['savings_eur'] == 0


def test_zero_grid_export_is_respected():
    p = flat_storage(pv_kw=[20.]*8, grid_export_limit_kw=0)
    r = optimize_storage(p)
    assert all(row['grid_export_kw'] == 0 for row in r['schedule'])
    assert_dispatch_invariants(p, r)


def test_period_peak_charge_not_annualized():
    p = flat_storage(peak_charge_eur_per_kw_period=10)
    r = optimize_storage(p)
    assert r['baseline_cost_eur'] == pytest.approx(12+100)


def test_infeasible_grid_is_rejected():
    with pytest.raises(ValueError):
        optimize_storage(flat_storage(grid_import_limit_kw=1))


@pytest.mark.parametrize('kwargs', [
    {'capacity_kwh':0}, {'power_kw':-2}, {'round_trip_efficiency':1.1}, {'initial_soc_fraction':.95},
    {'min_soc_fraction':.8,'max_soc_fraction':.4}, {'load_kw':[1,2]}, {'load_kw':[float('nan')]*8},
    {'interval_hours':.25}, {'market':'XX'}, {'unknown_field':42},
])
def test_storage_validation(kwargs):
    with pytest.raises(ValidationError):
        StorageRequest(**kwargs)


def test_custom_timeseries_lengths_must_match():
    with pytest.raises(ValidationError):
        flat_storage(pv_kw=[1,2])


def test_npv_reference_case():
    assert npv(.1, [-100,110]) == pytest.approx(0)
    assert npv(0, [-100,60,60]) == 20
    with pytest.raises(ValueError):
        npv(-1, [-100,110])


def test_irr_reference_case():
    assert conventional_irr([-100,110]) == pytest.approx(.1)
    assert conventional_irr([-100,90]) == pytest.approx(-.1)
    assert conventional_irr([-100,-10]) is None
    assert conventional_irr([100,110]) is None
    assert conventional_irr([-100,230,-132]) is None  # Two positive roots: do not choose one.


def test_annuity_zero_interest_and_zero_debt():
    assert annuity(100,0,10) == 10
    assert annuity(0,.1,10) == 0
    assert annuity(100,.1,1) == pytest.approx(110)


def test_finance_augmentation_and_debt_reconcile():
    p = FinanceRequest()
    r = calculate_finance(p)
    assert r['rows'][9]['augmentation_eur'] == 450000
    assert r['rows'][9]['dscr'] < p.minimum_dscr
    assert r['covenant_pass'] is False
    assert r['rows'][9]['debt_balance_eur'] == 0
    assert all(row['debt_service_eur'] == 0 for row in r['rows'][10:])
    assert r['rows'][10]['contracted_fraction'] == 0
    assert r['irr_pct'] == pytest.approx(16.128, abs=.005)
    for row in r['rows']:
        assert row['equity_cashflow_eur'] == pytest.approx(row['cfads_eur']-row['debt_service_eur'], abs=.02)


def test_finance_zero_debt_has_no_dscr():
    r = calculate_finance(FinanceRequest(debt_fraction=0))
    assert r['minimum_dscr'] is None
    assert r['covenant_pass'] is None
    assert all(row['dscr'] is None for row in r['rows'])


def test_finance_lower_margin_does_not_improve_npv():
    a = calculate_finance(FinanceRequest(annual_gross_margin_eur=820000))
    b = calculate_finance(FinanceRequest(annual_gross_margin_eur=400000))
    assert b['npv_eur'] < a['npv_eur']
    assert b['minimum_dscr'] < a['minimum_dscr']


def test_nonconventional_cashflow_irr_not_fabricated():
    r = calculate_finance(FinanceRequest(augmentation_cost_eur=2500000))
    assert r['irr_pct'] is None
    assert any('non-conventional' in w for w in r['warnings'])


@pytest.mark.parametrize('kwargs',[{'years':5}, {'debt_tenor_years':25}, {'contract_years':25}, {'augmentation_year':25}])
def test_finance_term_validation(kwargs):
    with pytest.raises(ValidationError):
        FinanceRequest(**kwargs)


def test_undiscounted_lcoe_known_case():
    p = PVRequest(capacity_kwp=1,specific_yield_kwh_kwp=1000,capex_eur_kwp=1000,opex_eur_kwp_year=0,
                  degradation_fraction=0,discount_rate=0,years=10,curtailment_fraction=0,inverter_replacement_year=None)
    r = calculate_pv(p)
    assert r['lcoe_eur_mwh'] == pytest.approx(100)
    assert r['first_year_generation_mwh'] == 1


def test_pv_monotonic_capex_and_degradation():
    a=calculate_pv(PVRequest())
    assert calculate_pv(PVRequest(capex_eur_kwp=1000))['lcoe_eur_mwh'] > a['lcoe_eur_mwh']
    assert calculate_pv(PVRequest(degradation_fraction=.02))['lcoe_eur_mwh'] > a['lcoe_eur_mwh']
    assert a['rows'][-1]['generation_mwh'] < a['rows'][0]['generation_mwh']


def test_pv_rounds_panel_count_up():
    r=calculate_pv(PVRequest(capacity_kwp=1,panel_kwp=.6))
    assert r['panel_count'] == 2


def test_forecast_seed_and_quantiles():
    a=forecast_prices(ForecastRequest())
    assert a == forecast_prices(ForecastRequest())
    assert a != forecast_prices(ForecastRequest(seed=43))
    assert all(row['p10_eur_mwh'] <= row['p50_eur_mwh'] <= row['p90_eur_mwh'] for row in a['rows'])


def test_forecast_negative_prices_not_clipped():
    r=forecast_prices(ForecastRequest(base_price_eur_mwh=-50,long_run_price_eur_mwh=-50,annual_shock_eur_mwh=0,trend_eur_mwh_year=0))
    assert all(row['p50_eur_mwh'] == -50 for row in r['rows'])


def test_drift_detects_synthetic_step():
    r=detect_drift(DriftRequest(expected=[100]*30,observed=[100]*20+[90]*10))
    assert r['alert_indices'] == list(range(20,30))
    assert r['drift_pct'] == -10


def test_drift_flat_baseline_no_false_alerts():
    r=detect_drift(DriftRequest(expected=[100]*30,observed=[100]*30))
    assert r['alert_count'] == 0


def test_drift_length_validation():
    with pytest.raises(ValidationError):
        DriftRequest(expected=[100]*20,observed=[100]*15)


def test_weibull_exponential_reference():
    r=reliability(ReliabilityRequest(shape=1,scale_hours=100,age_hours=100,horizon_hours=100))
    assert r['conditional_failure_pct'] == pytest.approx((1-math.exp(-1))*100, abs=.001)
    assert r['conditional_median_remaining_hours'] == pytest.approx(math.log(2)*100, abs=.01)


def test_carbon_units_and_negative_avoidance():
    r=sustainability(SustainabilityRequest(annual_generation_kwh=1000,years=1,degradation_fraction=0,
                                         embodied_kgco2e=100,annual_operational_kgco2e=0,end_of_life_kgco2e=0,
                                         counterfactual_kgco2e_kwh=.05))
    assert r['intensity_gco2e_kwh'] == 100
    assert r['net_counterfactual_avoided_tco2e'] == -.05


def test_acquisition_ev_and_equity_not_confused():
    r=screen_acquisition(MARequest(enterprise_value_eur=100,net_debt_eur=130,annual_ebitda_eur=10,annual_maintenance_capex_eur=0))
    assert r['implied_equity_value_eur'] == -30
    assert r['ev_ebitda'] == 10


def test_randomized_dispatch_energy_invariants():
    rng=np.random.default_rng(101)
    for _ in range(12):
        p=flat_storage(load_kw=rng.uniform(0,15,8).tolist(),pv_kw=rng.uniform(0,20,8).tolist(),
                       import_eur_per_kwh=rng.uniform(-.1,.5,8).tolist(),export_eur_per_kwh=rng.uniform(-.2,.6,8).tolist(),
                       round_trip_efficiency=float(rng.uniform(.7,1)))
        assert_dispatch_invariants(p,optimize_storage(p))


def test_covenant_decision_uses_unrounded_dscr():
    p = FinanceRequest(capex_eur=100000, annual_gross_margin_eur=64980,
                       annual_opex_eur=0, years=2, debt_fraction=.5, debt_interest_rate=0,
                       debt_tenor_years=1, annual_margin_degradation=0, escalation_rate=0,
                       augmentation_year=None, contract_years=0, merchant_margin_factor=1)
    r = calculate_finance(p)
    assert r["minimum_dscr"] == pytest.approx(1.2996)
    assert r["covenant_pass"] is False  # Rounding to 1.300 must not approve a breach.
