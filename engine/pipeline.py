from engine.normalizer import normalize_text

from engine.classifier import (
    detect_direction,
    detect_mode,
    detect_merchant,
    classify_transaction
)

from engine.signals import (
    detect_bounce,
    detect_charge,
    detect_reversal,
    detect_salary,
    detect_tax,
    detect_cash,
    detect_deposit,
    detect_withdrawal,
    detect_atm,
    detect_cheque,
    detect_investment,
    detect_insurance,
    detect_recharge,
    detect_travel,
    detect_utility,
    detect_loan
)

from engine.parser import parse_transaction


def process_transactions(df):

    # =========================
    # NORMALIZATION
    # =========================

    df["Normalized Narration"] = df[
        "Narration"
    ].apply(normalize_text)


    # =========================
    # DIRECTION DETECTION
    # =========================

    df["Direction"] = df.apply(
        detect_direction,
        axis=1
    )


    # =========================
    # MODE DETECTION
    # =========================

    mode_results = df[
        "Normalized Narration"
    ].apply(detect_mode)


    df["Mode"] = mode_results.apply(
        lambda x: x["mode"]
    )


    # =========================
    # MERCHANT DETECTION
    # =========================

    merchant_results = df[
        "Normalized Narration"
    ].apply(detect_merchant)


    df["Merchant"] = merchant_results.apply(
        lambda x: x["merchant"]
    )


    # =========================
    # TRANSACTION PARSING
    # =========================

    parse_results = df.apply(
        parse_transaction,
        axis=1
    )


    df["Transaction Prefix"] = parse_results.apply(
        lambda x: x["transaction_prefix"]
    )


    df["Transaction Subtype"] = parse_results.apply(
        lambda x: x["transaction_subtype"]
    )


    df["Reference ID"] = parse_results.apply(
        lambda x: x["reference_id"]
    )


    df["Entity Name"] = parse_results.apply(
        lambda x: x["entity_name"]
    )


    df["Bank Name"] = parse_results.apply(
        lambda x: x["bank_name"]
    )


    df["UPI ID"] = parse_results.apply(
        lambda x: x["upi_id"]
    )


    df["UPI Handle"] = parse_results.apply(
        lambda x: x["upi_handle"]
    )


    # =========================
    # SIGNAL EXTRACTION
    # =========================

    df["Bounce Flag"] = df[
        "Normalized Narration"
    ].apply(detect_bounce)


    df["Charge Flag"] = df[
        "Normalized Narration"
    ].apply(detect_charge)


    df["Reversal Flag"] = df[
        "Normalized Narration"
    ].apply(detect_reversal)


    df["Salary Flag"] = df[
        "Normalized Narration"
    ].apply(detect_salary)


    df["Tax Flag"] = df[
        "Normalized Narration"
    ].apply(detect_tax)


    df["Cash Flag"] = df[
        "Normalized Narration"
    ].apply(detect_cash)


    df["Deposit Flag"] = df[
        "Normalized Narration"
    ].apply(detect_deposit)


    df["Withdrawal Flag"] = df[
        "Normalized Narration"
    ].apply(detect_withdrawal)


    df["ATM Flag"] = df[
        "Normalized Narration"
    ].apply(detect_atm)


    df["Cheque Flag"] = df[
        "Normalized Narration"
    ].apply(detect_cheque)


    df["Investment Flag"] = df[
        "Normalized Narration"
    ].apply(detect_investment)


    df["Insurance Flag"] = df[
        "Normalized Narration"
    ].apply(detect_insurance)


    df["Recharge Flag"] = df[
        "Normalized Narration"
    ].apply(detect_recharge)


    df["Travel Flag"] = df[
        "Normalized Narration"
    ].apply(detect_travel)


    df["Utility Flag"] = df[
        "Normalized Narration"
    ].apply(detect_utility)


    df["Loan Flag"] = df[
        "Normalized Narration"
    ].apply(detect_loan)


    # =========================
    # CATEGORY CLASSIFICATION
    # =========================

    classification_results = df.apply(
        classify_transaction,
        axis=1
    )


    df["Category"] = classification_results.apply(
        lambda x: x["category"]
    )


    df["Matched Rule"] = classification_results.apply(
        lambda x: x["matched_rule"]
    )


    return df