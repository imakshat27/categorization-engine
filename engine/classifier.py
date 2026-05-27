from engine.rules import (
    load_category_rules,
    load_mode_rules,
    load_merchant_rules
)

from engine.confidence import build_classification

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

    for rule in rules:

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

    for rule in rules:

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

    if base_category == "TRANSFER":

        if direction == "IN":
            return "TRANSFER IN"

        if direction == "OUT":
            return "TRANSFER OUT"

    return base_category


def classify_transaction(row):

    # =====================================
    # EXTRACT METADATA
    # =====================================

    direction = row["Direction"]

    mode = row["Mode"]

    merchant = row["Merchant"]

    subtype = row["Transaction Subtype"]

    parse_quality = row["Parse Quality"]

    entity_type = row["Entity Type"]


    # =====================================
    # EXTRACT SIGNALS
    # =====================================

    bounce_flag = row["Bounce Flag"]

    charge_flag = row["Charge Flag"]

    reversal_flag = row["Reversal Flag"]

    salary_flag = row["Salary Flag"]

    tax_flag = row["Tax Flag"]

    cash_flag = row["Cash Flag"]

    deposit_flag = row["Deposit Flag"]

    withdrawal_flag = row["Withdrawal Flag"]

    atm_flag = row["ATM Flag"]

    cheque_flag = row["Cheque Flag"]

    investment_flag = row["Investment Flag"]

    insurance_flag = row["Insurance Flag"]

    recharge_flag = row["Recharge Flag"]

    travel_flag = row["Travel Flag"]

    utility_flag = row["Utility Flag"]

    loan_flag = row["Loan Flag"]


    # =====================================
    # CONFLICT DETECTION
    # =====================================

    conflicts = []


    if deposit_flag and withdrawal_flag:

        conflicts.append(
            "deposit_withdrawal_conflict"
        )


    if cash_flag and cheque_flag:

        conflicts.append(
            "cash_cheque_conflict"
        )


    # =====================================
    # REVERSAL / REFUND
    # =====================================

    if reversal_flag:

        return build_classification(

            category="REFUND OR REVERSAL",

            matched_rule="REVERSAL_SIGNAL_RULE",

            base_confidence=0.98,

            decision_path=[
                "reversal_flag"
            ],

            conflicts=conflicts
        )


    # =====================================
    # BOUNCE CHARGES
    # =====================================

    if bounce_flag and charge_flag:

        if mode == "IMPS":

            return build_classification(

                category="IMPS BOUNCE CHARGES",

                matched_rule="IMPS_BOUNCE_SIGNAL_RULE",

                base_confidence=0.95,

                decision_path=[
                    "bounce_flag",
                    "charge_flag",
                    "mode_imps"
                ],

                conflicts=conflicts
            )

        if mode == "ECS":

            return build_classification(

                category="ECS BOUNCED CHARGES",

                matched_rule="ECS_BOUNCE_SIGNAL_RULE",

                base_confidence=0.95,

                decision_path=[
                    "bounce_flag",
                    "charge_flag",
                    "mode_ecs"
                ],

                conflicts=conflicts
            )

        if mode == "ACH":

            return build_classification(

                category="ACH BOUNCED CHARGES",

                matched_rule="ACH_BOUNCE_SIGNAL_RULE",

                base_confidence=0.95,

                decision_path=[
                    "bounce_flag",
                    "charge_flag",
                    "mode_ach"
                ],

                conflicts=conflicts
            )


    # =====================================
    # SALARY
    # =====================================

    if salary_flag:

        if direction == "IN":

            return build_classification(

                category="SALARY RECEIVED",

                matched_rule="SALARY_IN_SIGNAL_RULE",

                base_confidence=0.93,

                decision_path=[
                    "salary_flag",
                    "direction_in"
                ],

                conflicts=conflicts
            )

        if direction == "OUT":

            return build_classification(

                category="SALARY PAID",

                matched_rule="SALARY_OUT_SIGNAL_RULE",

                base_confidence=0.90,

                decision_path=[
                    "salary_flag",
                    "direction_out"
                ],

                conflicts=conflicts
            )


    # =====================================
    # ATM
    # =====================================

    if atm_flag:

        if withdrawal_flag:

            return build_classification(

                category="ATM WITHDRAWAL",

                matched_rule="ATM_WITHDRAWAL_SIGNAL_RULE",

                base_confidence=0.94,

                decision_path=[
                    "atm_flag",
                    "withdrawal_flag"
                ],

                conflicts=conflicts
            )

        if deposit_flag:

            return build_classification(

                category="ATM DEPOSIT",

                matched_rule="ATM_DEPOSIT_SIGNAL_RULE",

                base_confidence=0.90,

                decision_path=[
                    "atm_flag",
                    "deposit_flag"
                ],

                conflicts=conflicts
            )


    # =====================================
    # CASH
    # =====================================

    if cash_flag:

        if withdrawal_flag:

            return build_classification(

                category="CASH WITHDRAWAL",

                matched_rule="CASH_WITHDRAWAL_SIGNAL_RULE",

                base_confidence=0.88,

                decision_path=[
                    "cash_flag",
                    "withdrawal_flag"
                ],

                conflicts=conflicts
            )

        if deposit_flag:

            return build_classification(

                category="CASH DEPOSIT",

                matched_rule="CASH_DEPOSIT_SIGNAL_RULE",

                base_confidence=0.88,

                decision_path=[
                    "cash_flag",
                    "deposit_flag"
                ],

                conflicts=conflicts
            )


    # =====================================
    # TAX
    # =====================================

    if tax_flag:

        return build_classification(

            category="TAX",

            matched_rule="TAX_SIGNAL_RULE",

            base_confidence=0.90,

            decision_path=[
                "tax_flag"
            ],

            conflicts=conflicts
        )


    # =====================================
    # INVESTMENTS
    # =====================================

    if investment_flag:

        return build_classification(

            category="INVESTMENTS",

            matched_rule="INVESTMENT_SIGNAL_RULE",

            base_confidence=0.92,

            decision_path=[
                "investment_flag"
            ],

            conflicts=conflicts
        )


    # =====================================
    # INSURANCE
    # =====================================

    if insurance_flag:

        return build_classification(

            category="INSURANCE",

            matched_rule="INSURANCE_SIGNAL_RULE",

            base_confidence=0.88,

            decision_path=[
                "insurance_flag"
            ],

            conflicts=conflicts
        )


    # =====================================
    # RECHARGE
    # =====================================

    if recharge_flag:

        return build_classification(

            category="RECHARGE",

            matched_rule="RECHARGE_SIGNAL_RULE",

            base_confidence=0.90,

            decision_path=[
                "recharge_flag"
            ],

            conflicts=conflicts
        )


    # =====================================
    # TRAVEL
    # =====================================

    if travel_flag:

        return build_classification(

            category="TRAVEL",

            matched_rule="TRAVEL_SIGNAL_RULE",

            base_confidence=0.88,

            decision_path=[
                "travel_flag"
            ],

            conflicts=conflicts
        )


    # =====================================
    # UTILITY
    # =====================================

    if utility_flag:

        utility_conflicts = conflicts.copy()

        utility_conflicts.append(
            "weak_signal_match"
        )

        return build_classification(

            category="UTILITY",

            matched_rule="UTILITY_SIGNAL_RULE",

            base_confidence=0.70,

            decision_path=[
                "utility_flag"
            ],

            conflicts=utility_conflicts
        )


    # =====================================
    # LOAN
    # =====================================

    if loan_flag:

        return build_classification(

            category="LOAN",

            matched_rule="LOAN_SIGNAL_RULE",

            base_confidence=0.94,

            decision_path=[
                "loan_flag"
            ],

            conflicts=conflicts
        )


    # =====================================
    # CHEQUE
    # =====================================

    if cheque_flag:

        if withdrawal_flag:

            return build_classification(

                category="CHEQUE WITHDRAWAL",

                matched_rule="CHEQUE_WITHDRAWAL_SIGNAL_RULE",

                base_confidence=0.90,

                decision_path=[
                    "cheque_flag",
                    "withdrawal_flag"
                ],

                conflicts=conflicts
            )

        if deposit_flag:

            return build_classification(

                category="CHEQUE DEPOSIT",

                matched_rule="CHEQUE_DEPOSIT_SIGNAL_RULE",

                base_confidence=0.90,

                decision_path=[
                    "cheque_flag",
                    "deposit_flag"
                ],

                conflicts=conflicts
            )

    # =====================================
    # ENTITY SEMANTIC CLASSIFICATION
    # =====================================

    if entity_type != "UNKNOWN":

        return build_classification(

            category=entity_type,

            matched_rule="ENTITY_INTELLIGENCE_RULE",

            base_confidence=0.92,

            decision_path=[
                "entity_semantic_match"
            ],

            conflicts=conflicts
        )
    
    # =====================================
    # P2M MERCHANT PAYMENT
    # =====================================

    if subtype == "P2M":

        return build_classification(

            category="PAYMENT GATEWAY",

            matched_rule="P2M_PROTOCOL_RULE",

            base_confidence=0.85,

            decision_path=[
                "protocol_subtype_p2m"
            ],

            conflicts=conflicts
        )


    # =====================================
    # P2V PEER TRANSFER
    # =====================================

    if subtype == "P2V":

        if direction == "IN":

            return build_classification(

                category="TRANSFER IN",

                matched_rule="P2V_TRANSFER_IN_RULE",

                base_confidence=0.80,

                decision_path=[
                    "protocol_subtype_p2v",
                    "direction_in"
                ],

                conflicts=conflicts
            )

        if direction == "OUT":

            return build_classification(

                category="TRANSFER OUT",

                matched_rule="P2V_TRANSFER_OUT_RULE",

                base_confidence=0.80,

                decision_path=[
                    "protocol_subtype_p2v",
                    "direction_out"
                ],

                conflicts=conflicts
            )


    # =====================================
    # TRANSFER LOGIC
    # =====================================

    if mode in ["UPI", "IMPS", "NEFT", "RTGS"]:

        if direction == "IN":

            return build_classification(

                category="TRANSFER IN",

                matched_rule="TRANSFER_IN_SIGNAL_RULE",

                base_confidence=0.65,

                decision_path=[
                    "transfer_rail",
                    "direction_in"
                ],

                conflicts=conflicts
            )

        if direction == "OUT":

            return build_classification(

                category="TRANSFER OUT",

                matched_rule="TRANSFER_OUT_SIGNAL_RULE",

                base_confidence=0.65,

                decision_path=[
                    "transfer_rail",
                    "direction_out"
                ],

                conflicts=conflicts
            )


    # =====================================
    # FALLBACK
    # =====================================

    return build_classification(

        category="UNCLASSIFIED",

        matched_rule="NO_SIGNAL_MATCH",

        base_confidence=0.20,

        decision_path=[
            "no_signal_match"
        ],

        conflicts=conflicts
    )