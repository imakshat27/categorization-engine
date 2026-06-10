import os
import tempfile
import unittest

import pandas as pd

from engine.training_data import (
    available_review_categories,
    build_training_record,
    build_transaction_id,
    load_review_records,
    select_review_candidates,
    upsert_review_records,
)


def review_row(**overrides):
    row = {
        "Bank": "Test Bank",
        "Bank Code": "TB01",
        "XN Date": "2026-06-10",
        "Cheque No": "",
        "Narration": "UPI/IRCTC/123456789/NA",
        "Normalized Narration": "UPI/IRCTC/123456789/NA",
        "Debits": 500.0,
        "Credits": None,
        "Direction": "OUT",
        "Mode": "UPI",
        "Protocol Family": "UPI_GENERIC",
        "Transaction Prefix": "UPI",
        "Transaction Subtype": "UNKNOWN",
        "Reference ID": "123456789",
        "Entity Name": "IRCTC",
        "Bank Name": "UNKNOWN",
        "UPI ID": "",
        "UPI Handle": "",
        "Parser Rule": "UPI_GENERIC",
        "Parser Confidence": 0.8,
        "Parse Quality": "MEDIUM",
        "Merchant": "IRCTC",
        "Entity Type": "TRAVEL",
        "Entity Role": "merchant",
        "Entity Confidence": 0.92,
        "Matched Entity Rule": "IRCTC",
        "Instrument Type": "UPI",
        "Intent Tags": "travel",
        "Movement Tags": "",
        "Bank Family": "UNKNOWN",
        "Category": "ELECTRONIC FUND TRANSFER",
        "Confidence": 0.62,
        "Decision Path": "protocol:generic_rail_transfer",
        "Conflicts": "rail_entity_ambiguity",
        "Matched Rule": "generic_rail_transfer",
        "Ranked Candidates": "ELECTRONIC FUND TRANSFER:0.672 | TRAVEL:0.652",
        "Alternative Categories": "TRAVEL:0.652",
        "Review Required": True,
        "Review Reason": "rail_entity_ambiguity",
        "Evidence Summary": "ELECTRONIC FUND TRANSFER <= protocol:generic_rail_transfer (0.82)",
    }
    row.update(overrides)
    return pd.Series(row)


