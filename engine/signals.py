from engine.matcher import first_token_match, regex_match


def safe_keyword_match(keyword, narration):
    return first_token_match([keyword], narration) is not None


def _detect(narration, terms=None, regexes=None):
    terms = terms or []
    regexes = regexes or []

    if first_token_match(terms, narration):
        return True

    for pattern in regexes:
        if regex_match(pattern, narration):
            return True

    return False


def detect_bounce(narration):
    return _detect(
        narration,
        ["BOUNCE", "BOUNCED", "RTN", "DISHONOUR", "DISHONOURED"],
        [
            r"\bCHQ\s+RTN\b",
            r"\bI/W\s+CHQ\s+RTN\b",
            r"\b(ACH|ECS|NACH|IMPS|NEFT|RTGS)\b.*\bRETURN(?:ED)?\b",
        ],
    )


def detect_charge(narration):
    return _detect(
        narration,
        ["CHARGE", "CHARGES", "CHRG", "FEE", "FEES", "RENTAL", "THROUGHPUT"],
        [r"\bCHRG:"],
    )


def detect_reversal(narration):
    return _detect(
        narration,
        ["REV", "REVERSAL", "REFUND", "REVERSED", "ORIGINAL RRN", "FAILED"],
        [r"\bREV[- /]?UPI\b", r"\bUPI/REV\b"],
    )


def detect_salary(narration):
    return _detect(narration, ["SALARY", "PAYROLL", "WAGES"])


def detect_tax(narration):
    return _detect(narration, ["TAX", "GST", "TDS", "INCOME TAX"])


def detect_cash(narration):
    return _detect(narration, ["CASH", "CASHRC"])


def detect_deposit(narration):
    return _detect(narration, ["DEPOSIT", "DEP"], [r"\bCASHRC:?\s*DEPOSIT\b"])


def detect_withdrawal(narration):
    return _detect(narration, ["WITHDRAWAL", "WDL", "WD"])


def detect_atm(narration):
    return _detect(narration, ["ATM", "ATW", "NWD"], [r"\bATM\s+WDL\b"])


def detect_cheque(narration):
    return _detect(
        narration,
        ["CHQ", "CHEQUE", "CLG", "MICR"],
        [r"\bBY\s+CLG\s+INST\b", r"\bI/W\s+CHQ\b"],
    )


def detect_investment(narration):
    return _detect(narration, ["INVESTMENT", "INVESTMENTS", "MUTUAL FUND", "SIP", "DEMAT"])


def detect_insurance(narration):
    return _detect(narration, ["INSURANCE", "LIC", "APY", "PRAN", "PREMIUM"])


def detect_recharge(narration):
    return _detect(narration, ["RECHARGE", "PREPAID", "POSTPAID"])


def detect_travel(narration):
    return _detect(narration, ["IRCTC", "MAKEMYTRIP", "MAKE MY TRIP", "YATRA", "TRAVEL"])


def detect_utility(narration):
    return _detect(narration, ["ELECTRICITY", "WATER", "GAS", "BILL PAYMENT", "BILL", "RENT"])


def detect_loan(narration):
    return _detect(narration, ["LOAN", "EMI"])
