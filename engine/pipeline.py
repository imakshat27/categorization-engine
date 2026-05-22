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
    detect_salary
)

from engine.parser import parse_upi_transaction


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
    # UPI PARSING
    # =========================

    upi_results = df[
        "Normalized Narration"
    ].apply(parse_upi_transaction)


    df["Entity Name"] = upi_results.apply(
        lambda x: x["entity_name"]
    )

    df["UPI ID"] = upi_results.apply(
        lambda x: x["upi_id"]
    )

    df["UPI Handle"] = upi_results.apply(
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