import re

from engine.matcher import clean_entity_text, regex_match


def empty_parser_result():
    return {
        "transaction_prefix": "UNKNOWN",
        "transaction_subtype": "UNKNOWN",
        "reference_id": "UNKNOWN",
        "entity_name": "UNKNOWN",
        "bank_name": "UNKNOWN",
        "upi_id": "UNKNOWN",
        "upi_handle": "UNKNOWN",
        "parse_quality": "LOW",
        "rail": "UNKNOWN",
        "family": "UNKNOWN",
        "subtype": "UNKNOWN",
        "counterparty": "UNKNOWN",
        "bank": "UNKNOWN",
        "instrument_no": "UNKNOWN",
        "handle": "UNKNOWN",
        "parser_rule": "NO_PARSER_MATCH",
        "parser_confidence": 0.20,
    }


def _finalize(result):
    result["subtype"] = result.get("transaction_subtype", "UNKNOWN")
    result["counterparty"] = result.get("entity_name", "UNKNOWN")
    result["bank"] = result.get("bank_name", "UNKNOWN")
    result["handle"] = result.get("upi_handle", "UNKNOWN")
    return result


def _set_quality(result, quality, confidence):
    result["parse_quality"] = quality
    result["parser_confidence"] = confidence


def _extract_upi_id(result, narration):
    match = re.search(r"[\w.-]+@[\w.-]+", narration)

    if not match:
        return

    upi_id = match.group(0).upper()
    result["upi_id"] = upi_id

    if "@" in upi_id:
        result["upi_handle"] = upi_id.split("@", 1)[1]


def parse_upi_transaction(narration):
    result = empty_parser_result()
    result["rail"] = "UPI"
    _extract_upi_id(result, narration)

    if regex_match(r"\bUPI/REV\s+([0-9]+)", narration):
        match = re.search(r"\bUPI/REV\s+([0-9]+)", narration, re.IGNORECASE)
        result.update(
            {
                "transaction_prefix": "UPI",
                "transaction_subtype": "REV",
                "reference_id": match.group(1),
                "entity_name": "REVERSAL",
                "family": "UPI_REVERSAL",
                "parser_rule": "UPI_REVERSAL_RRN",
            }
        )
        _set_quality(result, "HIGH", 0.94)
        return _finalize(result)

    if regex_match(r"\bREV[- /]?UPI\b", narration):
        parts = narration.split("/")
        result.update(
            {
                "transaction_prefix": "REV-UPI",
                "transaction_subtype": "REV",
                "family": "UPI_REVERSAL",
                "parser_rule": "REV_UPI_SLASH",
            }
        )

        if len(parts) >= 2:
            result["entity_name"] = clean_entity_text(parts[1])

        if len(parts) >= 3:
            result["reference_id"] = parts[2]

        _set_quality(result, "HIGH", 0.92)
        return _finalize(result)

    match = re.search(
        r"\bUPI/RRN\s*([0-9]+)\s*/\s*(.*)$",
        narration,
        re.IGNORECASE,
    )

    if match:
        result.update(
            {
                "transaction_prefix": "UPI",
                "transaction_subtype": "RRN",
                "reference_id": match.group(1),
                "entity_name": clean_entity_text(match.group(2)),
                "family": "UPI_RRN",
                "parser_rule": "UPI_RRN",
            }
        )
        _set_quality(result, "HIGH", 0.92)
        return _finalize(result)

    parts = [part.strip() for part in narration.split("/") if part.strip()]

    if parts and parts[0].startswith("UPI"):
        result["transaction_prefix"] = parts[0]
        result["family"] = "UPI_SLASH"
        result["parser_rule"] = "UPI_SLASH"

        if len(parts) >= 2:
            result["entity_name"] = clean_entity_text(parts[1])

        if len(parts) >= 3:
            if re.fullmatch(r"[0-9]{6,}", parts[2]):
                result["reference_id"] = parts[2]
            else:
                result["transaction_subtype"] = clean_entity_text(parts[2])

        if len(parts) >= 4:
            if result["reference_id"] == "UNKNOWN" and re.fullmatch(r"[0-9]{6,}", parts[3]):
                result["reference_id"] = parts[3]
            elif result["transaction_subtype"] == "UNKNOWN":
                result["transaction_subtype"] = clean_entity_text(parts[3])

        if len(parts) >= 5:
            result["bank_name"] = clean_entity_text(parts[4])

        _set_quality(result, "HIGH" if result["reference_id"] != "UNKNOWN" else "MEDIUM", 0.88)
        return _finalize(result)

    result["parser_rule"] = "UPI_WEAK"
    _set_quality(result, "LOW", 0.40)
    return _finalize(result)


