import json
import os
import tempfile
import unittest

import pandas as pd

from engine.ai_refinement import (
    build_semantic_payload,
    refine_row,
    select_rows_for_refinement,
)
from engine.pipeline import process_transactions
from engine.refinement_contracts import SEMANTIC_PAYLOAD_VERSION
from engine.refinement_validator import validate_ai_output
from engine.taxonomy import TAXONOMY_VERSION


def processed_row(narration, debits=None, credits=None, **extra):
    row = {
        "Bank": "Test Bank",
        "Cheque No": "",
        "Narration": narration,
        "Remarks": "",
        "Debits": debits,
        "Credits": credits,
    }
    row.update(extra)
    return process_transactions(pd.DataFrame([row])).iloc[0]


class AIRefinementTests(unittest.TestCase):
    def test_payload_is_versioned_and_compact(self):
        row = processed_row(
            "UPI/SUPER FILLINGS/425547609685/NA",
            debits=2000,
            Remarks="SUPER FILLINGS",
            Category="OLD VALUE",
        )
        payload = build_semantic_payload(row, row_index=7)

        self.assertEqual(payload["semantic_payload_version"], SEMANTIC_PAYLOAD_VERSION)
        self.assertEqual(payload["taxonomy_version"], TAXONOMY_VERSION)
        self.assertEqual(payload["row_index"], 7)
        self.assertIn("semantic_summary", payload)
        self.assertIn("category_definitions", payload)
        self.assertNotIn("Old Category", json.dumps(payload))

    def test_route_low_confidence_and_review_rows(self):
        high = processed_row("UPI/RRN 412288007493/UPI", debits=100)
        low = processed_row("UNRECOGNIZED LOCAL ENTRY", debits=123)
        df = pd.DataFrame([high, low])

        selected = select_rows_for_refinement(df, threshold=0.65)

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected.iloc[0]["Narration"], "UNRECOGNIZED LOCAL ENTRY")

    def test_validator_rejects_invalid_category(self):
        row = processed_row("UPI/RRN 412288007493/UPI", debits=100)
        payload = build_semantic_payload(row)
        validation = validate_ai_output(
            {
                "decision": "SUGGEST_CHANGE",
                "suggested_category": "MADE UP CATEGORY",
                "refinement_type": "AMBIGUITY_RESOLUTION",
                "semantic_reason": "invalid taxonomy",
                "missing_or_misread_signal": "",
                "recommended_deterministic_improvement": "",
                "ai_confidence_advisory": "LOW",
            },
            payload,
        )

        self.assertEqual(validation["validation_status"], "REJECTED")

    def test_validator_rejects_direction_incompatible_category(self):
        row = processed_row("FRIEND OR FAMILY", debits=5000)
        payload = build_semantic_payload(row)
        validation = validate_ai_output(
            {
                "decision": "SUGGEST_CHANGE",
                "suggested_category": "TRANSFER IN",
                "refinement_type": "AMBIGUITY_RESOLUTION",
                "semantic_reason": "manual transfer in",
                "missing_or_misread_signal": "",
                "recommended_deterministic_improvement": "",
                "ai_confidence_advisory": "MEDIUM",
            },
            payload,
        )

        self.assertEqual(validation["validation_status"], "REJECTED")
        self.assertIn("requires direction", validation["validation_errors"][0])

    def test_refine_row_accepts_no_change_and_logs_replay_data(self):
        row = processed_row("UPI/RRN 412288007493/UPI", debits=100)

        def fake_generate(_prompt):
            return json.dumps(
                {
                    "decision": "NO_CHANGE",
                    "suggested_category": row["Category"],
                    "refinement_type": "NO_ISSUE_DETECTED",
                    "semantic_reason": "generic rail transfer",
                    "missing_or_misread_signal": "",
                    "recommended_deterministic_improvement": "",
                    "ai_confidence_advisory": "HIGH",
                }
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "ai_refinement.jsonl")
            result = refine_row(
                row,
                row_index=3,
                generate_func=fake_generate,
                log_path=log_path,
            )

            self.assertEqual(result["Validation Status"], "ACCEPTED")
            self.assertEqual(result["AI Decision"], "NO_CHANGE")
            self.assertEqual(result["AI Suggested Category"], row["Category"])

            with open(log_path, "r", encoding="utf-8") as file:
                log = json.loads(file.readline())

            self.assertIn("semantic_payload", log)
            self.assertIn("prompt", log)
            self.assertIn("validation", log)
            self.assertEqual(
                log["semantic_payload"]["semantic_payload_version"],
                SEMANTIC_PAYLOAD_VERSION,
            )


if __name__ == "__main__":
    unittest.main()

