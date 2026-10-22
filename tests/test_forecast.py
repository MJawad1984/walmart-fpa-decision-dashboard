from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from forecast import load_rules, load_valuation_inputs, forecast_statements, dcf_value


def test_linked_forecast_balances_each_year():
    rules = load_rules()
    forecast = forecast_statements()
    tolerance = rules["model_controls"]["reconciliation_tolerance"]
    assert forecast["balance_check"].abs().max() <= tolerance


def test_forecast_revenue_increases_each_year():
    forecast = forecast_statements()
    assert (forecast["net_sales"].diff().dropna() > 0).all()


def test_higher_wacc_reduces_dcf_value():
    rules = load_rules()
    forecast = forecast_statements()
    inputs = load_valuation_inputs()
    low = dcf_value(forecast, 0.06, 0.025, rules, inputs)["value_per_share"]
    high = dcf_value(forecast, 0.08, 0.025, rules, inputs)["value_per_share"]
    assert low > high


def test_higher_terminal_growth_increases_dcf_value():
    rules = load_rules()
    forecast = forecast_statements()
    inputs = load_valuation_inputs()
    low = dcf_value(forecast, 0.07, 0.02, rules, inputs)["value_per_share"]
    high = dcf_value(forecast, 0.07, 0.03, rules, inputs)["value_per_share"]
    assert high > low


def test_invalid_terminal_growth_halts():
    rules = load_rules()
    forecast = forecast_statements()
    inputs = load_valuation_inputs()
    try:
        dcf_value(forecast, 0.03, 0.03, rules, inputs)
    except ValueError as exc:
        assert "EXCEPTION_PENDING_REVIEW" in str(exc)
    else:
        raise AssertionError("Invalid terminal-growth/WACC combination did not halt")