def parse_imps_transaction(narration):
    result = empty_parser_result()
    result["rail"] = "IMPS"
    result["transaction_prefix"] = "IMPS"

    match = re.search(
        r"\bRECD:?IMPS/([0-9]+)/([^/]+)/([^/]+)(?:/([^/]+))?",
        narration,
        re.IGNORECASE,
    )

    if match:
        result.update(
            {
                "family": "IMPS_RECEIVED",
                "parser_rule": "IMPS_RECEIVED_SLASH",
                "transaction_subtype": "RECD",
                "reference_id": match.group(1),
                "entity_name": clean_entity_text(match.group(2)),
                "bank_name": clean_entity_text(match.group(3)),
            }
        )
        _set_quality(result, "HIGH", 0.90)
        return _finalize(result)

    match = re.search(
        r"\bSENT\s*IMPS\s*([0-9]+)([A-Z0-9 ._-]+?)/([A-Z]{3,}[A-Z0-9]*)",
        narration,
        re.IGNORECASE,
    )

    if not match:
        match = re.search(
            r"\bSENTIMPS([0-9]+)([A-Z0-9 ._-]+?)/([A-Z]{3,}[A-Z0-9]*)",
            narration,
            re.IGNORECASE,
        )

    if match:
        result.update(
            {
                "family": "IMPS_SENT",
                "parser_rule": "IMPS_SENT_COMPACT",
                "transaction_subtype": "SENT",
                "reference_id": match.group(1),
                "entity_name": clean_entity_text(match.group(2)),
                "bank_name": clean_entity_text(match.group(3)),
            }
        )
        _set_quality(result, "HIGH", 0.88)
        return _finalize(result)

    match = re.search(
        r"\bIMPSP2A([0-9]+)\s+(.+)$",
        narration,
        re.IGNORECASE,
    )

    if match:
        result.update(
            {
                "family": "IMPS_P2A",
                "parser_rule": "IMPS_P2A",
                "transaction_subtype": "P2A",
                "reference_id": match.group(1),
                "entity_name": clean_entity_text(match.group(2)),
            }
        )
        _set_quality(result, "HIGH", 0.88)
        return _finalize(result)

    parts = [part.strip() for part in narration.split("/") if part.strip()]

    if "IMPS" in narration and parts:
        result["family"] = "IMPS_GENERIC"
        result["parser_rule"] = "IMPS_GENERIC"

        if len(parts) >= 2:
            result["reference_id"] = parts[1] if re.search(r"[0-9]{6,}", parts[1]) else "UNKNOWN"

        if len(parts) >= 3:
            result["entity_name"] = clean_entity_text(parts[2])

        _set_quality(result, "MEDIUM", 0.68)
        return _finalize(result)

    _set_quality(result, "LOW", 0.35)
    return _finalize(result)


def parse_neft_transaction(narration):
    result = empty_parser_result()
    result["rail"] = "NEFT"
    result["transaction_prefix"] = "NEFT"
    result["family"] = "NEFT"
    result["parser_rule"] = "NEFT_TEXT"

    match = re.search(
        r"\bNEFT\s+(.+?)\s+([A-Z]{2,}[A-Z0-9]*[0-9]{4,})\b",
        narration,
        re.IGNORECASE,
    )

    if match:
        result["entity_name"] = clean_entity_text(match.group(1))
        result["reference_id"] = match.group(2)
        _set_quality(result, "HIGH", 0.86)
        return _finalize(result)

    parts = narration.split("/")

    if len(parts) >= 2:
        result["reference_id"] = parts[1]

    if len(parts) >= 3:
        result["entity_name"] = clean_entity_text(parts[2])

    _set_quality(result, "MEDIUM", 0.66)
    return _finalize(result)


