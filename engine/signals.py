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