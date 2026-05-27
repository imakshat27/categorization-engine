from engine.evidence_engine import classify_facts
from engine.matcher import regex_match, token_match
from engine.rules import load_merchant_rules, load_mode_rules
from engine.semantic import build_semantic_facts, detect_direction


def detect_mode(narration):
    rules = load_mode_rules()

    for rule in rules:
        for pattern in rule["patterns"]:
            if token_match(
                pattern,
                narration,
                rule_name=rule["rule_name"],
                source="mode",
            ):
                return {
                    "mode": rule["mode"],
                    "matched_mode_rule": rule["rule_name"],
                }

    inferred_modes = [
        ("ACH", ["ACH"]),
        ("NACH", ["NACH"]),
        ("ECS", ["ECS"]),
        ("UPI", ["UPI", "UPIAR", "REV-UPI"]),
        ("IMPS", ["IMPS"]),
        ("NEFT", ["NEFT"]),
        ("RTGS", ["RTGS"]),
        ("ATM", ["ATM", "NWD", "ATW"]),
        ("CHEQUE", ["CHQ", "CHEQUE", "CLG", "MICR"]),
    ]

    for mode, patterns in inferred_modes:
        for pattern in patterns:
            if token_match(pattern, narration, rule_name=f"{mode}_INFERRED", source="mode"):
                return {
                    "mode": mode,
                    "matched_mode_rule": f"{mode}_INFERRED",
                }

    if regex_match(r"\bSENTIMPS|\bIMPSP2A", narration, rule_name="IMPS_COMPACT_INFERRED", source="mode"):
        return {
            "mode": "IMPS",
            "matched_mode_rule": "IMPS_COMPACT_INFERRED",
        }

    return {
        "mode": "UNKNOWN",
        "matched_mode_rule": "NO_MODE_RULE_MATCHED",
    }


def detect_merchant(narration):
    rules = load_merchant_rules()

    for rule in rules:
        for pattern in rule["patterns"]:
            if token_match(
                pattern,
                narration,
                rule_name=rule["rule_name"],
                source="merchant",
            ):
                return {
                    "merchant": rule["merchant"],
                    "matched_merchant_rule": rule["rule_name"],
                }

    return {
        "merchant": "UNKNOWN",
        "matched_merchant_rule": "NO_MERCHANT_RULE_MATCHED",
    }


def resolve_category(base_category, direction):
    if base_category == "TRANSFER":
        if direction == "IN":
            return "TRANSFER IN"

        if direction == "OUT":
            return "TRANSFER OUT"

    return base_category


def classify_transaction(row):
    facts = row.get("Semantic Facts")

    if not isinstance(facts, dict):
        facts = build_semantic_facts(row)

    return classify_facts(facts)
