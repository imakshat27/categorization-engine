import re


def safe_keyword_match(keyword, narration):

    pattern = rf'\b{re.escape(keyword)}\b'

    return re.search(
        pattern,
        narration
    ) is not None


def detect_bounce(narration):

    bounce_keywords = [
        "BOUNCE",
        "BOUNCED",
        "RETURN"
    ]

    for keyword in bounce_keywords:

        if safe_keyword_match(
            keyword,
            narration
        ):
            return True

    return False



def detect_charge(narration):

    charge_keywords = [
        "CHARGE",
        "CHARGES",
        "FEE"
    ]

    for keyword in charge_keywords:

        if safe_keyword_match(
            keyword,
            narration
        ):
            return True

    return False



def detect_reversal(narration):

    reversal_keywords = [
        "REV",
        "REVERSAL",
        "REFUND",
        "REVERSED"
    ]

    for keyword in reversal_keywords:

        if safe_keyword_match(
            keyword,
            narration
        ):
            return True

    return False



def detect_salary(narration):

    salary_keywords = [
        "SALARY",
        "PAYROLL"
    ]

    for keyword in salary_keywords:

        if safe_keyword_match(
            keyword,
            narration
        ):
            return True

    return False



def detect_tax(narration):

    keywords = [
        "TAX",
        "GST",
        "TDS"
    ]

    for keyword in keywords:

        if safe_keyword_match(
            keyword,
            narration
        ):
            return True

    return False



def detect_cash(narration):

    keywords = [
        "CASH"
    ]

    for keyword in keywords:

        if safe_keyword_match(
            keyword,
            narration
        ):
            return True

    return False



def detect_deposit(narration):

    keywords = [
        "DEPOSIT",
    ]

    for keyword in keywords:

        if safe_keyword_match(
            keyword,
            narration
        ):
            return True

    return False



def detect_withdrawal(narration):

    keywords = [
        "WITHDRAWAL",
        "WD",
    ]

    for keyword in keywords:

        if safe_keyword_match(
            keyword,
            narration
        ):
            return True

    return False



def detect_atm(narration):

    keywords = [
        "ATM",
        "ATW",
        "NWD"
    ]

    for keyword in keywords:

        if safe_keyword_match(
            keyword,
            narration
        ):
            return True

    return False



def detect_cheque(narration):

    keywords = [
        "CHQ",
        "CHEQUE"
    ]

    for keyword in keywords:

        if safe_keyword_match(
            keyword,
            narration
        ):
            return True

    return False



def detect_investment(narration):

    keywords = [
        "FD",
        "FIXED DEPOSIT",
        "MUTUAL FUND",
        "SIP"
    ]

    for keyword in keywords:

        if safe_keyword_match(
            keyword,
            narration
        ):
            return True

    return False



def detect_insurance(narration):

    keywords = [
        "INSURANCE",
        "LIC"
    ]

    for keyword in keywords:

        if safe_keyword_match(
            keyword,
            narration
        ):
            return True

    return False



def detect_recharge(narration):

    keywords = [
        "RECHARGE"
    ]

    for keyword in keywords:

        if safe_keyword_match(
            keyword,
            narration
        ):
            return True

    return False



def detect_travel(narration):

    keywords = [
        "IRCTC",
        "MAKEMYTRIP",
        "YATRA"
    ]

    for keyword in keywords:

        if safe_keyword_match(
            keyword,
            narration
        ):
            return True

    return False



def detect_utility(narration):

    keywords = [
        "ELECTRICITY",
        "WATER",
        "GAS",
        "BILL"
    ]

    for keyword in keywords:

        if safe_keyword_match(
            keyword,
            narration
        ):
            return True

    return False



def detect_loan(narration):

    keywords = [
        "LOAN",
        "EMI"
    ]

    for keyword in keywords:

        if safe_keyword_match(
            keyword,
            narration
        ):
            return True

    return False