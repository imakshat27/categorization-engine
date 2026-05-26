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

    # =====================================
    # EXTRACT METADATA
    # =====================================

    direction = row["Direction"]

    mode = row["Mode"]

    merchant = row["Merchant"]

    subtype = row["Transaction Subtype"]


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
    # REVERSAL / REFUND
    # =====================================

    if reversal_flag:

        return {
            "category": "REFUND OR REVERSAL",
            "matched_rule": "REVERSAL_SIGNAL_RULE"
        }


    # =====================================
    # BOUNCE CHARGES
    # =====================================

    if bounce_flag and charge_flag:

        if mode == "IMPS":

            return {
                "category": "IMPS BOUNCE CHARGES",
                "matched_rule": "IMPS_BOUNCE_SIGNAL_RULE"
            }

        if mode == "ECS":

            return {
                "category": "ECS BOUNCED CHARGES",
                "matched_rule": "ECS_BOUNCE_SIGNAL_RULE"
            }

        if mode == "ACH":

            return {
                "category": "ACH BOUNCED CHARGES",
                "matched_rule": "ACH_BOUNCE_SIGNAL_RULE"
            }


    # =====================================
    # SALARY
    # =====================================

    if salary_flag:

        if direction == "IN":

            return {
                "category": "SALARY RECEIVED",
                "matched_rule": "SALARY_IN_SIGNAL_RULE"
            }

        if direction == "OUT":

            return {
                "category": "SALARY PAID",
                "matched_rule": "SALARY_OUT_SIGNAL_RULE"
            }


    # =====================================
    # ATM
    # =====================================

    if atm_flag:

        if withdrawal_flag:

            return {
                "category": "ATM WITHDRAWAL",
                "matched_rule": "ATM_WITHDRAWAL_SIGNAL_RULE"
            }

        if deposit_flag:

            return {
                "category": "ATM DEPOSIT",
                "matched_rule": "ATM_DEPOSIT_SIGNAL_RULE"
            }


    # =====================================
    # CASH
    # =====================================

    if cash_flag:

        if withdrawal_flag:

            return {
                "category": "CASH WITHDRAWAL",
                "matched_rule": "CASH_WITHDRAWAL_SIGNAL_RULE"
            }

        if deposit_flag:

            return {
                "category": "CASH DEPOSIT",
                "matched_rule": "CASH_DEPOSIT_SIGNAL_RULE"
            }


    # =====================================
    # TAX
    # =====================================

    if tax_flag:

        return {
            "category": "TAX",
            "matched_rule": "TAX_SIGNAL_RULE"
        }


    # =====================================
    # INVESTMENTS
    # =====================================

    if investment_flag:

        return {
            "category": "INVESTMENTS",
            "matched_rule": "INVESTMENT_SIGNAL_RULE"
        }


    # =====================================
    # INSURANCE
    # =====================================

    if insurance_flag:

        return {
            "category": "INSURANCE",
            "matched_rule": "INSURANCE_SIGNAL_RULE"
        }


    # =====================================
    # RECHARGE
    # =====================================

    if recharge_flag:

        return {
            "category": "RECHARGE",
            "matched_rule": "RECHARGE_SIGNAL_RULE"
        }


    # =====================================
    # TRAVEL
    # =====================================

    if travel_flag:

        return {
            "category": "TRAVEL",
            "matched_rule": "TRAVEL_SIGNAL_RULE"
        }


    # =====================================
    # UTILITY
    # =====================================

    if utility_flag:

        return {
            "category": "UTILITY",
            "matched_rule": "UTILITY_SIGNAL_RULE"
        }


    # =====================================
    # LOAN
    # =====================================

    if loan_flag:

        return {
            "category": "LOAN",
            "matched_rule": "LOAN_SIGNAL_RULE"
        }


    # =====================================
    # CHEQUE
    # =====================================

    if cheque_flag:

        if withdrawal_flag:

            return {
                "category": "CHEQUE WITHDRAWAL",
                "matched_rule": "CHEQUE_WITHDRAWAL_SIGNAL_RULE"
            }

        if deposit_flag:

            return {
                "category": "CHEQUE DEPOSIT",
                "matched_rule": "CHEQUE_DEPOSIT_SIGNAL_RULE"
            }


    # =====================================
    # TRANSFER LOGIC
    # =====================================

    if mode in ["UPI", "IMPS", "NEFT", "RTGS"]:

        if direction == "IN":

            return {
                "category": "TRANSFER IN",
                "matched_rule": "TRANSFER_IN_SIGNAL_RULE"
            }

        if direction == "OUT":

            return {
                "category": "TRANSFER OUT",
                "matched_rule": "TRANSFER_OUT_SIGNAL_RULE"
            }


    # =====================================
    # FALLBACK
    # =====================================

    return {
        "category": "UNCLASSIFIED",
        "matched_rule": "NO_SIGNAL_MATCH"
    }