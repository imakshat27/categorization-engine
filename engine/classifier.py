from engine.rules import (
    load_category_rules,
    load_mode_rules,
    load_merchant_rules
)
import pandas as pd


def detect_direction(row):

    debit = row.get("Debits")
    credit = row.get("Credits")

    if pd.notna(debit) and debit > 0:
        return "OUT"

    if pd.notna(credit) and credit > 0:
        return "IN"

    return "UNKNOWN"

def detect_mode(narration):

    rules = load_mode_rules()

    # check all rules
    for rule in rules:

        # check all patterns
        for pattern in rule["patterns"]:

            if pattern in narration:

                return {
                    "mode": rule["mode"],
                    "matched_mode_rule": rule["rule_name"]
                }

    return {
        "mode": "UNKNOWN",
        "matched_mode_rule": "NO_MODE_RULE_MATCHED"
    }

def detect_merchant(narration):

    rules = load_merchant_rules()

    # check all merchant rules
    for rule in rules:

        # check all patterns
        for pattern in rule["patterns"]:

            if pattern in narration:

                return {
                    "merchant": rule["merchant"],
                    "matched_merchant_rule": rule["rule_name"]
                }

    return {
        "merchant": "UNKNOWN",
        "matched_merchant_rule": "NO_MERCHANT_RULE_MATCHED"
    }

def resolve_category(base_category, direction):

    # dynamic transfer classification
    if base_category == "TRANSFER":

        if direction == "IN":
            return "TRANSFER IN"

        if direction == "OUT":
            return "TRANSFER OUT"

    return base_category


def classify_transaction(row):

    narration = row["Normalized Narration"]
    direction = row["Direction"]

    rules = load_category_rules()

    # check all rules
    for rule in rules:

        # check all patterns
        for pattern in rule["patterns"]:

            if pattern in narration:

                return {
                    "category": resolve_category(
                        rule["category"],
                        direction
                    ),

                    "matched_rule": rule["rule_name"]
                }

    return {
        "category": "UNCLASSIFIED",
        "matched_rule": "NO_RULE_MATCHED"
    }