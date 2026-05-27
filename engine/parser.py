import re


# ======================================
# DEFAULT PARSER OUTPUT
# ======================================

def empty_parser_result():

    return {

        "transaction_prefix": "UNKNOWN",

        "transaction_subtype": "UNKNOWN",

        "reference_id": "UNKNOWN",

        "entity_name": "UNKNOWN",

        "bank_name": "UNKNOWN",

        "upi_id": "UNKNOWN",

        "upi_handle": "UNKNOWN",

        "parse_quality": "LOW"
    }


# ======================================
# UPI PARSER
# ======================================

def parse_upi_transaction(narration):

    result = empty_parser_result()

    parts = narration.split("/")


    # ======================================
    # EMPTY SAFETY
    # ======================================

    if len(parts) == 0:
        return result


    # ======================================
    # DETECT UPI FAMILY
    # ======================================

    upi_family = parts[0]

    result["transaction_prefix"] = upi_family


    # ======================================
    # UPIAR FORMAT
    # ======================================

    if upi_family == "UPIAR":

        if len(parts) >= 2:
            result["reference_id"] = parts[1]

        if len(parts) >= 3:
            result["transaction_subtype"] = parts[2]

        if len(parts) >= 4:
            result["entity_name"] = parts[3]

        if len(parts) >= 5:

            result["bank_name"] = parts[4]

            result["parse_quality"] = "HIGH"


    # ======================================
    # STANDARD UPI FORMAT
    # ======================================

    else:

        if len(parts) >= 2:
            result["reference_id"] = parts[1]

        if len(parts) >= 3:
            result["transaction_subtype"] = parts[2]

        if len(parts) >= 4:
            result["entity_name"] = parts[3]

        if len(parts) >= 5:

            result["bank_name"] = parts[4]

            result["parse_quality"] = "HIGH"


    # ======================================
    # UPI ID EXTRACTION
    # ======================================

    upi_pattern = r'[\w\.-]+@[\w]+'

    match = re.search(
        upi_pattern,
        narration
    )

    if match:

        upi_id = match.group()

        result["upi_id"] = upi_id

        result["upi_handle"] = (
            upi_id.split("@")[1]
            .upper()
        )

    return result


# ======================================
# NEFT PARSER
# ======================================

def parse_neft_transaction(narration):

    result = empty_parser_result()

    parts = narration.split("/")


    result["transaction_prefix"] = "NEFT"


    # reference id
    if len(parts) >= 2:
        result["reference_id"] = parts[1]


    # entity
    if len(parts) >= 3:

        result["entity_name"] = parts[2]

        result["parse_quality"] = "MEDIUM"


    return result


# ======================================
# IMPS PARSER
# ======================================

def parse_imps_transaction(narration):

    result = empty_parser_result()

    parts = narration.split("/")


    result["transaction_prefix"] = "IMPS"


    # subtype
    if len(parts) >= 2:
        result["transaction_subtype"] = parts[1]


    # reference id
    if len(parts) >= 3:
        result["reference_id"] = parts[2]


    # entity
    if len(parts) >= 4:

        result["entity_name"] = parts[3]

        result["parse_quality"] = "MEDIUM"


    return result


# ======================================
# ATM PARSER
# ======================================

def parse_atm_transaction(narration):

    result = empty_parser_result()

    result["transaction_prefix"] = "ATM"

    result["parse_quality"] = "LOW"

    return result


# ======================================
# CHEQUE PARSER
# ======================================

def parse_cheque_transaction(narration):

    result = empty_parser_result()

    result["transaction_prefix"] = "CHEQUE"

    parts = narration.split("/")


    # cheque reference
    if len(parts) >= 2:

        result["reference_id"] = parts[1]

        result["parse_quality"] = "MEDIUM"


    return result


# ======================================
# PARSER ROUTER
# ======================================

def parse_transaction(row):

    narration = row["Normalized Narration"]

    mode = row["Mode"]


    if mode == "UPI":
        return parse_upi_transaction(narration)


    if mode == "NEFT":
        return parse_neft_transaction(narration)


    if mode == "IMPS":
        return parse_imps_transaction(narration)


    if mode == "ATM":
        return parse_atm_transaction(narration)


    if mode == "CHEQUE":
        return parse_cheque_transaction(narration)


    return empty_parser_result()