def parse_rtgs_transaction(narration):
    result = empty_parser_result()
    result["rail"] = "RTGS"
    result["transaction_prefix"] = "RTGS"
    result["family"] = "RTGS"
    result["parser_rule"] = "RTGS_TEXT"
    _set_quality(result, "MEDIUM", 0.66)
    return _finalize(result)


def parse_atm_transaction(narration):
    result = empty_parser_result()
    result["rail"] = "ATM"
    result["transaction_prefix"] = "ATM"
    result["family"] = "ATM"
    result["parser_rule"] = "ATM_TEXT"
    result["entity_name"] = clean_entity_text(narration.replace("ATM", ""))
    _set_quality(result, "MEDIUM", 0.70)
    return _finalize(result)


def parse_cheque_transaction(narration):
    result = empty_parser_result()
    result["rail"] = "CHEQUE"
    result["transaction_prefix"] = "CHEQUE"
    result["family"] = "CHEQUE"
    result["parser_rule"] = "CHEQUE_TEXT"

    match = re.search(r"(?<![0-9])([0-9]{2,})(?=[:/\s-])", narration)

    if match:
        result["instrument_no"] = match.group(1)
        result["reference_id"] = match.group(1)

    result["entity_name"] = clean_entity_text(narration)
    _set_quality(result, "MEDIUM", 0.70)
    return _finalize(result)


def parse_generic_transaction(narration):
    result = empty_parser_result()
    result["entity_name"] = clean_entity_text(narration)

    if re.search(r"\bACH\b", narration, re.IGNORECASE):
        result.update({"rail": "ACH", "transaction_prefix": "ACH", "family": "ACH", "parser_rule": "ACH_TEXT"})
        _set_quality(result, "MEDIUM", 0.66)
    elif re.search(r"\bECS\b|\bNACH\b", narration, re.IGNORECASE):
        result.update({"rail": "ECS", "transaction_prefix": "ECS", "family": "ECS_NACH", "parser_rule": "ECS_NACH_TEXT"})
        _set_quality(result, "MEDIUM", 0.66)
    elif re.search(r"\bDIRECT\s+DEBIT\b", narration, re.IGNORECASE):
        result.update({"rail": "DIRECT_DEBIT", "transaction_prefix": "DIRECT_DEBIT", "family": "DIRECT_DEBIT", "parser_rule": "DIRECT_DEBIT_TEXT"})
        _set_quality(result, "MEDIUM", 0.62)
    elif re.search(r"\bKOTAKPAYOUT\b", narration, re.IGNORECASE):
        result.update({"rail": "INTERNAL", "transaction_prefix": "KOTAKPAYOUT", "family": "PAYOUT", "parser_rule": "KOTAK_PAYOUT"})
        _set_quality(result, "MEDIUM", 0.72)
    elif re.search(r"\bSWEEP\b|\bFD\b|\bFIXED\s+DEPOSIT\b", narration, re.IGNORECASE):
        result.update({"rail": "INTERNAL", "transaction_prefix": "SWEEP_FD", "family": "SWEEP_FIXED_DEPOSIT", "parser_rule": "SWEEP_FIXED_DEPOSIT"})
        _set_quality(result, "MEDIUM", 0.74)

    return _finalize(result)


def parse_transaction(row):
    narration = row.get("Normalized Narration", "")

    if re.search(r"\bUPI\b|REV[- /]?UPI", narration, re.IGNORECASE):
        return parse_upi_transaction(narration)

    if re.search(r"\bIMPS\b|\bSENTIMPS|\bIMPSP2A", narration, re.IGNORECASE):
        return parse_imps_transaction(narration)

    if re.search(r"\bNEFT\b", narration, re.IGNORECASE):
        return parse_neft_transaction(narration)

    if re.search(r"\bRTGS\b", narration, re.IGNORECASE):
        return parse_rtgs_transaction(narration)

    if re.search(r"\bATM\b|\bATM\s+WDL\b|\bNWD\b|\bATW\b", narration, re.IGNORECASE):
        return parse_atm_transaction(narration)

    if re.search(r"\bCHQ\b|\bCHEQUE\b|\bCLG\b|\bMICR\b", narration, re.IGNORECASE):
        return parse_cheque_transaction(narration)

    return parse_generic_transaction(narration)
