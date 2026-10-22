from __future__ import annotations

from pathlib import Path
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


def load_balance_sheet_base() -> dict[str, float]:
    frame = pd.read_csv(DATA_DIR / "fy2026_balance_sheet.csv")
    return dict(zip(frame["line_item"], frame["amount_usd_mn"].astype(float)))


def load_valuation_inputs() -> dict[str, float]:
    frame = pd.read_csv(DATA_DIR / "valuation_inputs.csv")
    return dict(zip(frame["metric"], frame["value"].astype(float)))


def historical_drivers(financials: pd.DataFrame, rules: dict) -> dict[str, float]:
    hist = financials[financials["fiscal_year"].between(2024, 2026)].copy()
    hist["membership_other"] = hist["total_revenue"] - hist["net_sales"]
    hist["operating_expense"] = hist["total_revenue"] - hist["cost_of_sales"] - hist["operating_income"]

    days = rules["calendar"]["days_per_year"]
    indexed = financials.set_index("fiscal_year")
    dso, dio, dpo = [], [], []
    for year in (2024, 2025, 2026):
        current = indexed.loc[year]
        prior = indexed.loc[year - 1]
        dso.append(((prior["receivables"] + current["receivables"]) / 2) / current["net_sales"] * days)
        dio.append(((prior["inventory"] + current["inventory"]) / 2) / current["cost_of_sales"] * days)
        dpo.append(((prior["accounts_payable"] + current["accounts_payable"]) / 2) / current["cost_of_sales"] * days)

    return {
        "membership_other_pct_sales": (hist["membership_other"] / hist["net_sales"]).mean(),
        "cost_of_sales_pct_sales": (hist["cost_of_sales"] / hist["net_sales"]).mean(),
        "operating_expense_pct_sales": (hist["operating_expense"] / hist["net_sales"]).mean(),
        "depreciation_pct_sales": (hist["depreciation_amortization"] / hist["net_sales"]).mean(),
        "dso_days": sum(dso) / len(dso),
        "dio_days": sum(dio) / len(dio),
        "dpo_days": sum(dpo) / len(dpo),
    }


def _asset_total(bs: dict[str, float]) -> float:
    return sum(
        bs[key]
        for key in (
            "cash_and_cash_equivalents",
            "receivables",
            "inventory",
            "prepaid_and_other_current_assets",
            "property_plant_equipment_net",
            "operating_and_finance_lease_assets",
            "goodwill",
            "other_long_term_assets",
        )
    )


def _liability_equity_total(bs: dict[str, float]) -> float:
    return sum(
        bs[key]
        for key in (
            "interest_bearing_debt_excluding_finance_leases",
            "accounts_payable",
            "accrued_liabilities",
            "accrued_income_taxes",
            "operating_and_finance_lease_obligations",
            "deferred_income_taxes_and_other",
            "redeemable_noncontrolling_interest",
            "total_shareholders_equity",
        )
    )


