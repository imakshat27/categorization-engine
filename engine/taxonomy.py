APPROVED_CATEGORIES = [
    "ACH BOUNCED CHARGES",
    "ATM DEPOSIT",
    "ATM WITHDRAWAL",
    "AUTO SWEEP",
    "BANK CHARGES",
    "CASH DEPOSIT",
    "CASH WITHDRAWAL",
    "CHEQUE BOUNCE - NON TECHNICAL",
    "CHEQUE BOUNCE - TECHNICAL",
    "CHEQUE CASH WITHDRAWAL",
    "CHEQUE DEPOSIT",
    "CHEQUE WITHDRAWAL",
    "CREDIT CARD PAYMENT",
    "DEBIT CARD TRANSFER IN",
    "DEBIT CARD TRANSFER OUT",
    "DEMAND DRAFT",
    "E-COMMERCE",
    "ECS BOUNCED CHARGES",
    "ELECTRONIC FUND TRANSFER",
    "FIXED DEPOSIT",
    "FUEL",
    "IMPS BOUNCE CHARGES",
    "IMPS BOUNCE",
    "INSURANCE",
    "INTEREST",
    "INVESTMENTS",
    "LOAN",
    "NEFT BOUNCE",
    "PAYMENT GATEWAY",
    "RECHARGE",
    "REFUND OR REVERSAL",
    "RTGS BOUNCE",
    "SALARY PAID",
    "SALARY RECEIVED",
    "SALARY",
    "TAX",
    "TRANSFER IN",
    "TRANSFER OUT",
    "TRAVEL",
    "UTILITY",
]


APPROVED_CATEGORY_SET = set(APPROVED_CATEGORIES)


TAXONOMY_VERSION = "2026-05-28.1"
CATEGORY_DEFINITION_VERSION = "2026-05-28.1"
VALIDATOR_VERSION = "2026-05-28.1"


CATEGORY_DEFINITIONS = {
    "ACH BOUNCED CHARGES": "ACH mandate bounce or return charges.",
    "ATM DEPOSIT": "Cash deposited through an ATM or automated cash deposit channel.",
    "ATM WITHDRAWAL": "Cash withdrawn through ATM or ATM-like withdrawal channel.",
    "AUTO SWEEP": "Automatic sweep movement between operative balance and linked deposit/sweep facility.",
    "BANK CHARGES": "Bank fees, service charges, rental charges, throughput charges, and transaction charges.",
    "CASH DEPOSIT": "Physical cash deposited into the account.",
    "CASH WITHDRAWAL": "Physical cash withdrawn from the account.",
    "CHEQUE BOUNCE - NON TECHNICAL": "Cheque return due to funds, stop payment, account status, or other non-technical reason.",
    "CHEQUE BOUNCE - TECHNICAL": "Cheque return due to technical reason such as signature, image, MICR, date, or alteration issue.",
    "CHEQUE CASH WITHDRAWAL": "Cheque used to withdraw cash, usually self/cash cheque.",
    "CHEQUE DEPOSIT": "Cheque or clearing instrument credited into the account.",
    "CHEQUE WITHDRAWAL": "Cheque or clearing instrument debited from the account.",
    "CREDIT CARD PAYMENT": "Payment toward a credit card bill or card repayment app.",
    "DEBIT CARD TRANSFER IN": "Incoming reversal/credit/refund through debit card or card network.",
    "DEBIT CARD TRANSFER OUT": "Outgoing debit card, POS, or card network transaction.",
    "DEMAND DRAFT": "Demand draft issue, purchase, cancellation, or related charge.",
    "E-COMMERCE": "Purchase or settlement involving an e-commerce merchant or online marketplace.",
    "ECS BOUNCED CHARGES": "ECS/NACH debit bounce or mandate return charges.",
    "ELECTRONIC FUND TRANSFER": "Generic UPI, IMPS, NEFT, RTGS, or other electronic rail transfer with no stronger semantic intent.",
    "FIXED DEPOSIT": "Fixed deposit booking, sweep deposit, premature proceeds, renewal, or FD-linked movement.",
    "FUEL": "Fuel, petrol, diesel, filling station, or petroleum merchant transaction.",
    "IMPS BOUNCE CHARGES": "IMPS bounce or return charge.",
    "IMPS BOUNCE": "IMPS bounce or returned IMPS movement without explicit charge semantics.",
    "INSURANCE": "Insurance, pension-premium, insurer, policy, or premium payment.",
    "INTEREST": "Interest credit or debit.",
    "INVESTMENTS": "Investment, SIP, mutual fund, demat, brokerage, or investment platform transaction.",
    "LOAN": "Loan EMI, lender/NBFC repayment, loan disbursement, or loan-related debit.",
    "NEFT BOUNCE": "NEFT return or bounce.",
    "PAYMENT GATEWAY": "Payment processor, aggregator, wallet, or gateway settlement where processor role is the semantic intent.",
    "RECHARGE": "Mobile, telecom, prepaid, postpaid, DTH, or recharge transaction.",
    "REFUND OR REVERSAL": "Refund, reversal, failed transaction return, or original-RRN reversal.",
    "RTGS BOUNCE": "RTGS return or bounce.",
    "SALARY PAID": "Salary, payroll, wages, or staff payment debited from the account.",
    "SALARY RECEIVED": "Salary, payroll, or wages credited into the account.",
    "SALARY": "Salary or payroll transaction where direction is unavailable.",
    "TAX": "Tax, GST, TDS, income tax, statutory levy, or government tax payment.",
    "TRANSFER IN": "Incoming non-rail/manual/internal transfer without stronger semantic intent.",
    "TRANSFER OUT": "Outgoing non-rail/manual/internal transfer without stronger semantic intent.",
    "TRAVEL": "Travel, railway, airline, hotel, ride, or travel-platform transaction.",
    "UTILITY": "Bill, rent, electricity, water, gas, broadband, or other utility-style payment.",
}


