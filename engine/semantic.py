import re

from engine.entity_registry import ENTITY_REGISTRY
from engine.matcher import (
    any_token_match,
    clean_entity_text,
    first_token_match,
    regex_match,
    token_match,
)
from engine.parser import parse_transaction


RAIL_TERMS = {
    "UPI": ["UPI", "UPIAR", "UPI/RRN", "REV-UPI"],
    "IMPS": ["IMPS", "SENTIMPS", "IMPSP2A"],
    "NEFT": ["NEFT"],
    "RTGS": ["RTGS"],
    "ATM": ["ATM", "NWD", "ATW"],
    "CHEQUE": ["CHQ", "CHEQUE", "CLG", "MICR"],
    "ECS": ["ECS"],
    "ACH": ["ACH"],
    "NACH": ["NACH"],
}


INTENT_RULES = {
    "reversal": {
        "terms": ["REV", "REVERSAL", "REFUND", "REVERSED", "ORIGINAL RRN", "FAILED"],
        "regex": [r"\bREV[- /]?UPI\b", r"\bUPI/REV\b"],
    },
    "bounce": {
        "terms": ["BOUNCE", "BOUNCED", "RTN", "DISHONOUR", "DISHONOURED"],
        "regex": [
            r"\bCHQ\s+RTN\b",
            r"\bI/W\s+CHQ\s+RTN\b",
            r"\b(ACH|ECS|NACH|IMPS|NEFT|RTGS)\b.*\bRETURN(?:ED)?\b",
        ],
    },
    "charge": {
        "terms": ["CHARGE", "CHARGES", "CHRG", "FEE", "FEES", "RENTAL", "THROUGHPUT"],
        "regex": [r"\bCHRG:"],
    },
    "salary": {
        "terms": ["SALARY", "PAYROLL", "WAGES"],
        "regex": [],
    },
    "tax": {
        "terms": ["TAX", "GST", "TDS", "INCOME TAX"],
        "regex": [],
    },
    "interest": {
        "terms": ["INTEREST", "CREDIT INTEREST"],
        "regex": [],
    },
    "investment": {
        "terms": ["INVESTMENT", "INVESTMENTS", "MUTUAL FUND", "SIP", "DEMAT"],
        "regex": [],
    },
    "insurance": {
        "terms": ["INSURANCE", "PREMIUM", "LIC", "PRAN", "APY"],
        "regex": [],
    },
    "recharge": {
        "terms": ["RECHARGE", "PREPAID", "POSTPAID"],
        "regex": [],
    },
    "travel": {
        "terms": ["IRCTC", "MAKEMYTRIP", "YATRA", "TRAVEL"],
        "regex": [],
    },
    "utility": {
        "terms": ["ELECTRICITY", "WATER", "GAS", "BILL PAYMENT", "BILL", "RENT"],
        "regex": [],
    },
    "loan": {
        "terms": ["LOAN", "EMI"],
        "regex": [],
    },
    "fuel": {
        "terms": ["FUEL", "PETROL", "DIESEL", "FILLING", "FILLINGS"],
        "regex": [],
    },
    "fixed_deposit": {
        "terms": ["FIXED DEPOSIT", "FD", "FD PREMAT", "PREMAT PROCEEDS"],
        "regex": [r"\bSWEEP\s+TRF\s+FROM\b", r"\bSWEEP\s+TRANSFER\s+TO\b"],
    },
    "auto_sweep": {
        "terms": ["AUTO SWEEP"],
        "regex": [],
    },
    "credit_card_payment": {
        "terms": ["CREDIT CARD", "CC PAYMENT", "CCBP", "CARD PAYMENT"],
        "regex": [],
    },
    "demand_draft": {
        "terms": ["DEMAND DRAFT", "DD ISSUE", "DD CHARGES"],
        "regex": [r"(?<![A-Z0-9])DD(?![A-Z0-9])"],
    },
    "direct_debit": {
        "terms": ["DIRECT DEBIT", "NACH", "ECS", "ACH"],
        "regex": [],
    },
}