class TrainingDataTests(unittest.TestCase):
    def test_training_record_uses_minimal_jsonl_schema(self):
        row = review_row()

        record = build_training_record(
            row,
            final_category="TRAVEL",
            feedback_source="unit_test",
            reviewer="tester",
            feedback_note="IRCTC should map to travel.",
            row_index=7,
            reviewed_at="2026-06-10T00:00:00+00:00",
        )

        self.assertEqual(
            record,
            {
                "bank": "Test Bank",
                "narration": "UPI/IRCTC/123456789/NA",
                "deterministic_category": "ELECTRONIC FUND TRANSFER",
                "deterministic_confidence": 0.62,
                "verified_category": "TRAVEL",
            },
        )

    def test_transaction_id_matches_minimal_jsonl_identity(self):
        row = review_row(Confidence=0.62)
        same_transaction = review_row(Confidence=0.91)
        different_narration = review_row(Narration="GST TAX PAYMENT")

        self.assertEqual(
            build_transaction_id(row),
            build_transaction_id(same_transaction),
        )
        self.assertNotEqual(
            build_transaction_id(row),
            build_transaction_id(different_narration),
        )

    def test_upsert_skips_duplicates_unless_update_is_explicit(self):
        row = review_row()
        first = build_training_record(
            row,
            final_category="ELECTRONIC FUND TRANSFER",
            reviewed_at="2026-06-10T00:00:00+00:00",
        )
        updated = build_training_record(
            row,
            final_category="TRAVEL",
            reviewed_at="2026-06-10T01:00:00+00:00",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "reviews.jsonl")

            stats = upsert_review_records([first], path=path)
            self.assertEqual(stats["inserted"], 1)

            stats = upsert_review_records([updated], path=path)
            self.assertEqual(stats["skipped_duplicates"], 1)
            records = load_review_records(path)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["verified_category"], "ELECTRONIC FUND TRANSFER")

            stats = upsert_review_records(
                [updated],
                path=path,
                allow_updates=True,
            )
            self.assertEqual(stats["updated"], 1)
            records = load_review_records(path)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["verified_category"], "TRAVEL")
            self.assertEqual(
                set(records[0]),
                {
                    "bank",
                    "narration",
                    "deterministic_category",
                    "deterministic_confidence",
                    "verified_category",
                },
            )

    def test_review_selection_prioritizes_informative_rows(self):
        rows = [
            review_row(
                Narration="UPI/RRN 111/UPI",
                **{
                    "Normalized Narration": "UPI/RRN 111/UPI",
                    "Reference ID": "111",
                    "Entity Name": "UNKNOWN",
                    "Merchant": "UNKNOWN",
                    "Entity Type": "UNKNOWN",
                    "Category": "ELECTRONIC FUND TRANSFER",
                    "Confidence": 0.92,
                    "Conflicts": "",
                    "Review Required": False,
                    "Ranked Candidates": "ELECTRONIC FUND TRANSFER:0.82",
                },
            ),
            review_row(
                Narration="LOCAL ENTRY",
                **{
                    "Normalized Narration": "LOCAL ENTRY",
                    "Reference ID": "",
                    "Entity Name": "UNKNOWN",
                    "Merchant": "UNKNOWN",
                    "Entity Type": "UNKNOWN",
                    "Category": "TRANSFER OUT",
                    "Confidence": 0.34,
                    "Conflicts": "weak_fallback",
                    "Review Required": True,
                    "Ranked Candidates": "TRANSFER OUT:0.34",
                },
            ),
            review_row(
                Narration="UPI/IRCTC/222/NA",
                **{
                    "Normalized Narration": "UPI/IRCTC/222/NA",
                    "Reference ID": "222",
                    "Category": "TRAVEL",
                    "Confidence": 0.78,
                    "Conflicts": "rail_entity_ambiguity",
                    "Review Required": True,
                    "Ranked Candidates": "TRAVEL:0.75 | ELECTRONIC FUND TRANSFER:0.72",
                },
            ),
        ]
        df = pd.DataFrame(rows)

        selected = select_review_candidates(df, hide_generic_high_confidence=True)

        self.assertNotIn("UPI/RRN 111/UPI", set(selected["Narration"]))
        self.assertIn("LOCAL ENTRY", set(selected["Narration"]))
        self.assertGreater(
            selected.iloc[0]["Review Priority"],
            selected.iloc[-1]["Review Priority"],
        )

    def test_available_review_categories_follow_active_filters(self):
        rows = [
            review_row(
                Narration="UPI/RRN 111/UPI",
                **{
                    "Normalized Narration": "UPI/RRN 111/UPI",
                    "Reference ID": "111",
                    "Entity Name": "UNKNOWN",
                    "Merchant": "UNKNOWN",
                    "Entity Type": "UNKNOWN",
                    "Category": "ELECTRONIC FUND TRANSFER",
                    "Confidence": 0.92,
                    "Conflicts": "",
                    "Review Required": False,
                    "Ranked Candidates": "ELECTRONIC FUND TRANSFER:0.82",
                },
            ),
            review_row(
                Narration="UPI/IRCTC/222/NA",
                **{
                    "Normalized Narration": "UPI/IRCTC/222/NA",
                    "Reference ID": "222",
                    "Category": "TRAVEL",
                    "Confidence": 0.78,
                    "Conflicts": "rail_entity_ambiguity",
                    "Review Required": True,
                    "Ranked Candidates": "TRAVEL:0.75 | ELECTRONIC FUND TRANSFER:0.72",
                },
            ),
            review_row(
                Narration="GST TAX PAYMENT",
                **{
                    "Normalized Narration": "GST TAX PAYMENT",
                    "Reference ID": "",
                    "Entity Name": "UNKNOWN",
                    "Merchant": "UNKNOWN",
                    "Entity Type": "UNKNOWN",
                    "Category": "TAX",
                    "Confidence": 0.9,
                    "Conflicts": "",
                    "Review Required": False,
                    "Ranked Candidates": "TAX:0.9",
                },
            ),
        ]
        df = pd.DataFrame(rows)

        available = available_review_categories(
            df,
            hide_generic_high_confidence=True,
        )
        conflicted = available_review_categories(
            df,
            hide_generic_high_confidence=True,
            conflict_only=True,
        )

        self.assertNotIn("ELECTRONIC FUND TRANSFER", available)
        self.assertIn("TRAVEL", available)
        self.assertIn("TAX", available)
        self.assertEqual(conflicted, ["TRAVEL"])


if __name__ == "__main__":
    unittest.main()
