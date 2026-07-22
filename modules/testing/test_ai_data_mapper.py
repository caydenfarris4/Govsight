"""
Unit tests for the AI data massaging layer
(modules/data_adapter/ai_data_mapper.py and ingestion_pipeline.py).

Covers: sample profiling, heuristic mapping quality, every whitelisted
transform, required-field validation, mapping persistence/approval
versioning, and idempotent canonical upserts. The AI path is exercised
via a stubbed model response so no API key or network is needed.
"""

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from modules.data_adapter.ai_data_mapper import (  # noqa: E402
    MappingEngine,
    MappingStore,
    TransformExecutor,
    profile_sample,
)
from modules.data_adapter.ingestion_pipeline import IngestionPipeline  # noqa: E402

ERP_SAMPLE = [
    {"Acct No": "10-20-5300", "Acct Description": "Police Professional Services",
     "AcctType": "Expense", "Dept Name": "Police", "Fund No": "10",
     "FY": "FY2025", "Adopted Budget": "$125,000.00", "YTD Amount": "(3,500.00)"},
    {"Acct No": "10-00-4100", "Acct Description": "Property Tax",
     "AcctType": "Revenue", "Dept Name": "General Revenue", "Fund No": "10",
     "FY": "FY2025", "Adopted Budget": "$2,819,000", "YTD Amount": "1,080,802.68"},
]


class TestProfiling(unittest.TestCase):
    def test_profile_infers_types_and_examples(self):
        profile = {f["name"]: f for f in profile_sample(ERP_SAMPLE)}
        self.assertEqual(profile["Adopted Budget"]["inferred_type"], "number")
        self.assertEqual(profile["Acct No"]["inferred_type"], "string")
        self.assertIn("10-20-5300", profile["Acct No"]["examples"])

    def test_empty_sample(self):
        self.assertEqual(profile_sample([]), [])


class TestHeuristicMapping(unittest.TestCase):
    def setUp(self):
        self.engine = MappingEngine()

    def test_maps_all_required_gl_fields(self):
        proposal = self.engine.propose("gl_accounts", ERP_SAMPLE)
        self.assertEqual(proposal["method"], "heuristic")
        self.assertEqual(proposal["unmapped_required"], [])
        by_target = {m["target"]: m for m in proposal["mappings"]}
        # The global-assignment matcher must not confuse similar names
        self.assertEqual(by_target["account_number"]["source"], "Acct No")
        self.assertEqual(by_target["account_name"]["source"], "Acct Description")
        self.assertEqual(by_target["department"]["source"], "Dept Name")
        self.assertEqual(by_target["fiscal_year"]["transform"], "to_integer")
        self.assertEqual(by_target["budget_amount"]["transform"], "to_number")

    def test_unknown_entity_raises(self):
        with self.assertRaises(ValueError):
            self.engine.propose("not_an_entity", ERP_SAMPLE)

    def test_ai_path_sanitizes_bad_mappings(self):
        ai_response = json.dumps({"mappings": [
            {"target": "account_number", "source": "Acct No",
             "transform": "direct", "confidence": 0.99, "note": "ok"},
            {"target": "account_name", "source": "NoSuchField",
             "transform": "direct", "confidence": 0.9},      # bad source: dropped
            {"target": "not_a_field", "source": "Acct No",
             "transform": "direct", "confidence": 0.9},      # bad target: dropped
            {"target": "budget_amount", "source": "Adopted Budget",
             "transform": "eval_code", "confidence": 0.9},   # bad transform: dropped
        ]})
        with patch.object(MappingEngine, "_call_openai", return_value=ai_response), \
             patch.object(MappingEngine, "_call_anthropic", return_value=None):
            proposal = self.engine.propose("gl_accounts", ERP_SAMPLE)
        self.assertEqual(proposal["method"], "ai")
        targets = {m["target"] for m in proposal["mappings"]}
        self.assertEqual(targets, {"account_number"})
        # Unmapped required fields must be surfaced for human review
        self.assertIn("account_name", proposal["unmapped_required"])