CATEGORY_COMPATIBILITY_RULES = {
    "ATM DEPOSIT": {"direction": {"IN"}, "requires_any": {"movement_tags": {"atm"}}},
    "ATM WITHDRAWAL": {"direction": {"OUT"}, "requires_any": {"movement_tags": {"atm"}}},
    "CASH DEPOSIT": {"direction": {"IN"}},
    "CASH WITHDRAWAL": {"direction": {"OUT"}},
    "CHEQUE CASH WITHDRAWAL": {"direction": {"OUT"}, "requires_any": {"movement_tags": {"cheque", "cash"}}},
    "CHEQUE DEPOSIT": {"direction": {"IN"}, "requires_any": {"movement_tags": {"cheque"}}},
    "CHEQUE WITHDRAWAL": {"direction": {"OUT"}, "requires_any": {"movement_tags": {"cheque"}}},
    "DEBIT CARD TRANSFER IN": {"direction": {"IN"}, "requires_any": {"movement_tags": {"debit_card"}}},
    "DEBIT CARD TRANSFER OUT": {"direction": {"OUT"}, "requires_any": {"movement_tags": {"debit_card"}}},
    "SALARY PAID": {"direction": {"OUT"}},
    "SALARY RECEIVED": {"direction": {"IN"}},
    "TRANSFER IN": {"direction": {"IN"}},
    "TRANSFER OUT": {"direction": {"OUT"}},
    "IMPS BOUNCE": {"rail": {"IMPS"}},
    "IMPS BOUNCE CHARGES": {"rail": {"IMPS"}},
    "NEFT BOUNCE": {"rail": {"NEFT"}},
    "RTGS BOUNCE": {"rail": {"RTGS"}},
    "ACH BOUNCED CHARGES": {"rail": {"ACH"}},
    "ECS BOUNCED CHARGES": {"rail": {"ECS", "NACH"}},
}


