def detect_bounce(narration):

    bounce_keywords = [
        "BOUNCE",
        "BOUNCED",
        "RETURN"
    ]

    for keyword in bounce_keywords:

        if keyword in narration:
            return True

    return False



def detect_charge(narration):

    charge_keywords = [
        "CHARGE",
        "CHARGES",
        "FEE"
    ]

    for keyword in charge_keywords:

        if keyword in narration:
            return True

    return False



def detect_reversal(narration):

    reversal_keywords = [
        "REVERSAL",
        "REFUND",
        "REVERSED"
    ]

    for keyword in reversal_keywords:

        if keyword in narration:
            return True

    return False



def detect_salary(narration):

    salary_keywords = [
        "SALARY",
        "PAYROLL"
    ]

    for keyword in salary_keywords:

        if keyword in narration:
            return True

    return False


def detect_tax(narration):

    keywords = [
        "TAX",
        "GST",
        "TDS"
    ]

    return any(
        keyword in narration
        for keyword in keywords
    )



def detect_cash(narration):

    keywords = [
        "CASH"
    ]

    return any(
        keyword in narration
        for keyword in keywords
    )



def detect_deposit(narration):

    keywords = [
        "DEPOSIT",
        "CR"
    ]

    return any(
        keyword in narration
        for keyword in keywords
    )



def detect_withdrawal(narration):

    keywords = [
        "WITHDRAWAL",
        "WD",
        "DR"
    ]

    return any(
        keyword in narration
        for keyword in keywords
    )



def detect_atm(narration):

    keywords = [
        "ATM"
    ]

    return any(
        keyword in narration
        for keyword in keywords
    )



def detect_cheque(narration):

    keywords = [
        "CHQ",
        "CHEQUE"
    ]

    return any(
        keyword in narration
        for keyword in keywords
    )



def detect_investment(narration):

    keywords = [
        "FD",
        "FIXED DEPOSIT",
        "MUTUAL FUND",
        "SIP"
    ]

    return any(
        keyword in narration
        for keyword in keywords
    )



def detect_insurance(narration):

    keywords = [
        "INSURANCE",
        "LIC"
    ]

    return any(
        keyword in narration
        for keyword in keywords
    )



def detect_recharge(narration):

    keywords = [
        "RECHARGE"
    ]

    return any(
        keyword in narration
        for keyword in keywords
    )



def detect_travel(narration):

    keywords = [
        "IRCTC",
        "MAKEMYTRIP",
        "YATRA"
    ]

    return any(
        keyword in narration
        for keyword in keywords
    )



def detect_utility(narration):

    keywords = [
        "ELECTRICITY",
        "WATER",
        "GAS",
        "BILL"
    ]

    return any(
        keyword in narration
        for keyword in keywords
    )



def detect_loan(narration):

    keywords = [
        "LOAN",
        "EMI"
    ]

    return any(
        keyword in narration
        for keyword in keywords
    )