class TestTransforms(unittest.TestCase):
    def setUp(self):
        self.ex = TransformExecutor()

    def _one(self, transform, rec, source="f", params=None):
        return self.ex._apply_one(
            {"target": "t", "source": source, "transform": transform,
             "params": params or {}}, rec)

    def test_to_number_currency_and_negatives(self):
        self.assertEqual(self._one("to_number", {"f": "$1,234.56"}), 1234.56)
        self.assertEqual(self._one("to_number", {"f": "(2,500.00)"}), -2500.0)
        self.assertEqual(self._one("to_number", {"f": "150-"}), -150.0)

    def test_to_integer_fy_prefix(self):
        self.assertEqual(self._one("to_integer", {"f": "FY2025"}), 2025)

    def test_to_date_formats(self):
        for raw in ("2026-07-15", "07/15/2026", "20260715"):
            self.assertEqual(self._one("to_date", {"f": raw}), "2026-07-15")
        with self.assertRaises(ValueError):
            self._one("to_date", {"f": "not a date"})

    def test_signed_amount(self):
        rec = {"amt": "1,250.00", "dc": "CR"}
        self.assertEqual(self._one("signed_amount", rec, source=["amt", "dc"]), -1250.0)
        rec["dc"] = "DR"
        self.assertEqual(self._one("signed_amount", rec, source=["amt", "dc"]), 1250.0)

    def test_constant_concat_map_values_boolean(self):
        self.assertEqual(self._one("constant", {}, params={"value": "Expense"}), "Expense")
        self.assertEqual(self._one("concat", {"a": "10", "b": "20"},
                                   source=["a", "b"], params={"separator": "-"}), "10-20")
        self.assertEqual(self._one("map_values", {"f": "E"},
                                   params={"values": {"E": "Expense"}}), "Expense")
        self.assertTrue(self._one("to_boolean", {"f": "Yes"}))
        self.assertFalse(self._one("to_boolean", {"f": "N"}))

    def test_required_field_validation_collects_row_errors(self):
        mappings = [
            {"target": "account_number", "source": "Acct No", "transform": "direct", "params": {}},
            {"target": "account_name", "source": "Acct Description", "transform": "direct", "params": {}},
            {"target": "account_type", "source": "AcctType", "transform": "direct", "params": {}},
            {"target": "fiscal_year", "source": "FY", "transform": "to_integer", "params": {}},
            {"target": "budget_amount", "source": "Adopted Budget", "transform": "to_number", "params": {}},
            {"target": "ytd_actual", "source": "YTD Amount", "transform": "to_number", "params": {}},
        ]
        bad_row = dict(ERP_SAMPLE[0], **{"Adopted Budget": "", "Acct No": ""})
        result = TransformExecutor().apply("gl_accounts", mappings,
                                           [ERP_SAMPLE[0], bad_row])
        self.assertEqual(result["succeeded"], 1)
        self.assertEqual(result["failed"], 1)
        errors = " ".join(result["errors"][0]["errors"])
        self.assertIn("budget_amount", errors)
        self.assertIn("account_number", errors)


class TestStoreAndPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = MappingStore(db_path=os.path.join(self.tmp, "map.db"))
        self.canonical = os.path.join(self.tmp, "canon.db")
        self.pipe = IngestionPipeline(store=self.store,
                                      canonical_db_path=self.canonical)

    def test_approval_versioning_retires_previous(self):
        p1 = self.pipe.propose_mapping("src", "csv", "gl_accounts",
                                       sample_records=ERP_SAMPLE)
        self.store.approve_mapping(p1["mapping_id"], "tester")
        p2 = self.pipe.propose_mapping("src", "csv", "gl_accounts",
                                       sample_records=ERP_SAMPLE)
        self.store.approve_mapping(p2["mapping_id"], "tester")
        approved = self.store.get_approved_mapping(p2["source_id"], "gl_accounts")
        self.assertEqual(approved["version"], 2)
        versions = self.store.list_mappings(p2["source_id"])
        statuses = {m["version"]: m["status"] for m in versions}
        self.assertEqual(statuses[1], "retired")
        self.assertEqual(statuses[2], "approved")

    def test_upsert_is_idempotent(self):
        p = self.pipe.propose_mapping("src", "csv", "gl_accounts",
                                      sample_records=ERP_SAMPLE)
        result = TransformExecutor().apply("gl_accounts", p["mappings"], ERP_SAMPLE)
        n1 = self.pipe._upsert_canonical("gl_accounts", result["records"])
        n2 = self.pipe._upsert_canonical("gl_accounts", result["records"])
        self.assertEqual((n1, n2), (2, 2))
        conn = sqlite3.connect(self.canonical)
        count = conn.execute("SELECT COUNT(*) FROM gl_accounts").fetchone()[0]
        conn.close()
        self.assertEqual(count, 2)  # re-sync never duplicates

    def test_sync_requires_approved_mapping(self):
        self.store.register_source("srcX", "csv", {"content": "a,b\n1,2\n"})
        with self.assertRaises(ValueError):
            self.pipe.run_sync("srcX", "gl_accounts")


if __name__ == "__main__":
    unittest.main()
