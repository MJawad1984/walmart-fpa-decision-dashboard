from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from analysis import load_rules, load_financials, load_guidance, calculate_working_capital, assess_guidance


def test_working_capital_metrics_match_expected_values():
    rules = load_rules()
    wc = calculate_working_capital(load_financials(), rules).set_index("fiscal_year")

    assert wc.loc[2024, "dso_days"] == 4.751
    assert wc.loc[2024, "dio_days"] == 41.504
    assert wc.loc[2024, "dpo_days"] == 41.164
    assert wc.loc[2024, "cash_conversion_cycle_days"] == 5.091

    assert wc.loc[2025, "cash_conversion_cycle_days"] == 3.598
    assert wc.loc[2026, "cash_conversion_cycle_days"] == 3.268


def test_cash_conversion_cycle_improves_across_period():
    rules = load_rules()
    wc = calculate_working_capital(load_financials(), rules)
    ccc = wc["cash_conversion_cycle_days"].tolist()
    assert ccc[0] > ccc[1] > ccc[2]


def test_fy25_initial_guidance_was_exceeded():
    rules = load_rules()
    result = assess_guidance(load_guidance(), rules)
    expected = rules["guidance"]["labels"]["above"]
    assert set(result["status"]) == {expected}


def test_material_guidance_variances_are_flagged():
    rules = load_rules()
    result = assess_guidance(load_guidance(), rules)
    assert result["material_variance"].all()
