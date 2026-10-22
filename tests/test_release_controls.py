import copy
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from analysis import load_rules, load_financials, load_guidance, calculate_working_capital, assess_guidance

class ReleaseControls(unittest.TestCase):
    def test_missing_baseline(self):
        with self.assertRaisesRegex(ValueError, 'EXCEPTION_PENDING_REVIEW'):
            calculate_working_capital(load_financials().iloc[1:], load_rules())

    def test_duplicate_year(self):
        frame = load_financials()
        frame.loc[1, 'fiscal_year'] = frame.loc[0, 'fiscal_year']
        with self.assertRaisesRegex(ValueError, 'EXCEPTION_PENDING_REVIEW'):
            calculate_working_capital(frame, load_rules())

    def test_boundary_within_range(self):
        frame = load_guidance()
        frame['actual'] = frame['guidance_high']
        self.assertEqual(set(assess_guidance(frame, load_rules())['status']), {'WITHIN_GUIDANCE'})

    def test_capex_review(self):
        result = assess_guidance(load_guidance(), load_rules()).set_index('metric')
        self.assertEqual(result.loc['Capital expenditures as pct of net sales', 'interpretation'], 'REVIEW_CAPITAL_ALLOCATION')

    def test_source_reconciliations(self):
        frame = load_guidance().set_index('metric')
        self.assertAlmostEqual(frame.loc['Net sales growth', 'actual'], 677736 / 642637 - 1)
        self.assertAlmostEqual(frame.loc['Operating income growth', 'actual'], 29746 / 27105 - 1)
        self.assertAlmostEqual(frame.loc['Capital expenditures as pct of net sales', 'actual'], 23783 / 674538)

    def test_external_day_basis(self):
        rules = load_rules()
        base = calculate_working_capital(load_financials(), rules)
        changed = copy.deepcopy(rules)
        changed['calendar']['days_per_year'] *= 2
        result = calculate_working_capital(load_financials(), changed)
        for column in ['dso_days', 'dio_days', 'dpo_days', 'cash_conversion_cycle_days']:
            np.testing.assert_allclose(result[column], base[column] * 2, atol=0.002)


def bad_financial(column, value):
    def check(self):
        frame = load_financials()
        frame.loc[0, column] = value
        with self.assertRaisesRegex(ValueError, 'EXCEPTION_PENDING_REVIEW'):
            calculate_working_capital(frame, load_rules())
    return check

for label, column, value in [('sales_zero','net_sales',0), ('cogs_zero','cost_of_sales',0), ('sales_negative','net_sales',-1), ('baseline_inventory_missing','inventory',np.nan), ('receivables_infinite','receivables',np.inf)]:
    setattr(ReleaseControls, 'test_' + label, bad_financial(column, value))


def bad_guidance(column, value):
    def check(self):
        frame = load_guidance()
        frame.loc[0, column] = value
        with self.assertRaisesRegex(ValueError, 'EXCEPTION_PENDING_REVIEW'):
            assess_guidance(frame, load_rules())
    return check

for label, column, value in [('actual_missing','actual',np.nan), ('actual_infinite','actual',np.inf), ('inverted_range','guidance_low',0.5), ('wrong_midpoint','guidance_mid',0.9), ('reported_currency_mismatch','basis','REPORTED_CURRENCY'), ('missing_basis','basis',''), ('unknown_basis','basis','UNKNOWN')]:
    setattr(ReleaseControls, 'test_' + label, bad_guidance(column, value))
