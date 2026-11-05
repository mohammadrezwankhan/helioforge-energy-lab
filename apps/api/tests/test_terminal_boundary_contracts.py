"""Terminal input failures and one-sided sensitivity remain explicit and bounded."""

import pytest

from helioforge.engines.terminal import (
    TerminalModelError,
    terminal_defaults,
    terminal_sensitivity,
    terminal_solve,
    terminal_sweep,
    terminal_validate_inputs,
)


@pytest.mark.parametrize("value", [None, [], "scenario", 3])
def test_terminal_requires_an_input_object(value: object) -> None:
    with pytest.raises(TerminalModelError, match="Inputs must be an object") as caught:
        terminal_solve(value)
    assert caught.value.code == "ERR_VALIDATION"


def test_missing_fields_and_invalid_soc_order_are_explicit_validation_errors() -> None:
    missing = terminal_defaults()
    del missing["pvKw"]
    with pytest.raises(TerminalModelError, match="missing fields: pvKw") as caught:
        terminal_validate_inputs(missing)
    assert caught.value.code == "ERR_VALIDATION"
    with pytest.raises(TerminalModelError, match="minSocFraction must be less"):
        terminal_validate_inputs({**terminal_defaults(), "minSocFraction": 0.8, "maxSocFraction": 0.2})


@pytest.mark.parametrize("value", [True, False, "8", None, [8]])
def test_numeric_terminal_fields_never_coerce_non_numeric_values(value: object) -> None:
    with pytest.raises(TerminalModelError, match="pvKw must be a finite number") as caught:
        terminal_validate_inputs({**terminal_defaults(), "pvKw": value})
    assert caught.value.code == "ERR_VALIDATION"


@pytest.mark.parametrize(
    "field,value,code,message",
    [
        ("parameter", "unknown", "ERR_VALIDATION", "Unknown sweep parameter"),
        ("parameter", 3, "ERR_VALIDATION", "Unknown sweep parameter"),
        ("lower", True, "ERR_VALIDATION", "must be finite numbers"),
        ("upper", "5", "ERR_VALIDATION", "must be finite numbers"),
        ("lower", float("nan"), "ERR_VALIDATION", "must be finite numbers"),
        ("upper", float("inf"), "ERR_VALIDATION", "must be finite numbers"),
        pytest.param("upper", 10**10000, "ERR_VALIDATION", "must be finite numbers", id="overflow"),
        ("lower", 5, "ERR_VALIDATION", "lower bound must be less"),
        ("steps", True, "ERR_BOUND", "integer from 2 through 21"),
        ("steps", 2.5, "ERR_BOUND", "integer from 2 through 21"),
        ("scale", "cubic", "ERR_VALIDATION", "must be linear or log"),
        ("scale", None, "ERR_VALIDATION", "must be linear or log"),
        ("lower", -1, "ERR_BOUND", "sweep bounds must stay within"),
    ],
)
def test_invalid_second_sweep_axis_reports_error_before_evaluating_points(
    field: str, value: object, code: str, message: str
) -> None:
    second: dict[str, object] = {
        "parameter": "gridKw",
        "lower": 1,
        "upper": 5,
        "steps": 2,
        "scale": "linear",
    }
    second[field] = value
    inputs = terminal_defaults()
    with pytest.raises(TerminalModelError, match=message) as caught:
        terminal_sweep(inputs, "pvKw", 1, 5, 2, "linear", second=second)
    assert caught.value.code == code
    assert inputs == terminal_defaults()


def test_sweep_rejects_duplicate_axes_and_exclusive_efficiency_lower_bound() -> None:
    with pytest.raises(TerminalModelError, match="two different parameters"):
        terminal_sweep(
            terminal_defaults(),
            "pvKw",
            1,
            5,
            2,
            "linear",
            second={"parameter": "pvKw", "lower": 1, "upper": 5, "steps": 2, "scale": "linear"},
        )
    with pytest.raises(TerminalModelError, match=r"within greater than 0\.0") as caught:
        terminal_sweep(terminal_defaults(), "roundtripEfficiency", 0, 1, 2, "linear")
    assert caught.value.code == "ERR_BOUND"


def test_idle_storage_does_not_report_a_power_or_soc_limit() -> None:
    result = terminal_solve({**terminal_defaults(), "pvKw": 0, "loadKw": 0, "gridKw": 0})
    assert result["metrics"]["initialSocKwh"] == result["metrics"]["finalSocKwh"] == 10
    assert all(row["chargeKw"] == row["dischargeKw"] == 0 for row in result["rows"])
    storage_flag = next(flag for flag in result["flags"] if flag["key"] == "soc-or-power-limit")
    assert storage_flag["active"] is False
    assert "No configured battery power or SOC boundary" in storage_flag["explanation"]


@pytest.mark.parametrize("price,method,cost", [(-10.0, "forward", -960.0), (10.0, "backward", 960.0)])
def test_price_boundaries_use_valid_one_sided_cost_elasticity(price: float, method: str, cost: float) -> None:
    result = terminal_sensitivity(
        {
            **terminal_defaults(),
            "pvKw": 0,
            "batteryKwh": 0,
            "batteryKw": 0,
            "loadKw": 10,
            "gridKw": 4,
            "importPrice": price,
        }
    )
    # With 4 kW imported in each of the 24 hours, cost is 96 * price.
    assert result["baseline"]["metrics"]["periodCost"] == pytest.approx(cost)
    row = next(row for row in result["rows"] if row["parameter"] == "importPrice")
    assert row["method"] == method
    assert row["periodCostElasticity"] == pytest.approx(1, rel=1e-9, abs=1e-12)
    assert row["unservedKwhElasticity"] == pytest.approx(0, abs=1e-12)
    assert row["error"] is None
