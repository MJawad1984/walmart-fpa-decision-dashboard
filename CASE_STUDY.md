# Public-data FP&A decision dashboard

I built a reproducible historical finance dashboard from Walmart's public SEC filings and earnings releases. It compares FY2025 initial public guidance with outcomes on matching measurement bases and connects FY2024–FY2026 sales, operating cash flow, capital expenditure and working capital.

## Business question

Did the company exceed its initial public guidance, and how did growth translate into cash after reinvestment?

The dashboard uses public management guidance, not an internal budget. All financial amounts are USD millions in the input tables. Presentation charts use USD billions.

## What I found during assurance

The previous draft compared constant-currency growth guidance with reported-currency actuals. I corrected net sales growth to 677,736 / 642,637 − 1, or 5.46%. For operating income, the initial guidance used an adjusted baseline. I compared 29,746 of adjusted constant-currency operating income with the 27,105 adjusted baseline, producing 9.74% growth.

The conclusions remain above the initial 3%–4% sales range and 4%–6% operating-income range. The measurement correction changes the size of the variance and makes the comparison defensible.

FY2025 adjusted EPS was $2.51 against an initial $2.23–$2.37 range. Capital expenditure was 3.53% of reported net sales against approximately 3.0%–3.5% initial guidance. I classify that last result as above range and requiring capital-allocation review. Higher expenditure is not automatically favourable.

FY2026 reported net sales were $706.413bn. Operating cash flow was $41.565bn and payments for property and equipment were $26.642bn, leaving $14.923bn of free cash flow. The derived cash-conversion cycle moved from 5.091 days in FY2024 to 3.598 in FY2025 and 3.268 in FY2026, using average balances and a configurable 365-day basis.

## Deliverables and validation

- Editable Excel dashboard with three native charts, supporting calculations and source inputs.
- Deterministic Python/Pandas calculation engine, explicit basis validation and configurable controls.
- 27 acceptance checks passed, including the existing forecast tests and new historical release controls. These checks do not establish complete accounting assurance of the forecast or DCF.
- Workbook formula error scan returned no matches. A changed day-basis input doubled the calculated cash-cycle days; the original input was restored. Python and workbook guidance calculations reconciled.
- SQLite deterministic-run record contains SHA-256 input, rules and output hashes. The exact 10-field LLM governance schema is present with zero calls. No external model API was used.

## Scope and limitations

This historical release uses official public source values and deterministic derivations. It contains no synthetic transactions, paid-course dataset, employer-confidential information or client data. It does not imply employment by, endorsement by, or access to internal data from Walmart.

The existing linked forecast and DCF remain separate modelling demonstrations. A balanced forecast alone does not establish sound lease, minority-interest, financing or valuation treatment. Further finance review is required before promoting those modules as assured models. No Power BI `.pbix` is included; the delivered dashboard is Excel.

## Sources

Source URLs and document purposes are recorded in [source_registry.yaml](source_registry.yaml). The relevant release sections are FY2024 Q4 guidance page 5, FY2025 Q4 constant currency page 13, adjusted operating income page 14 and adjusted EPS page 16. FY2026 financial statement amounts were checked against the FY2026 10-K. FY2023 opening working-capital balances were checked against the FY2024 10-K.

## Reproduce

```bash
python -m pip install -r requirements.txt
python run_acceptance.py
python scripts/prepare_dashboard.py
```

The Excel authoring source is `scripts/build_dashboard.mjs`. It uses the Codex artifact-tool runtime. The exported workbook is usable in Excel without that authoring runtime. The standard Python acceptance and data preparation commands do not need an API key or network access.
