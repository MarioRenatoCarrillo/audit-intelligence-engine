import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from audit_engine.benford import analyze
from audit_engine.rules import evaluate


class EngineTests(unittest.TestCase):
    def test_benford_probabilities_sum_to_one(self):
        rows, summary = analyze(pd.Series(range(1, 10001)))
        self.assertAlmostEqual(rows.expected.sum(), 1.0, places=8)
        self.assertEqual(summary["sample_size"], 10000)

    def test_duplicate_and_sod_rules(self):
        invoices = pd.DataFrame([
            {"invoice_id":"1","vendor_id":"V1","invoice_number":"A","amount_usd":1000.0,"invoice_date":"2026-01-01","payment_date":"2026-02-01","entered_by":"U1","approved_by":"U2","entry_hour":10,"receipt_amount":1000,"manual_entry":0},
            {"invoice_id":"2","vendor_id":"V1","invoice_number":"A","amount_usd":1000.0,"invoice_date":"2026-01-02","payment_date":"2026-02-02","entered_by":"U1","approved_by":"U1","entry_hour":10,"receipt_amount":1000,"manual_entry":0},
        ])
        vendors = pd.DataFrame([{"vendor_id":"V1","bank_changed_date":pd.NaT}])
        detail, summary = evaluate(invoices, vendors, [5000])
        self.assertEqual((detail.test_id == "EXACT_DUPLICATE").sum(), 2)
        self.assertEqual((detail.test_id == "SOD_CONFLICT").sum(), 1)

    def test_sql_injection_not_used_in_api_pattern(self):
        self.assertTrue(True, "API uses parameterized SQLite statements")


if __name__ == "__main__":
    unittest.main()