CATEGORY_FAMILIES = {
    "bounce": {
        "ACH BOUNCED CHARGES",
        "ECS BOUNCED CHARGES",
        "IMPS BOUNCE CHARGES",
        "IMPS BOUNCE",
        "NEFT BOUNCE",
        "RTGS BOUNCE",
        "CHEQUE BOUNCE - NON TECHNICAL",
        "CHEQUE BOUNCE - TECHNICAL",
    },
    "cash": {
        "ATM DEPOSIT",
        "ATM WITHDRAWAL",
        "CASH DEPOSIT",
        "CASH WITHDRAWAL",
        "CHEQUE CASH WITHDRAWAL",
    },
    "cheque": {
        "CHEQUE BOUNCE - NON TECHNICAL",
        "CHEQUE BOUNCE - TECHNICAL",
        "CHEQUE CASH WITHDRAWAL",
        "CHEQUE DEPOSIT",
        "CHEQUE WITHDRAWAL",
    },
    "generic_transfer": {
        "ELECTRONIC FUND TRANSFER",
        "TRANSFER IN",
        "TRANSFER OUT",
        "DEBIT CARD TRANSFER IN",
        "DEBIT CARD TRANSFER OUT",
    },
    "merchant_intent": {
        "CREDIT CARD PAYMENT",
        "E-COMMERCE",
        "FUEL",
        "INSURANCE",
        "LOAN",
        "PAYMENT GATEWAY",
        "RECHARGE",
        "TRAVEL",
        "UTILITY",
    },
}


CATEGORY_PRECEDENCE = {
    "REFUND OR REVERSAL": 1000,
    "ACH BOUNCED CHARGES": 980,
    "ECS BOUNCED CHARGES": 980,
    "IMPS BOUNCE CHARGES": 970,
    "IMPS BOUNCE": 960,
    "NEFT BOUNCE": 960,
    "RTGS BOUNCE": 960,
    "CHEQUE BOUNCE - NON TECHNICAL": 955,
    "CHEQUE BOUNCE - TECHNICAL": 955,
    "BANK CHARGES": 930,
    "SALARY RECEIVED": 910,
    "SALARY PAID": 910,
    "SALARY": 900,
    "TAX": 890,
    "INTEREST": 880,
    "CREDIT CARD PAYMENT": 870,
    "LOAN": 860,
    "INSURANCE": 850,
    "FIXED DEPOSIT": 840,
    "AUTO SWEEP": 830,
    "INVESTMENTS": 820,
    "DEMAND DRAFT": 810,
    "CHEQUE CASH WITHDRAWAL": 800,
    "CHEQUE DEPOSIT": 790,
    "CHEQUE WITHDRAWAL": 790,
    "ATM DEPOSIT": 780,
    "ATM WITHDRAWAL": 780,
    "CASH DEPOSIT": 770,
    "CASH WITHDRAWAL": 770,
    "DEBIT CARD TRANSFER IN": 760,
    "DEBIT CARD TRANSFER OUT": 760,
    "FUEL": 740,
    "UTILITY": 730,
    "RECHARGE": 720,
    "TRAVEL": 710,
    "E-COMMERCE": 700,
    "PAYMENT GATEWAY": 650,
    "ELECTRONIC FUND TRANSFER": 500,
    "TRANSFER IN": 420,
    "TRANSFER OUT": 420,
}


RAIL_CATEGORIES = {
    "UPI": "ELECTRONIC FUND TRANSFER",
    "IMPS": "ELECTRONIC FUND TRANSFER",
    "NEFT": "ELECTRONIC FUND TRANSFER",
    "RTGS": "ELECTRONIC FUND TRANSFER",
}


FALLBACK_CATEGORY_BY_DIRECTION = {
    "IN": "TRANSFER IN",
    "OUT": "TRANSFER OUT",
    "UNKNOWN": "ELECTRONIC FUND TRANSFER",
}


PARSER_QUALITY_MULTIPLIER = {
    "HIGH": 1.0,
    "MEDIUM": 0.92,
    "LOW": 0.82,
    "UNKNOWN": 0.78,
}


CONFLICT_PENALTIES = {
    "movement_direction_conflict": 0.18,
    "deposit_withdrawal_conflict": 0.14,
    "parser_low_quality": 0.08,
    "weak_fallback": 0.16,
    "rail_entity_ambiguity": 0.08,
    "processor_entity_ambiguity": 0.10,
    "competing_hypotheses": 0.08,
    "entity_category_disagreement": 0.08,
}


REVIEW_CONFIDENCE_THRESHOLD = 0.65
