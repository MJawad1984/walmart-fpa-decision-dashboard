from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CONFIG_PATH = ROOT / "config" / "rules.yaml"
OUTPUT_DIR = ROOT / "generated"


def load_rules() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_financials() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "walmart_public_financials.csv")


def load_guidance() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "fy25_initial_guidance.csv")


def validate_financials(df: pd.DataFrame, rules: dict) -> None:
    required = [
        "fiscal_year", "net_sales", "cost_of_sales", "receivables",
        "inventory", "accounts_payable"
    ]
    missing_columns = [c for c in required if c not in df.columns]
    if missing_columns:
        raise ValueError(f"EXCEPTION_PENDING_REVIEW: Missing required columns: {missing_columns}")

    fy = df["fiscal_year"].astype(int).tolist()
    if fy != sorted(fy) or len(fy) != len(set(fy)):
        raise ValueError("EXCEPTION_PENDING_REVIEW: Fiscal years must be unique and ascending")

    history = rules['history']
    expected = list(range(history['baseline_year'], history['analysis_end_year'] + 1))
    if fy != expected:
        raise ValueError('EXCEPTION_PENDING_REVIEW: incomplete fiscal-year history')
    required_rows = df[required]
    if not np.isfinite(required_rows.to_numpy(dtype=float)).all():
        status = rules["model_controls"]["missing_value_status"]
        raise ValueError(status)
    if (df[['net_sales', 'cost_of_sales']] <= 0).any().any():
        raise ValueError('EXCEPTION_PENDING_REVIEW: non-positive sales or cost denominator')


def calculate_working_capital(df: pd.DataFrame, rules: dict) -> pd.DataFrame:
    validate_financials(df, rules)
    days = rules["calendar"]["days_per_year"]
    decimals = rules["working_capital"]["rounding_decimals"]

    rows = []
    indexed = df.set_index("fiscal_year")
    for year in indexed.index:
        prior_year = year - 1
        if prior_year not in indexed.index or year < rules['history']['analysis_start_year']:
            continue

        current = indexed.loc[year]
        prior = indexed.loc[prior_year]

        avg_ar = (prior["receivables"] + current["receivables"]) / 2
        avg_inventory = (prior["inventory"] + current["inventory"]) / 2
        avg_ap = (prior["accounts_payable"] + current["accounts_payable"]) / 2

        dso = avg_ar / current["net_sales"] * days
        dio = avg_inventory / current["cost_of_sales"] * days
        dpo = avg_ap / current["cost_of_sales"] * days
        ccc = dso + dio - dpo

        rows.append({
            "fiscal_year": int(year),
            "dso_days": round(dso, decimals),
            "dio_days": round(dio, decimals),
            "dpo_days": round(dpo, decimals),
            "cash_conversion_cycle_days": round(ccc, decimals),
        })

    return pd.DataFrame(rows)


def assess_guidance(guidance: pd.DataFrame, rules: dict) -> pd.DataFrame:
    required = ['metric', 'guidance_low', 'guidance_high', 'guidance_mid', 'actual', 'basis', 'unit']
    if any(c not in guidance.columns for c in required):
        raise ValueError('EXCEPTION_PENDING_REVIEW: guidance columns missing')
    if guidance['metric'].duplicated().any() or set(guidance['metric']) != set(rules['guidance']['required_bases']):
        raise ValueError('EXCEPTION_PENDING_REVIEW: guidance metrics missing or duplicated')
    numeric = guidance[['guidance_low', 'guidance_high', 'guidance_mid', 'actual']]
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError('EXCEPTION_PENDING_REVIEW: non-finite guidance input')
    if (guidance['guidance_low'] > guidance['guidance_high']).any():
        raise ValueError('EXCEPTION_PENDING_REVIEW: inverted guidance range')
    expected_mid = (guidance['guidance_low'] + guidance['guidance_high']) / 2
    if ((guidance['guidance_mid'] - expected_mid).abs() > rules['guidance']['zero_denominator_tolerance']).any():
        raise ValueError('EXCEPTION_PENDING_REVIEW: inconsistent guidance midpoint')
    for _, row in guidance.iterrows():
        if row['basis'] != rules['guidance']['required_bases'][row['metric']]:
            raise ValueError('EXCEPTION_PENDING_REVIEW: guidance/actual basis mismatch')
    labels = rules["guidance"]["labels"]
    materiality = rules["guidance"]["midpoint_materiality_pct"]
    zero_tol = rules["guidance"]["zero_denominator_tolerance"]

    result = guidance.copy()

    def classify(row: pd.Series) -> str:
        actual = row["actual"]
        if actual > row["guidance_high"]:
            return labels["above"]
        if actual < row["guidance_low"]:
            return labels["below"]
        return labels["within"]

    result["status"] = result.apply(classify, axis=1)
    result["variance_to_mid"] = result["actual"] - result["guidance_mid"]
    denominator = result["guidance_mid"].abs()
    result["variance_to_mid_pct"] = result["variance_to_mid"] / denominator.where(denominator > zero_tol)
    result["material_variance"] = result["variance_to_mid_pct"].abs() >= materiality
    result['interpretation'] = result.apply(lambda r: rules['guidance']['above_range_interpretation'][r['metric']] if r['status'] == labels['above'] else 'REVIEW_IN_CONTEXT', axis=1)
    return result


def export_outputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    rules = load_rules()
    financials = load_financials()
    guidance = load_guidance()

    wc = calculate_working_capital(financials, rules)
    guidance_assessment = assess_guidance(guidance, rules)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    wc.to_csv(OUTPUT_DIR / "working_capital_metrics.csv", index=False)
    guidance_assessment.to_csv(OUTPUT_DIR / "fy25_guidance_assessment.csv", index=False)
    financials.to_csv(OUTPUT_DIR / "power_bi_fact_financials.csv", index=False)

    return wc, guidance_assessment


if __name__ == "__main__":
    working_capital, guidance_assessment = export_outputs()
    print(working_capital.to_string(index=False))
    print()
    print(guidance_assessment.to_string(index=False))