MOVEMENT_RULES = {
    "cash": {
        "terms": ["CASH", "CASHRC"],
        "regex": [],
    },
    "deposit": {
        "terms": ["DEPOSIT", "DEP"],
        "regex": [r"\bCASHRC:?\s*DEPOSIT\b"],
    },
    "withdrawal": {
        "terms": ["WITHDRAWAL", "WDL", "WD"],
        "regex": [],
    },
    "atm": {
        "terms": ["ATM", "NWD", "ATW"],
        "regex": [r"\bATM\s+WDL\b"],
    },
    "cheque": {
        "terms": ["CHQ", "CHEQUE", "CLG", "MICR"],
        "regex": [r"\bBY\s+CLG\s+INST\b", r"\bI/W\s+CHQ\b"],
    },
    "manual_transfer": {
        "terms": ["KOTAKPAYOUT", "FRIEND OR FAMILY", "FRM TRF", "TO TRF", "FUND TRF"],
        "regex": [r"^\s*\d{5,}[A-Z].*BANK"],
    },
    "debit_card": {
        "terms": ["DEBIT CARD", "VISA", "RUPAY", "MASTER CARD", "MASTERCARD"],
        "regex": [r"\bPOS\b"],
    },
}


NON_TECHNICAL_BOUNCE_TERMS = [
    "FUNDSINSUFFICIENT",
    "FUNDS INSUFFICIENT",
    "INSUFFICIENT FUNDS",
    "ACCOUNT CLOSED",
    "PAYMENT STOPPED",
    "STOP PAYMENT",
]


TECHNICAL_BOUNCE_TERMS = [
    "SIGNATURE",
    "DRAWER SIGNATURE",
    "TECHNICAL",
    "IMAGE",
    "MICR MISMATCH",
    "ALTERATION",
    "DATE INVALID",
]


def empty_semantic_facts():
    return {
        "protocol": {
            "rail": "UNKNOWN",
            "family": "UNKNOWN",
            "subtype": "UNKNOWN",
            "reference_id": "UNKNOWN",
            "counterparty": "UNKNOWN",
            "bank": "UNKNOWN",
            "instrument_no": "UNKNOWN",
            "handle": "UNKNOWN",
            "parser_rule": "NO_PARSER_MATCH",
            "parse_quality": "LOW",
            "parser_confidence": 0.20,
        },
        "entity": {
            "canonical": "UNKNOWN",
            "category": "UNKNOWN",
            "role": "UNKNOWN",
            "confidence": 0.0,
            "ambiguity": "UNKNOWN",
            "matched_alias": "UNKNOWN",
        },
        "movement": {
            "direction": "UNKNOWN",
            "direction_source": "amount_columns",
            "tags": [],
            "instrument_type": "UNKNOWN",
        },
        "intent": {
            "tags": [],
            "bounce_type": "UNKNOWN",
        },
        "bank_family": {
            "bank": "UNKNOWN",
            "family": "UNKNOWN",
            "confidence": 0.0,
        },
        "matches": [],
    }


def detect_direction(row):
    debit = row.get("Debits")
    credit = row.get("Credits")

    try:
        if debit is not None and float(debit) > 0:
            return "OUT"
    except (TypeError, ValueError):
        pass

    try:
        if credit is not None and float(credit) > 0:
            return "IN"
    except (TypeError, ValueError):
        pass

    return "UNKNOWN"


def _add_match(facts, match, layer):
    if not match:
        return

    item = dict(match)
    item["layer"] = layer
    facts["matches"].append(item)


def _detect_rail(narration):
    for rail, terms in RAIL_TERMS.items():
        match = first_token_match(
            terms,
            narration,
            rule_name=f"{rail}_RAIL",
            source="protocol",
        )

        if match:
            return rail, match

    return "UNKNOWN", None


def _detect_entity(text):
    best = None

    for entity in ENTITY_REGISTRY:
        for alias in entity["aliases"]:
            match = token_match(
                alias,
                text,
                rule_name=f"ENTITY_{entity['canonical']}",
                source="entity",
            )

            if not match:
                continue

            score = entity["confidence"]

            if best is None or score > best["confidence"]:
                best = {
                    "canonical": entity["canonical"],
                    "category": entity["category"],
                    "role": entity["role"],
                    "confidence": entity["confidence"],
                    "ambiguity": entity["ambiguity"],
                    "matched_alias": alias,
                    "match": match,
                }

    if best is None:
        return {
            "canonical": "UNKNOWN",
            "category": "UNKNOWN",
            "role": "UNKNOWN",
            "confidence": 0.0,
            "ambiguity": "UNKNOWN",
            "matched_alias": "UNKNOWN",
        }

    match = best.pop("match")
    best["match"] = match
    return best