def forecast_statements() -> pd.DataFrame:
    rules = load_rules()
    financials = load_financials()
    drivers = historical_drivers(financials, rules)
    base = load_balance_sheet_base()

    tolerance = rules["model_controls"]["reconciliation_tolerance"]
    days = rules["calendar"]["days_per_year"]
    forecast_rules = rules["forecast"]

    base_asset_total = _asset_total(base)
    base_liability_equity_total = _liability_equity_total(base)
    if abs(base_asset_total - base_liability_equity_total) > tolerance:
        raise ValueError("EXCEPTION_PENDING_REVIEW: FY2026 base balance sheet does not balance")

    base_sales = float(financials.loc[financials["fiscal_year"] == 2026, "net_sales"].iloc[0])
    ratios = {
        "prepaid_pct_sales": base["prepaid_and_other_current_assets"] / base_sales,
        "lease_asset_pct_sales": base["operating_and_finance_lease_assets"] / base_sales,
        "other_asset_pct_sales": base["other_long_term_assets"] / base_sales,
        "accrued_pct_sales": base["accrued_liabilities"] / base_sales,
        "tax_payable_pct_sales": base["accrued_income_taxes"] / base_sales,
        "lease_liability_pct_sales": base["operating_and_finance_lease_obligations"] / base_sales,
        "other_liability_pct_sales": base["deferred_income_taxes_and_other"] / base_sales,
    }

    if forecast_rules["debt_strategy"] != "FLAT_NOMINAL_DEBT":
        raise ValueError("Unsupported debt strategy")

    prior_sales = base_sales
    prior_bs = base.copy()
    prior_core_nwc = (
        prior_bs["receivables"]
        + prior_bs["inventory"]
        + prior_bs["prepaid_and_other_current_assets"]
        - prior_bs["accounts_payable"]
        - prior_bs["accrued_liabilities"]
        - prior_bs["accrued_income_taxes"]
    )

    rows: list[dict[str, float]] = []
    for year in forecast_rules["years"]:
        year = int(year)
        growth = float(forecast_rules["net_sales_growth"][year])
        capex_pct = float(forecast_rules["capex_pct_net_sales"][year])
        tax_rate = float(forecast_rules["tax_rate"])
        interest_rate = float(forecast_rules["net_interest_rate_on_prior_debt_and_leases"])
        payout = float(forecast_rules["dividend_payout_pct_net_income"])

        net_sales = prior_sales * (1 + growth)
        membership_other = net_sales * drivers["membership_other_pct_sales"]
        total_revenue = net_sales + membership_other
        cost_of_sales = net_sales * drivers["cost_of_sales_pct_sales"]
        operating_expense = net_sales * drivers["operating_expense_pct_sales"]
        operating_income = total_revenue - cost_of_sales - operating_expense
        net_interest = (
            prior_bs["interest_bearing_debt_excluding_finance_leases"]
            + prior_bs["operating_and_finance_lease_obligations"]
        ) * interest_rate
        pretax_income = operating_income - net_interest
        income_tax = max(pretax_income, 0.0) * tax_rate
        net_income = pretax_income - income_tax
        depreciation = net_sales * drivers["depreciation_pct_sales"]
        capex = net_sales * capex_pct
        dividends = max(net_income, 0.0) * payout

        receivables = net_sales * drivers["dso_days"] / days
        inventory = cost_of_sales * drivers["dio_days"] / days
        prepaid = net_sales * ratios["prepaid_pct_sales"]
        ppe = prior_bs["property_plant_equipment_net"] + capex - depreciation
        lease_assets = net_sales * ratios["lease_asset_pct_sales"]
        goodwill = prior_bs["goodwill"]
        other_assets = net_sales * ratios["other_asset_pct_sales"]

        debt = prior_bs["interest_bearing_debt_excluding_finance_leases"]
        accounts_payable = cost_of_sales * drivers["dpo_days"] / days
        accrued_liabilities = net_sales * ratios["accrued_pct_sales"]
        accrued_income_taxes = net_sales * ratios["tax_payable_pct_sales"]
        lease_obligations = net_sales * ratios["lease_liability_pct_sales"]
        deferred_and_other = net_sales * ratios["other_liability_pct_sales"]
        redeemable_nci = prior_bs["redeemable_noncontrolling_interest"]
        equity = prior_bs["total_shareholders_equity"] + net_income - dividends

        delta_operating_assets = (
            (receivables - prior_bs["receivables"])
            + (inventory - prior_bs["inventory"])
            + (prepaid - prior_bs["prepaid_and_other_current_assets"])
            + (lease_assets - prior_bs["operating_and_finance_lease_assets"])
            + (other_assets - prior_bs["other_long_term_assets"])
        )
        delta_operating_liabilities = (
            (accounts_payable - prior_bs["accounts_payable"])
            + (accrued_liabilities - prior_bs["accrued_liabilities"])
            + (accrued_income_taxes - prior_bs["accrued_income_taxes"])
            + (lease_obligations - prior_bs["operating_and_finance_lease_obligations"])
            + (deferred_and_other - prior_bs["deferred_income_taxes_and_other"])
        )

        operating_cash_flow = net_income + depreciation - delta_operating_assets + delta_operating_liabilities
        investing_cash_flow = -capex
        financing_cash_flow = (debt - prior_bs["interest_bearing_debt_excluding_finance_leases"]) - dividends
        ending_cash = (
            prior_bs["cash_and_cash_equivalents"]
            + operating_cash_flow
            + investing_cash_flow
            + financing_cash_flow
        )

        current_bs = {
            "cash_and_cash_equivalents": ending_cash,
            "receivables": receivables,
            "inventory": inventory,
            "prepaid_and_other_current_assets": prepaid,
            "property_plant_equipment_net": ppe,
            "operating_and_finance_lease_assets": lease_assets,
            "goodwill": goodwill,
            "other_long_term_assets": other_assets,
            "interest_bearing_debt_excluding_finance_leases": debt,
            "accounts_payable": accounts_payable,
            "accrued_liabilities": accrued_liabilities,
            "accrued_income_taxes": accrued_income_taxes,
            "operating_and_finance_lease_obligations": lease_obligations,
            "deferred_income_taxes_and_other": deferred_and_other,
            "redeemable_noncontrolling_interest": redeemable_nci,
            "total_shareholders_equity": equity,
        }

        balance_check = _asset_total(current_bs) - _liability_equity_total(current_bs)
        if abs(balance_check) > tolerance:
            raise ValueError(f"EXCEPTION_PENDING_REVIEW: forecast balance sheet out by {balance_check}")

        core_nwc = (
            receivables + inventory + prepaid
            - accounts_payable - accrued_liabilities - accrued_income_taxes
        )
        delta_core_nwc = core_nwc - prior_core_nwc
        unlevered_fcf = operating_income * (1 - tax_rate) + depreciation - capex - delta_core_nwc

        rows.append({
            "fiscal_year": year,
            "net_sales": net_sales,
            "membership_and_other_income": membership_other,
            "total_revenue": total_revenue,
            "cost_of_sales": cost_of_sales,
            "operating_expense": operating_expense,
            "operating_income": operating_income,
            "net_interest": net_interest,
            "pretax_income": pretax_income,
            "income_tax": income_tax,
            "net_income": net_income,
            "depreciation_amortization": depreciation,
            "capex": capex,
            "operating_cash_flow": operating_cash_flow,
            "investing_cash_flow": investing_cash_flow,
            "financing_cash_flow": financing_cash_flow,
            "ending_cash": ending_cash,
            "receivables": receivables,
            "inventory": inventory,
            "accounts_payable": accounts_payable,
            "property_plant_equipment_net": ppe,
            "interest_bearing_debt_excluding_finance_leases": debt,
            "total_shareholders_equity": equity,
            "total_assets": _asset_total(current_bs),
            "total_liabilities_and_equity": _liability_equity_total(current_bs),
            "balance_check": balance_check,
            "core_operating_nwc": core_nwc,
            "delta_core_operating_nwc": delta_core_nwc,
            "unlevered_fcf": unlevered_fcf,
        })

        prior_sales = net_sales
        prior_bs = current_bs
        prior_core_nwc = core_nwc

    return pd.DataFrame(rows)


