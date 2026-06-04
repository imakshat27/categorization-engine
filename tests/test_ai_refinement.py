import json
import os
import tempfile
import unittest

import pandas as pd

from engine.ai_refinement import (
    build_refinement_prompt,
    build_semantic_payload,
    refine_row,
    refine_transactions,
    route_row_for_refinement,
    select_rows_for_refinement,
    _normalize_ai_output_shape,
)
from engine.pipeline import process_transactions
from engine.refinement_contracts import SEMANTIC_PAYLOAD_VERSION
from engine.refinement_validator import validate_ai_output
from engine.taxonomy import CATEGORY_DEFINITIONS, TAXONOMY_VERSION


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
        self.assertLess(len(payload["category_definitions"]), len(CATEGORY_DEFINITIONS))
        self.assertNotIn("Old Category", json.dumps(payload))

        prompt = build_refinement_prompt(payload)
        self.assertLess(len(prompt), len(json.dumps({"category_definitions": CATEGORY_DEFINITIONS})))

    def test_balanced_routing_skips_zero_context_and_routes_entity_gap(self):
        generic_low = processed_row("UNRECOGNIZED LOCAL ENTRY", debits=123)
        generic_peer = processed_row("UPI/MOHD IRFAN/421649697130/NA", debits=100)
        entity_gap = processed_row("UPI/R K SONS/421910458283/NA", debits=100)
        df = pd.DataFrame([generic_low, generic_peer, entity_gap])

        selected = select_rows_for_refinement(df, threshold=0.65)

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected.iloc[0]["Narration"], "UPI/R K SONS/421910458283/NA")
        self.assertEqual(selected.iloc[0]["AI Routing Reason"], "ENTITY_RULE_GAP")
        self.assertEqual(
            route_row_for_refinement(generic_low)["skip_reason"],
            "GENERIC_TRANSFER_ONLY",
        )

    def test_known_entity_rail_background_does_not_route_to_ai(self):
        row = processed_row("UPI/SWIGGY/422893219208/NA", debits=500)
        routing = route_row_for_refinement(row)

        self.assertEqual(row["Category"], "E-COMMERCE")
        self.assertFalse(routing["eligible"])
        self.assertEqual(routing["skip_reason"], "KNOWN_ENTITY_RAIL_BACKGROUND")

    def test_payment_channel_only_skips_balanced_but_can_route_exploratory(self):
        row = processed_row(
            "UPI/FAROOQUI MOHDK/423417140851/Sent from Paytm",
            debits=500,
        )

        balanced = route_row_for_refinement(row, routing_policy="balanced")
        exploratory = route_row_for_refinement(row, routing_policy="exploratory")

        self.assertFalse(balanced["eligible"])
        self.assertEqual(balanced["skip_reason"], "PAYMENT_CHANNEL_ONLY")
        self.assertTrue(exploratory["eligible"])
        self.assertEqual(exploratory["routing_reason"], "PAYMENT_CHANNEL_AMBIGUITY")

    def test_strict_policy_suppresses_medium_confidence_entity_gap(self):
        row = processed_row("UPI/R K SONS/421910458283/NA", debits=100)

        strict = route_row_for_refinement(row, routing_policy="strict")
        balanced = route_row_for_refinement(row, routing_policy="balanced")

        self.assertFalse(strict["eligible"])
        self.assertTrue(balanced["eligible"])

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

            self.assertNotIn("semantic_payload", log)
            self.assertIn("prompt_chars", log)
            self.assertNotIn("prompt", log)
            self.assertIn("validation", log)
            self.assertIn("category_definition_count", log)

    def test_refine_row_audit_logging_keeps_replay_data(self):
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
            refine_row(
                row,
                row_index=3,
                generate_func=fake_generate,
                log_path=log_path,
                log_detail="audit",
            )

            with open(log_path, "r", encoding="utf-8") as file:
                log = json.loads(file.readline())

            self.assertIn("semantic_payload", log)
            self.assertIn("prompt", log)
            self.assertIn("raw_ai_response", log)
            self.assertEqual(
                log["semantic_payload"]["semantic_payload_version"],
                SEMANTIC_PAYLOAD_VERSION,
            )

    def test_legacy_same_category_suggest_change_becomes_engine_fix(self):
        row = processed_row("N/0811OP4131082484/DBSS0IN0811/PVA TRADERS", credits=1000)

        def fake_generate(_prompt):
            return json.dumps(
                {
                    "decision": "SUGGEST_CHANGE",
                    "suggested_category": row["Category"],
                    "refinement_type": "WEAK_DETERMINISTIC_EVIDENCE",
                    "semantic_reason": "Weak evidence for deterministic category",
                    "missing_or_misread_signal": "entity registry gap",
                    "recommended_deterministic_improvement": "Add PVA TRADERS entity mapping",
                    "ai_confidence_advisory": "LOW",
                }
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            result = refine_row(
                row,
                row_index=15,
                generate_func=fake_generate,
                log_path=os.path.join(tmpdir, "ai_refinement.jsonl"),
            )

        self.assertEqual(result["Validation Status"], "ACCEPTED")
        self.assertEqual(result["AI Decision"], "NEEDS_DETERMINISTIC_FIX")
        self.assertEqual(result["AI Outcome"], "ENGINE_FIX_NEEDED")
        self.assertIn("PVA TRADERS", result["AI Proposed Action"])

    def test_incompatible_category_suggestion_is_preserved_as_advisory_fix(self):
        row = pd.Series(
            {
                "Narration": "ACHDEBIT:PY3001UV0000485FEB24,TVS CREDIT SERVICES",
                "Normalized Narration": "ACHDEBIT:PY3001UV0000485FEB24,TVS CREDIT SERVICES",
                "Category": "TRANSFER OUT",
                "Confidence": 0.0,
                "Review Required": True,
                "Mode": "UNKNOWN",
                "Protocol Family": "UNKNOWN",
                "Direction": "OUT",
                "Entity Name": "ACHDEBIT:PY3001UV0000485FEB24,TVS CREDIT SERVICES",
                "Entity Type": "UNKNOWN",
                "Entity Role": "UNKNOWN",
                "Entity Confidence": 0.0,
                "Intent Tags": "",
                "Movement Tags": "",
                "Bank Family": "UNKNOWN",
                "Parse Quality": "LOW",
                "Parser Rule": "NO_PARSER_MATCH",
                "Conflicts": "parser_low_quality | weak_fallback",
                "Ranked Candidates": "TRANSFER OUT:0.129",
                "Evidence Summary": "TRANSFER OUT <= fallback:weak_directional_fallback (0.34)",
                "AI Refinement Eligible": True,
                "AI Routing Policy": "balanced",
                "AI Routing Reason": "ENTITY_RULE_GAP",
                "AI Skip Reason": "",
            }
        )

        def fake_generate(_prompt):
            return json.dumps(
                {
                    "decision": "SUGGEST_CHANGE",
                    "suggested_category": "ACH BOUNCED CHARGES",
                    "refinement_type": "WEAK_DETERMINISTIC_EVIDENCE",
                    "semantic_reason": "ACH debit family was not parsed",
                    "missing_or_misread_signal": "ACH rail",
                    "recommended_deterministic_improvement": "",
                    "ai_confidence_advisory": "LOW",
                }
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            result = refine_row(
                row,
                row_index=8,
                generate_func=fake_generate,
                log_path=os.path.join(tmpdir, "ai_refinement.jsonl"),
            )

        self.assertEqual(result["Validation Status"], "ACCEPTED")
        self.assertEqual(result["AI Decision"], "NEEDS_DETERMINISTIC_FIX")
        self.assertEqual(result["AI Outcome"], "ENGINE_FIX_NEEDED")
        self.assertEqual(result["AI Suggested Category"], "ACH BOUNCED CHARGES")
        self.assertIn("requires rail", result["Validation Warnings"])

    def test_refine_transactions_logs_skipped_rows_without_model_call(self):
        generic_low = processed_row("UNRECOGNIZED LOCAL ENTRY", debits=123)
        entity_gap = processed_row("UPI/R K SONS/421910458283/NA", debits=100)
        df = pd.DataFrame([generic_low, entity_gap])
        calls = []

        def fake_generate(prompt):
            calls.append(prompt)
            payload = json.loads(prompt)["semantic_payload"]
            return json.dumps(
                {
                    "decision": "NO_CHANGE",
                    "suggested_category": payload["deterministic"]["category"],
                    "refinement_type": "NO_ISSUE_DETECTED",
                    "semantic_reason": "deterministic category retained",
                    "missing_or_misread_signal": "",
                    "recommended_deterministic_improvement": "",
                    "ai_confidence_advisory": "MEDIUM",
                }
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "ai_refinement.jsonl")
            results = refine_transactions(
                df,
                threshold=0.65,
                generate_func=fake_generate,
                log_path=log_path,
            )

            self.assertEqual(len(calls), 1)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["AI Routing Reason"], "ENTITY_RULE_GAP")

            with open(log_path, "r", encoding="utf-8") as file:
                logs = [json.loads(line) for line in file]

            self.assertEqual(len(logs), 2)
            self.assertEqual(logs[0]["event_type"], "AI_REFINEMENT_SKIPPED_SUMMARY")
            self.assertEqual(
                logs[0]["refinement_result"]["skip_counts"]["GENERIC_TRANSFER_ONLY"],
                1,
            )
            self.assertEqual(logs[1]["event_type"], "AI_REFINEMENT_ATTEMPTED")

    def test_normalizes_provider_wrapped_schema_response(self):
        wrapped = {
            "instruction": {
                "output_schema": {
                    "decision": "NO_CHANGE",
                    "suggested_category": "TRANSFER OUT",
                    "refinement_type": "NO_ISSUE_DETECTED",
                    "semantic_reason": "generic transfer",
                    "missing_or_misread_signal": "",
                    "recommended_deterministic_improvement": "",
                    "ai_confidence_advisory": "LOW",
                }
            }
        }

        normalized = _normalize_ai_output_shape(wrapped)

        self.assertEqual(normalized["decision"], "NO_CHANGE")
        self.assertEqual(normalized["suggested_category"], "TRANSFER OUT")

    def test_refine_row_accepts_provider_wrapped_response(self):
        row = processed_row("FRIEND OR FAMILY", debits=5000)

        def fake_generate(_prompt):
            return """
```json
{
  "instruction": {
    "output_schema": {
      "decision": "NO_CHANGE",
      "suggested_category": "TRANSFER OUT",
      "refinement_type": "NO_ISSUE_DETECTED",
      "semantic_reason": "generic outgoing transfer",
      "missing_or_misread_signal": "",
      "recommended_deterministic_improvement": "",
      "ai_confidence_advisory": "LOW"
    }
  }
}
```

Explanation: ignored.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "ai_refinement.jsonl")
            result = refine_row(
                row,
                row_index=4,
                generate_func=fake_generate,
                log_path=log_path,
                provider="huggingface",
                log_detail="audit",
            )

            self.assertEqual(result["Validation Status"], "ACCEPTED")
            self.assertEqual(result["AI Decision"], "NO_CHANGE")

            with open(log_path, "r", encoding="utf-8") as file:
                log = json.loads(file.readline())

            self.assertIn("extracted_ai_response", log)
            self.assertIn("parsed_ai_response", log)
            self.assertEqual(log["model_metadata"]["provider"], "huggingface")


if __name__ == "__main__":
    unittest.main()