def _detect_rule_tags(rule_map, narration):
    tags = []
    matches = []

    for tag, config in rule_map.items():
        tag_matches = []
        tag_matches.extend(
            any_token_match(
                config.get("terms", []),
                narration,
                rule_name=f"{tag.upper()}_TERM",
                source=tag,
            )
        )

        for pattern in config.get("regex", []):
            match = regex_match(
                pattern,
                narration,
                rule_name=f"{tag.upper()}_REGEX",
                source=tag,
            )

            if match:
                tag_matches.append(match)

        if tag_matches:
            tags.append(tag)
            matches.extend(tag_matches)

    return tags, matches


def _detect_bounce_type(narration):
    if first_token_match(TECHNICAL_BOUNCE_TERMS, narration, source="bounce_type"):
        return "TECHNICAL"

    if first_token_match(NON_TECHNICAL_BOUNCE_TERMS, narration, source="bounce_type"):
        return "NON_TECHNICAL"

    return "UNKNOWN"


def _detect_bank_family(narration, bank):
    checks = [
        ("KOTAK_PAYOUT", r"\bKOTAKPAYOUT[-/]", 0.86),
        ("SWEEP_FIXED_DEPOSIT", r"\bSWEEP\s+(TRF\s+FROM|TRANSFER\s+TO)\b", 0.90),
        ("CENTRAL_BANK_CASH_RECEIPT", r"\bCASHRC:?", 0.78),
        ("CHEQUE_CLEARING", r"\b(BY\s+CLG\s+INST|MICR\s+INWARD|CLG\s+TO)\b", 0.86),
        ("BANK_CHARGE", r"\bCHRG:|\bCHARGE\b|\bCHARGES\b", 0.88),
        ("DIRECT_DEBIT", r"\bDIRECT\s+DEBIT\b", 0.78),
        ("MANUAL_BENEFICIARY_TRANSFER", r"^\s*\d{5,}[A-Z].*BANK", 0.70),
    ]

    for family, pattern, confidence in checks:
        match = regex_match(
            pattern,
            narration,
            rule_name=f"BANK_FAMILY_{family}",
            source="bank_family",
        )

        if match:
            return {
                "bank": bank or "UNKNOWN",
                "family": family,
                "confidence": confidence,
                "match": match,
            }

    return {
        "bank": bank or "UNKNOWN",
        "family": "UNKNOWN",
        "confidence": 0.0,
    }


def build_semantic_facts(row):
    facts = empty_semantic_facts()
    narration = row.get("Normalized Narration", "")
    raw_narration = row.get("Narration", narration)
    bank = row.get("Bank", "UNKNOWN")

    protocol = parse_transaction(row)
    facts["protocol"].update(protocol)

    rail, rail_match = _detect_rail(narration)

    if rail != "UNKNOWN" and facts["protocol"]["rail"] == "UNKNOWN":
        facts["protocol"]["rail"] = rail

    _add_match(facts, rail_match, "protocol")

    facts["movement"]["direction"] = detect_direction(row)

    movement_tags, movement_matches = _detect_rule_tags(MOVEMENT_RULES, narration)
    facts["movement"]["tags"] = movement_tags

    for match in movement_matches:
        _add_match(facts, match, "movement")

    intent_tags, intent_matches = _detect_rule_tags(INTENT_RULES, narration)
    facts["intent"]["tags"] = intent_tags
    facts["intent"]["bounce_type"] = _detect_bounce_type(narration)

    for match in intent_matches:
        _add_match(facts, match, "intent")

    counterparty_text = " ".join(
        [
            str(facts["protocol"].get("counterparty", "")),
            str(row.get("Remarks", "")),
            str(raw_narration),
        ]
    )
    facts["entity"] = _detect_entity(clean_entity_text(counterparty_text))

    if "match" in facts["entity"]:
        _add_match(facts, facts["entity"].pop("match"), "entity")

    facts["bank_family"] = _detect_bank_family(narration, bank)

    if "match" in facts["bank_family"]:
        _add_match(facts, facts["bank_family"].pop("match"), "bank_family")

    if "atm" in movement_tags:
        facts["movement"]["instrument_type"] = "ATM"
    elif "cheque" in movement_tags:
        facts["movement"]["instrument_type"] = "CHEQUE"
    elif "cash" in movement_tags:
        facts["movement"]["instrument_type"] = "CASH"
    elif "debit_card" in movement_tags:
        facts["movement"]["instrument_type"] = "DEBIT_CARD"

    return facts