def dcf_value(forecast: pd.DataFrame, wacc: float, terminal_growth: float, rules: dict, inputs: dict[str, float]) -> dict[str, float]:
    if rules["model_controls"]["terminal_growth_must_be_below_wacc"] and terminal_growth >= wacc:
        raise ValueError("EXCEPTION_PENDING_REVIEW: terminal growth must be below WACC")

    explicit_pv = 0.0
    for period, fcf in enumerate(forecast["unlevered_fcf"], start=1):
        explicit_pv += float(fcf) / ((1 + wacc) ** period)

    final_fcf = float(forecast["unlevered_fcf"].iloc[-1])
    terminal_value = final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
    terminal_pv = terminal_value / ((1 + wacc) ** len(forecast))
    enterprise_value = explicit_pv + terminal_pv

    debt = inputs["interest_bearing_debt_excluding_finance_leases"]
    if rules["valuation"]["include_lease_obligations_as_debt"]:
        debt += inputs["operating_and_finance_lease_obligations"]
    net_debt = debt - inputs["cash_and_cash_equivalents"]
    equity_value = enterprise_value - net_debt
    value_per_share = equity_value / inputs["shares_outstanding"]

    return {
        "wacc": wacc,
        "terminal_growth": terminal_growth,
        "explicit_fcf_pv": explicit_pv,
        "terminal_value_pv": terminal_pv,
        "enterprise_value": enterprise_value,
        "net_debt_including_leases": net_debt,
        "equity_value": equity_value,
        "value_per_share": value_per_share,
    }


def valuation_outputs(forecast: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rules = load_rules()
    inputs = load_valuation_inputs()
    value_rules = rules["valuation"]

    base = dcf_value(
        forecast,
        float(value_rules["wacc_base"]),
        float(value_rules["terminal_growth_base"]),
        rules,
        inputs,
    )
    base_frame = pd.DataFrame([base])

    sensitivity_rows = []
    for wacc in value_rules["wacc_sensitivity"]:
        for terminal_growth in value_rules["terminal_growth_sensitivity"]:
            result = dcf_value(forecast, float(wacc), float(terminal_growth), rules, inputs)
            sensitivity_rows.append(result)
    sensitivity = pd.DataFrame(sensitivity_rows)
    return base_frame, sensitivity


def export_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    forecast = forecast_statements()
    base_valuation, sensitivity = valuation_outputs(forecast)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    forecast.to_csv(OUTPUT_DIR / "linked_three_statement_forecast.csv", index=False)
    base_valuation.to_csv(OUTPUT_DIR / "dcf_base_case.csv", index=False)
    sensitivity.to_csv(OUTPUT_DIR / "dcf_sensitivity.csv", index=False)
    return forecast, base_valuation, sensitivity


if __name__ == "__main__":
    forecast_frame, base_value, sensitivity_frame = export_outputs()
    print(forecast_frame.to_string(index=False))
    print()
    print(base_value.to_string(index=False))
    print()
    print(sensitivity_frame[["wacc", "terminal_growth", "value_per_share"]].to_string(index=False))
