#!/usr/bin/env python3
"""Run focused numerical acceptance for each roadmap study and write evidence JSON."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError


ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api"
DEFAULT_OUTPUT = ROOT / "docs" / "remediation-20261029" / "study-contracts.json"
sys.path.insert(0, str(API))

# Each entry points at an executed test containing a hand case, reconstruction,
# analytic invariant, or solver feasibility check beyond a default-finite test.
# The expected statement is deliberately a claim about that specific fixture.
ORACLES: dict[str, tuple[str, str, str, str]] = {
    # engineering_studies (12)
    "hybrid-resonance": ("test_engineering_studies.py", "test_resonance_zero_coupling_retains_two_uncoupled_natural_modes", "At zero coupling, modal frequencies equal the two configured natural frequencies and both modes are stable.", "frequency / damping"),
    "hybrid-clipping": ("test_engineering_studies.py", "test_clipping_recovery_is_limited_by_power_and_soc_headroom", "For the hand case, 2 kWh is recovered; unrecovered clipped DC is 400 - 2/0.96 kWh and the DC ledger residual is zero.", "kWh DC / kWh stored"),
    "hybrid-inertia": ("test_engineering_studies.py", "test_synthetic_inertia_reduces_initial_rocof_and_stays_bounded", "Synthetic inertia improves initial RoCoF relative to zero inertia; frequency remains within the tested 40 Hz floor and RoCoF below 10 Hz/s.", "Hz / Hz/s"),
    "storage-degradation": ("test_engineering_studies.py", "test_degradation_contributions_are_separate_and_increase_with_stress", "SEI, plating and fatigue remain separate; hotter, colder/faster-charge and higher-cycle cases increase their corresponding loss terms.", "fraction / % capacity"),
    "storage-stacking": ("test_engineering_studies.py", "test_storage_stacking_obeys_energy_power_and_terminal_soc", "A 2 kWh/1 kW, two-period case returns to 0.2 kWh terminal SOC and earns 0.2 EUR under the stated price spread.", "kWh / EUR"),
    "storage-synergy": ("test_engineering_studies.py", "test_hybrid_storage_split_conserves_energy_and_reports_unmet_power", "The small split-storage case has zero power-balance residual and zero unmet energy within the tested tolerance.", "kW / kWh"),
    "pv-backtracking": ("test_engineering_studies.py", "test_backtracking_reduces_or_preserves_planar_row_shading", "Turning backtracking on does not increase mean modeled row shading relative to the same planar case with backtracking off.", "fraction"),
    "pv-agrivoltaic": ("test_engineering_studies.py", "test_agrivoltaic_polygon_area_and_par_tradeoff_hand_case", "A 100 m by 50 m rectangle has area 5,000 m²; a 1 m setback leaves 4,700 m² and lower coverage increases modeled crop PAR.", "m² / mol/m²/day"),
    "pv-albedo": ("test_engineering_studies.py", "test_bifacial_albedo_gain_and_monthly_annual_reconciliation", "Monthly rear-response energy sums to annual total; zero albedo contributes zero rear-side energy.", "kWh / fraction"),
    "research-vibration": ("test_engineering_studies.py", "test_vibration_fft_recovers_known_sine_peak_and_seed_is_reproducible", "A 64 Hz pure sine sampled at 1,024 Hz is reported at 64 Hz; fixed-seed default output repeats exactly.", "Hz / signal unit"),
    "research-epd": ("test_engineering_studies.py", "test_epd_sum_skips_duplicate_and_makes_missing_records_visible", "Two duplicate 2-unit records at factor 3 contribute 6 kgCO₂e once; incomplete record is disclosed rather than imputed.", "kgCO₂e / records"),
    "research-scr": ("test_engineering_studies.py", "test_scr_and_voltage_drop_hand_case_is_labeled_as_screening", "600 MVA / 100 MW gives SCR 6; the specified three-phase screening case gives 4.25% voltage drop.", "MVA/MW / % / Ω"),
    # decision_studies (12)
    "overview-weather": ("test_decision_studies.py", "test_weather_stress_exposes_the_common_factor_correlation", "A 0.5 common shock fraction appears as 0.5 off-diagonal theoretical correlation in the six-row synthetic portfolio.", "% / correlation"),
    "overview-merit": ("test_decision_studies.py", "test_merit_matrix_compares_value_routes_to_variable_cost", "For the hand asset, net route values are 30, 50 and 70 EUR/MWh; weights yield 45 EUR/MWh.", "EUR/MWh"),
    "overview-carbon": ("test_decision_studies.py", "test_carbon_uses_hourly_marginal_factors_without_credits_or_day_annualization", "Two hourly samples produce 2,800 kgCO₂e marginal, 2,000 kgCO₂e static, and an 800 kgCO₂e difference.", "kgCO₂e / MWh"),
    "markets-capture": ("test_decision_studies.py", "test_capture_price_zero_generation_has_null_not_fabricated_value", "Capture price is null when total supplied generation is zero; no price is fabricated from a zero denominator.", "EUR/MWh; null at zero MWh"),
    "markets-negative": ("test_decision_studies.py", "test_negative_price_suspension_uses_15_minute_runs_and_warns_about_hypotheses", "Five negative quarter-hours form two runs meeting a two-interval suspension threshold; country policy remains explicitly unverified.", "15-minute intervals / minutes / runs"),
    "markets-interconnection": ("test_decision_studies.py", "test_interconnection_zero_capacity_cannot_create_flow", "Transfer flow is exactly zero at zero interconnection capacity even with a price spread.", "MW"),
    "forecast-regimes": ("test_decision_studies.py", "test_markov_paths_are_seeded_and_quantiles_are_ordered", "Identical seed and inputs reproduce paths; a changed seed changes them and p10 <= p50 <= p90.", "EUR/MWh / paths"),
    "forecast-commodities": ("test_decision_studies.py", "test_commodity_correlation_matrix_must_be_positive_semidefinite", "An explicitly indefinite correlation matrix is rejected before path generation.", "correlation matrix"),
    "forecast-tail": ("test_decision_studies.py", "test_tail_metrics_use_losses_and_cvar_is_not_below_var", "Losses equal (price - 80 EUR/MWh) x 100 MWh; 95% and 99% CVaR are not below their VaR.", "EUR / EUR/MWh / MWh"),
    "investment-sculpt": ("test_decision_studies.py", "test_sculpting_reconciles_amortization_and_handles_zero_rate_and_zero_debt", "Zero-rate debt amortizes 50,000 EUR to zero; with zero debt, DSCR is null rather than a fabricated ratio.", "EUR / ratio; null at zero debt"),
    "investment-tranches": ("test_decision_studies.py", "test_tranche_capacity_uses_cash_flow_bound_above_one_trillion_euros", "At zero interest and DSCR 1, the independent 40-year floor and merchant capacities are 4e12 and 8e12 EUR.", "EUR"),
    "investment-waterfall": ("test_decision_studies.py", "test_waterfall_conserves_distribution_and_applies_catchup_then_promote", "For a 200 EUR distribution pool, tiers allocate the full 200 EUR: capital, pref, catch-up and promote in order.", "EUR"),
    # workflow_studies (12)
    "lessons-duck": ("test_workflow_studies.py", "test_duck_lesson_hand_calculates_net_load_ramp_and_energy_closure", "Two half-hour rows close 11 kWh demand = 5 kWh renewable + 6 kWh net load, with 4 kW/h maximum upward ramp.", "kWh / kW/h"),
    "lessons-blackstart": ("test_workflow_studies.py", "test_blackstart_procedure_requires_sequence_and_respects_active_plus_inrush_budgets", "Out-of-sequence energization and a 70+30 kW step against a 90 kW post-reserve budget are rejected.", "kW / state"),
    "lessons-hydrogen": ("test_workflow_studies.py", "test_hydrogen_stages_close_electric_and_lhv_energy_ledger", "A 1 kg batch stores 33.3 kWh LHV and at 50% fuel-cell efficiency returns 16.65 kWh; zero hydrogen has null efficiency.", "kWh / kWh LHV / fraction"),
    "compare-pareto": ("test_workflow_studies.py", "test_pareto_dominance_and_recommendation_are_limited_to_comparable_runs", "Dominated run c is dominated by a and b; different scenario/sample sets are not compared or recommended.", "runs / groups"),
    "compare-dunkelflaute": ("test_workflow_studies.py", "test_dunkelflaute_dispatch_enforces_direction_and_physical_balance", "For a 100 kW, 100 kWh case, each interval is one-directional, energy closes, and terminal SOC returns to the zero initial target.", "kW / kWh"),
    "compare-thermal": ("test_study_acceptance_contracts.py", "test_thermal_comparison_matches_single_regime_hand_calculation", "For one year at 1 cycle/day, full utilization and depth, EFC is 365; at reference temperature multiplier is 1 and 0.1%/1000 EFC gives 3.65% screening index.", "EFC / multiplier / % index"),
    "pilots-photogrammetry": ("test_workflow_studies.py", "test_photogrammetry_hand_case_empty_cloud_and_mismatch", "Paired errors [0, 3, 4] m yield RMSE sqrt(25/3), maximum 4 m and P50 3 m; empty data preserves null RMSE.", "m / points"),
    "pilots-dts": ("test_workflow_studies.py", "test_dts_reports_stale_missing_and_only_fresh_gradient_data", "At now=10 h and max age=1 h, the 9 h reading is stale by the strict age rule and the null reading remains missing.", "hours / °C / °C/m"),
    "pilots-offgas": ("test_workflow_studies.py", "test_offgas_warning_is_explicit_hypothetical_sensor_vote", "Two sensors each cast one vote when any present channel meets its threshold; state remains a hypothetical warning.", "sensors / state"),
    "council-debate": ("test_workflow_studies.py", "test_council_debate_keeps_conflicting_assertions_and_disputes", "The annual-value topic remains disputed; at zero discount the hand NPV is 230,000 x 15 - 1,200,000 EUR.", "EUR / rounds / topics"),
    "council-evidence": ("test_workflow_studies.py", "test_manifest_checks_expiry_units_bounds_and_supplied_provenance", "A wrong-unit, expired document with missing issuer/source is reported with all three distinct issues.", "documents / issue flags"),
    "council-consensus": ("test_workflow_studies.py", "test_bayesian_probability_normalization_entropy_and_boundary_cases", "Prior 0.5 and likelihood ratio 2 yield posterior 2/3 and binary entropy; prior zero stays zero.", "probability / bits"),
    # toolkit_studies (3)
    "storage-annual": ("test_toolkit_studies.py", "test_annual_nonnegative_flows_losses_limits_and_independent_cost_ledger", "Every hourly bus/SOC ledger is reconstructed and monthly energy+peak costs independently sum to the annual metric.", "kW / kWh / EUR"),
    "pv-sensitivity": ("test_toolkit_studies.py", "test_lcoe_sensitivity_increases_with_capex_and_decreases_with_yield", "LCOE increases with capex and decreases with yield for the same modeled assumptions.", "EUR/MWh"),
    "pv-reserve": ("test_toolkit_studies.py", "test_reserve_zero_interest_hand_case", "A 1,000 EUR reserve spread evenly over 10 years at zero inflation and fund return requires 100 EUR/year.", "EUR / year"),
    # physical_studies (9)
    "hybrid-powerflow": ("test_physical_studies.py", "test_balanced_two_bus_powerflow_matches_resistive_hand_solution_and_branch_loss", "For 0.1 pu resistance and 50 MW load on 100 MVA base, load voltage is (1+sqrt(0.8))/2 pu and branch I²R loss closes.", "p.u. / MW / MVA"),
    "hybrid-switching": ("test_physical_studies.py", "test_switching_and_averaged_inverter_modes_are_distinct_and_numerically_converged", "Sampled switching mode has more carrier ripple than averaged mode and half-step relative error below 5%.", "A / fraction"),
    "lessons-energization": ("test_physical_studies.py", "test_energization_trace_starts_at_breaker_step_and_closes_circuit_energy_balance", "Current is zero before the 5 ms breaker close, then nonzero; circuit energy residual stays within 0.5 J.", "s / A / J"),
    "storage-response": ("test_physical_studies.py", "test_frequency_droop_obeys_ramp_soc_power_and_dt_energy_integration", "For two 49.9 Hz samples, 1000 kW/Hz droop with 100 kW/s ramp produces [10,20] kW; energy is sum(P dt)/3600.", "kW / kWh"),
    "storage-agingfit": ("test_physical_studies.py", "test_agingfit_recovers_synthetic_coefficient_and_reports_heldout_error", "Synthetic fixture fit recovers about 0.018 capacity fraction per 1,000 cycles within 2% and reports held-out RMSE below 0.003.", "fraction / records"),
    "compare-thermalphysics": ("test_physical_studies.py", "test_thermal_arrhenius_source_stops_at_temperature_event", "The explicit Arrhenius fixture terminates at the 50°C configured event threshold with a positive sub-0.01 reaction fraction.", "°C / fraction / J"),
    "pv-raytrace": ("test_physical_studies.py", "test_ray_triangle_shading_handles_shadow_backface_and_zero_sun", "One 10 m² panel at 800 W/m² for one hour receives 8 kWh unshadowed and zero when shadowed, back-facing, or sunless.", "kWh / samples"),
    "pv-setbacks": ("test_physical_studies.py", "test_polygon_setback_preserves_multipolygon_holes_and_crop_light_tradeoff", "Two parcel exteriors total 125 m², less a 4 m² hole gives 121 m²; 1 m setback leaves 57 m² usable.", "m² / ha / mol/m²/day"),
    "research-bearing": ("test_physical_studies.py", "test_bearing_spectrum_envelope_flags_heldout_frequency_outlier_without_diagnosis", "A synthetic 62 Hz held-out component exceeds the training spectrum envelope while the nominal trace is not flagged.", "records / sigma"),
    # planning_studies (9)
    "storage-annualopt": ("test_planning_studies.py", "test_annual_storage_matches_hand_calculated_energy_and_monthly_peak_cost", "With 80 kW residual load, zero storage power, 0.10 EUR/kWh and 2 EUR/kW-month, annual cost is 72,000 EUR.", "EUR / kW"),
    "compare-reliability": ("test_planning_studies.py", "test_reliability_zero_observed_events_keeps_analytic_rare_event_inside_ci", "For stationary failure 1e-6 and repair 0.08, analytic outage=failure/(failure+repair) is contained in reported annualized 95% LOLE/EENS intervals.", "h/year / kWh/year"),
    "forecast-cointegration": ("test_planning_studies.py", "test_cointegration_fit_uses_chronological_holdout_and_assumed_rank", "The generated 120-row case splits 90 training and 30 chronological holdout rows, keeps rank as an explicit assumption, and reports holdout errors.", "price units / observations / RMSE"),
    "forecast-backtest": ("test_planning_studies.py", "test_forecast_backtest_fits_training_rows_and_reports_holdout_metrics", "A constant 100 EUR/MWh series has zero holdout MAE/RMSE and 100% interval coverage with a chronological 35/12 split.", "EUR/MWh / observations"),
    "markets-network": ("test_planning_studies.py", "test_six_zone_dcopf_prices_separate_across_congested_cut", "A 20 MW congested cut separates 10 EUR/MWh source and 100 EUR/MWh local marginal prices with zero balance mismatch.", "MW / EUR/MWh"),
    "investment-contracts": ("test_planning_studies.py", "test_contract_tax_losses_carry_forward_and_zero_investment_irr_stays_null", "A 2,000 EUR loss carries forward; later 10,000 EUR margin at 25% tax yields 1,750 EUR cash tax; zero-investment IRRs remain null.", "EUR / %; null IRR"),
    "lessons-hydrogenaux": ("test_planning_studies.py", "test_hydrogen_ledger_accounts_for_treatment_compression_and_auxiliaries", "For 10 kg, water feed exceeds stoichiometric water, 350 bar compression and auxiliaries are included, and the full energy ledger closes.", "kg / kWh / bar"),
    "overview-risk": ("test_planning_studies.py", "test_portfolio_risk_distinguishes_breach_missing_and_unprovenanced_data", "Three rows produce one breach, one missing value and two incomplete-provenance records without converting unknowns into a clean result.", "rows / status"),
    "pilots-registration": ("test_planning_studies.py", "test_point_cloud_icp_recovers_rigid_transform_without_photo_inputs", "An independently rotated/translated 3D point set is recovered with RMSE below 1e-6 m, all inliers retained, and no photo claim.", "m / points / radians"),
    # control_studies (2)
    "hybrid-controls": ("test_control_studies.py", "test_no_load_case_holds_grid_voltage_and_zero_current", "At zero load the balanced dq control holds grid d-voltage, zero d-axis current, and the analytic capacitor q-axis current.", "V / A"),
    "research-eigenmodes": ("test_control_studies.py", "test_eigenmodes_report_actual_matrix_eigenvalues_and_stable_default", "Reported eigenvalues match independent NumPy eigvals of the reconstructed 10x10 state matrix; the hand matrix coefficient and stable classification agree.", "s⁻¹ / modes"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def finite_json(value: Any) -> bool:
    try:
        encoded = canonical(value)
        json.loads(encoded)
        return True
    except (TypeError, ValueError, OverflowError):
        return False


def metric_snapshot(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"label": metric["label"], "value": metric["value"], "unit": metric["unit"]}
            for metric in result.get("metrics", [])]


def stable_view(value: Any) -> Any:
    volatile = {"solver_runtime_seconds", "runtime_seconds", "elapsed_seconds", "wall_time_seconds"}
    if isinstance(value, dict):
        return {key: stable_view(item) for key, item in value.items() if key not in volatile}
    if isinstance(value, list):
        return [stable_view(item) for item in value]
    return value


class _ResultCapture:
    def __init__(self) -> None:
        self.current_node: str | None = None
        self.calls: dict[str, list[dict[str, Any]]] = {}
        self.patched: set[tuple[int, str]] = set()

    def _patch(self, owner: Any, name: str) -> None:
        key = (id(owner), name)
        if key in self.patched:
            return
        original = getattr(owner, name, None)
        if not callable(original):
            return
        self.patched.add(key)

        def record_call(*args: Any, **kwargs: Any) -> Any:
            try:
                result = original(*args, **kwargs)
            except Exception as exc:
                if self.current_node is not None:
                    self.calls.setdefault(self.current_node, []).append({
                        "raised": type(exc).__name__,
                        "message": str(exc)[:240],
                    })
                raise
            if self.current_node is not None and isinstance(result, dict):
                self.calls.setdefault(self.current_node, []).append({"result": result})
            return result

        setattr(owner, name, record_call)

    def pytest_collection_modifyitems(self, session: Any, config: Any, items: list[Any]) -> None:
        del session, config
        for item in items:
            test_module = item.module
            for name in ("run", "run_workflow_study", "annual"):
                function = getattr(test_module, name, None)
                if callable(function) and getattr(function, "__module__", "").startswith("helioforge.engines."):
                    self._patch(test_module, name)
            for imported in vars(test_module).values():
                if getattr(imported, "__name__", "").startswith("helioforge.engines.") and callable(getattr(imported, "run", None)):
                    self._patch(imported, "run")

    def pytest_runtest_setup(self, item: Any) -> None:
        self.current_node = item.nodeid

    def pytest_runtest_teardown(self, item: Any, nextitem: Any) -> None:
        del item, nextitem
        self.current_node = None


def _summarize_captured(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries = []
    for call in calls:
        if "raised" in call:
            summaries.append({"outcome": "raised", "exception": call["raised"], "message": call["message"]})
            continue
        result = call["result"]
        encoded = canonical(result)
        detail_values = result.get("details", {})
        scalar_details = ({key: value for key, value in detail_values.items()
                          if value is None or isinstance(value, (bool, int, float, str))}
                          if isinstance(detail_values, dict) else {})
        summaries.append({
            "outcome": "returned",
            "metric_snapshot": metric_snapshot(result),
            "scalar_details": scalar_details,
            "table_row_count": len(result.get("table", [])),
            "result_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
        })
    return summaries


def report_pytest_outcomes(nodeids: list[str]) -> tuple[dict[str, str], int, dict[str, list[dict[str, Any]]], dict[str, int]]:
    previous = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="helioforge-study-acceptance-") as temp:
        report_path = Path(temp) / "study-tests.xml"
        os.chdir(API)
        capture = _ResultCapture()
        case_counts = {"executed": 0, "passed": 0, "failed": 0, "skipped": 0}
        try:
            exit_code = int(pytest.main(["-q", "--disable-warnings", f"--junitxml={report_path}", *nodeids], plugins=[capture]))
        finally:
            os.chdir(previous)
        outcomes: dict[str, str] = {}
        if report_path.is_file():
            xml = ET.parse(report_path).getroot()
            for case in xml.iter("testcase"):
                case_counts["executed"] += 1
                source_file = case.attrib.get("file")
                if source_file:
                    test_file = Path(source_file).name
                else:
                    test_file = case.attrib.get("classname", "").split(".")[-1] + ".py"
                test_name = case.attrib.get("name", "").split("[", 1)[0]
                key = f"tests/{test_file}::{test_name}"
                failure = case.find("failure")
                error = case.find("error")
                skipped = case.find("skipped")
                status = "FAIL" if failure is not None or error is not None else (
                    "SKIP" if skipped is not None else "PASS"
                )
                case_counts[{"PASS": "passed", "FAIL": "failed", "SKIP": "skipped"}[status]] += 1
                prior = outcomes.get(key)
                outcomes[key] = "FAIL" if "FAIL" in (prior, status) else (
                    "PASS" if prior == "PASS" or status == "PASS" else "SKIP"
                )
        return outcomes, exit_code, capture.calls, case_counts


def run_one(module: Any, study: dict[str, Any], test_status: str,
            observed_cases: list[dict[str, Any]], repo_root: Path) -> dict[str, Any]:
    study_id = study["id"]
    defaults = {field["name"]: copy.deepcopy(field["default"])
                for field in [*study.get("fields", []), *study.get("data_fields", [])]}

    # The normal result goes through the same public study request envelope as the API.
    from helioforge.studies import StudyRequest, evaluate

    result = evaluate(StudyRequest(study=study_id))
    result_without_digest = copy.deepcopy(result)
    evidence_digest = result_without_digest.pop("evidence_sha256", None)
    digest_matches = evidence_digest == hashlib.sha256(canonical(result_without_digest).encode()).hexdigest()
    json_text = canonical(result)
    json_copy = json.loads(json_text)
    export_ok = canonical(json_copy) == json_text and digest_matches

    schema_ok = (
        {"metrics", "series", "table", "warnings", "study", "model_version",
         "inputs", "data_kind", "equations", "limitations", "sources", "evidence_sha256"} <= set(result)
        and ("details" not in result or isinstance(result["details"], dict))
        and bool(result.get("metrics"))
        and all({"label", "value", "unit"} <= set(metric) for metric in result["metrics"])
        and all(len(series.get("x", [])) == len(series.get("y", [])) for series in result["series"])
        and finite_json(result)
    )

    # Run one actual catalogue input boundary when scalar bounds exist. For data-only studies,
    # try a zero/empty data boundary and then the shortest valid prefix of list fixtures.
    boundary = {"status": "FAIL", "reason": "No valid declared boundary case was found."}
    scalar_fields = [field for field in study.get("fields", [])
                     if isinstance(field.get("min"), (int, float)) and isinstance(field.get("default"), (int, float))]
    candidates: list[tuple[str, dict[str, Any]]] = []
    if scalar_fields:
        field = scalar_fields[0]
        for edge_name in ("min", "max"):
            if isinstance(field.get(edge_name), (int, float)):
                payload = copy.deepcopy(defaults)
                payload[field["name"]] = field[edge_name]
                candidates.append((f"{field['name']}={field[edge_name]} ({edge_name} bound)", payload))
    for field in study.get("data_fields", []):
        name, default = field["name"], copy.deepcopy(field["default"])
        if isinstance(default, list):
            if not default:
                candidates.append((f"{name}=empty (declared zero-length boundary)", copy.deepcopy(defaults)))
            elif all(isinstance(item, (int, float)) for item in default):
                payload = copy.deepcopy(defaults)
                payload[name] = [0 for _ in default]
                candidates.append((f"{name}=zero vector at preserved length", payload))
            else:
                payload = copy.deepcopy(defaults)
                payload[name] = []
                candidates.append((f"{name}=empty-list boundary", payload))
                for count in range(1, len(default)):
                    payload = copy.deepcopy(defaults)
                    payload[name] = copy.deepcopy(default[:count])
                    candidates.append((f"{name}=valid prefix length {count}", payload))
        elif isinstance(default, dict):
            candidates.append((f"{name}=declared object default", copy.deepcopy(defaults)))
    for label, payload in candidates:
        try:
            boundary_result = module.run(study_id, payload)
            if finite_json(boundary_result):
                boundary = {"status": "PASS", "case": label,
                            "metric_snapshot": metric_snapshot(boundary_result)}
                break
        except (ValidationError, ValueError, ArithmeticError, TypeError):
            continue

    try:
        module.run(study_id, {"__acceptance_unknown_field__": 1})
        invalid_check = {"status": "FAIL", "case": "unknown input field", "actual": "accepted"}
    except (ValidationError, ValueError) as exc:
        invalid_check = {"status": "PASS", "case": "unknown input field", "actual": type(exc).__name__}
    except Exception as exc:  # unexpected exceptions are not accepted as validation
        invalid_check = {"status": "FAIL", "case": "unknown input field", "actual": type(exc).__name__}

    try:
        repeat = module.run(study_id, copy.deepcopy(defaults))
        repeatable = stable_view(repeat) == stable_view(module.run(study_id, copy.deepcopy(defaults)))
        repeat_check = {"status": "PASS" if repeatable else "FAIL",
                        "comparison": "exact after excluding reported wall-clock solver fields"}
    except Exception as exc:
        repeat_check = {"status": "FAIL", "actual": type(exc).__name__}

    test_file, test_name, expected, units = ORACLES[study_id]
    nodeid = f"tests/{test_file}::{test_name}"
    actual = {
        "independent_test_outcome": test_status,
        "observed_cases": _summarize_captured(observed_cases),
        "default_metric_snapshot": metric_snapshot(result),
        "default_result_sha256": hashlib.sha256(json_text.encode()).hexdigest(),
    }
    details = result.get("details", {})
    solver_status = details.get("solver_status")
    solver_check = ({"status": "PASS" if solver_status == "optimal" else "FAIL", "actual": solver_status}
                    if solver_status is not None else {"status": "NOT_APPLICABLE",
                        "reason": "This study result has no solver_status field; solver feasibility is not part of its declared computation."})
    fit_success = details.get("fit_success")
    if fit_success is not None:
        solver_check = {"status": "PASS" if fit_success else "FAIL", "actual": "fit_success=" + str(fit_success)}
    converged = details.get("converged")
    if converged is not None:
        solver_check = {"status": "PASS" if converged else "FAIL", "actual": "converged=" + str(converged)}
    if study_id == "compare-dunkelflaute":
        solver_check = {
            "status": "PASS" if test_status == "PASS" else "FAIL",
            "solver": "SciPy/HiGHS MILP",
            "feasibility_evidence": "The linked case checks interval direction, power/SOC bounds, energy balance, and terminal SOC.",
            "optimality_status": "U — not exposed in this result; feasibility checks do not independently prove global optimality.",
        }

    source_file = Path(module.__file__).resolve()
    test_path = (API / "tests" / test_file).resolve()
    uncovered = [str(item) for item in study.get("limitations", [])]
    if not uncovered:
        uncovered = ["No source-backed calibration against external measured data was executed in this software acceptance."]
    uncovered.append("No independent scientific or field validation is established by this software test.")

    checks = {
        "default_contract": {"status": "PASS" if schema_ok else "FAIL",
                             "actual": {"finite_json": finite_json(result), "null_metric_count": sum(m["value"] is None for m in result["metrics"]),
                                        "metric_count": len(result["metrics"])}},
        "boundary_case": boundary,
        "invalid_input": invalid_check,
        "repeatability": repeat_check,
        "json_export": {"status": "PASS" if export_ok else "FAIL",
                        "actual": "strict JSON round-trip preserved result and recomputed evidence digest" if export_ok else "JSON round-trip or digest mismatch",
                        "sha256": hashlib.sha256(json_text.encode()).hexdigest()},
        "solver_feasibility": solver_check,
    }
    required_statuses = [checks[name]["status"] for name in ("default_contract", "boundary_case", "invalid_input", "repeatability", "json_export")]
    status = "PASS" if test_status == "PASS" and all(value == "PASS" for value in required_statuses) and solver_check["status"] != "FAIL" else "FAIL"
    return {
        "study_id": study_id,
        "workspace": study["page"],
        "title": study["title"],
        "status": status,
        "test_ids": [{"node_id": nodeid, "status": test_status}],
        "oracle": {
            "method": "Executed existing targeted independent software oracle; expected relation is documented below and in the referenced test.",
            "expected": expected,
            "actual": actual,
            "units": units,
            "evidence_class": "independent_software_oracle",
        },
        "checks": checks,
        "source_hashes": {
            "provenance_file": "apps/api/helioforge/provenance.py",
            "provenance_sha256": sha256(repo_root / "apps/api/helioforge/provenance.py"),
            "schemas_file": "apps/api/helioforge/schemas.py",
            "schemas_sha256": sha256(repo_root / "apps/api/helioforge/schemas.py"),
            "shared_finance_file": "apps/api/helioforge/engines/finance.py",
            "shared_finance_sha256": sha256(repo_root / "apps/api/helioforge/engines/finance.py"),
            "engine_file": source_file.relative_to(repo_root).as_posix(),
            "engine_sha256": sha256(source_file),
            "test_file": test_path.relative_to(repo_root).as_posix(),
            "test_sha256": sha256(test_path),
            "catalogue_file": "apps/api/helioforge/studies.py",
            "catalogue_sha256": sha256(repo_root / "apps" / "api" / "helioforge" / "studies.py"),
        },
        "uncovered_conditions": uncovered,
    }


def main() -> int:
    from helioforge.studies import MODULES, catalogue

    studies = catalogue()
    by_id = {study["id"]: study for study in studies}
    if set(by_id) != set(ORACLES) or len(studies) != 59:
        missing = sorted(set(by_id) - set(ORACLES))
        stale = sorted(set(ORACLES) - set(by_id))
        print(f"oracle map mismatch: missing={missing}, stale={stale}", file=sys.stderr)
        return 2

    modules = {study["id"]: module for module in MODULES for study in module.STUDIES}
    nodeids = sorted({f"tests/{test_file}::{test_name}" for test_file, test_name, _, _ in ORACLES.values()})
    test_outcomes, pytest_exit, captured_cases, test_case_counts = report_pytest_outcomes(nodeids)
    records = []
    for study_id in sorted(by_id):
        test_file, test_name, _, _ = ORACLES[study_id]
        test_node = f"tests/{test_file}::{test_name}"
        outcome = test_outcomes.get(test_node, "FAIL")
        observed = [call for captured_node, calls in captured_cases.items()
                    if captured_node == test_node or captured_node.startswith(test_node + "[")
                    for call in calls]
        records.append(run_one(modules[study_id], by_id[study_id], outcome,
                               observed, ROOT))

    report = {
        "artifact_schema": "helioforge.study-acceptance.v1",
        "generated_on": "2026-10-29",
        "source_revision_basis": "74d6730e38323b69c180d7f4b4945d11010203f3; dirty remediation tree",
        "purpose": "Focused software/numerical acceptance of all registered study IDs; not scientific, calibration, regulatory or deployment validation.",
        "study_count": len(records),
        "targeted_test_run": {"pytest_exit_code": pytest_exit, "distinct_node_ids": len(nodeids),
                              "executed_test_cases": test_case_counts["executed"],
                              "passed_test_cases": test_case_counts["passed"],
                              "failed_test_cases": test_case_counts["failed"],
                              "skipped_test_cases": test_case_counts["skipped"],
                              "passed": sum(status == "PASS" for status in test_outcomes.values()),
                              "failed_or_missing": sum(status != "PASS" for status in test_outcomes.values()),
                              "node_id_status": test_outcomes},
        "status_counts": {status: sum(record["status"] == status for record in records) for status in ("PASS", "FAIL")},
        "studies": records,
    }
    output = Path(os.environ.get("HELIOFORGE_STUDY_ACCEPTANCE_OUTPUT", str(DEFAULT_OUTPUT))).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS" if report["status_counts"]["FAIL"] == 0 else "FAIL",
                      "study_count": len(records), "studies_passed": report["status_counts"]["PASS"],
                      "studies_failed": report["status_counts"]["FAIL"],
                      "targeted_test_nodes": len(nodeids), "targeted_tests_passed": report["targeted_test_run"]["passed"],
                      "executed_test_cases": test_case_counts["executed"],
                      "passed_test_cases": test_case_counts["passed"],
                      "failed_test_cases": test_case_counts["failed"],
                      "targeted_tests_failed_or_missing": report["targeted_test_run"]["failed_or_missing"],
                      "output": str(output)}, ensure_ascii=False))
    return 0 if report["status_counts"]["FAIL"] == 0 and pytest_exit == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
