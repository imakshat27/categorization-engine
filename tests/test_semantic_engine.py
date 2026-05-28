import unittest

import pandas as pd

from engine.matcher import token_match
from engine.parser import parse_transaction
from engine.pipeline import process_transactions
from engine.taxonomy import APPROVED_CATEGORY_SET


def classify_one(narration, debits=None, credits=None, **extra):
    row = {
        "Bank": "Test Bank",
        "Cheque No": "",
        "Narration": narration,
        "Remarks": "",
        "Debits": debits,
        "Credits": credits,
    }
    row.update(extra)
    return process_transactions(pd.DataFrame([row])).iloc[0]


class SemanticEngineTests(unittest.TestCase):
    def test_token_matching_is_boundary_safe(self):
        self.assertIsNone(token_match("REV", "FOREVER STORE"))
        self.assertIsNone(token_match("GAS", "RANGASAISRAVANTH"))
        self.assertIsNotNone(token_match("REV", "UPI/REV 416057667127/ORIGINAL RRN"))

    def test_parser_extracts_protocol_families_once(self):
        upi = parse_transaction({"Normalized Narration": "UPI/RRN 412288007493/UPI"})
        self.assertEqual(upi["rail"], "UPI")
        self.assertEqual(upi["family"], "UPI_RRN")
        self.assertEqual(upi["reference_id"], "412288007493")

        imps = parse_transaction({"Normalized Narration": "SentIMPS421717626944Saareporc/UTIBX9075/SAAR"})
        self.assertEqual(imps["rail"], "IMPS")
        self.assertEqual(imps["family"], "IMPS_SENT")
        self.assertEqual(imps["reference_id"], "421717626944")

        achd = parse_transaction({"Normalized Narration": "ACHD/HDBFINANCIALSERVIC/HDBFIN90DIHK"})
        self.assertEqual(achd["rail"], "ACH")
        self.assertEqual(achd["family"], "ACH_DEBIT")
        self.assertEqual(achd["counterparty"], "HDBFINANCIALSERVIC")

    def test_generic_rail_becomes_electronic_fund_transfer(self):
        result = classify_one("UPI/RRN 412288007493/UPI", debits=240.9)
        self.assertEqual(result["Category"], "ELECTRONIC FUND TRANSFER")
        self.assertGreaterEqual(result["Confidence"], 0.65)

    def test_entity_can_override_rail_with_conflict_provenance(self):
        result = classify_one(
            "UPI/SUPER FILLINGS/425547609685/NA",
            debits=2000,
            Remarks="SUPER FILLINGS",
        )
        self.assertEqual(result["Category"], "FUEL")
        self.assertIn("rail_entity_ambiguity", result["Conflicts"])
        self.assertIn("ELECTRONIC FUND TRANSFER", result["Ranked Candidates"])

    def test_payment_channel_does_not_auto_override_rail(self):
        result = classify_one(
            "UPI/RRN 412384753669/Payment from PhonePe",
            debits=20000,
            Remarks="PAYMENT FROM PHONEPE",
        )
        self.assertEqual(result["Category"], "ELECTRONIC FUND TRANSFER")
        self.assertNotIn("processor_entity_ambiguity", result["Conflicts"])

    def test_achd_finance_counterparties_classify_as_loans(self):
        examples = [
            "ACHD/GROWTHSOURCEFINANC/020520240718",
            "ACHD/HDBFINANCIALSERVIC/HDBFIN90DIHK",
        ]

        for narration in examples:
            with self.subTest(narration=narration):
                result = classify_one(narration, debits=1000)
                self.assertEqual(result["Mode"], "ACH")
                self.assertEqual(result["Protocol Family"], "ACH_DEBIT")
                self.assertEqual(result["Category"], "LOAN")

    def test_old_category_column_is_not_semantic_truth(self):
        result = classify_one(
            "UPI/IRCTC/123456789/NA",
            debits=500,
            Category="TRANSFER OUT",
            Remarks="IRCTC",
        )
        self.assertEqual(result["Category"], "TRAVEL")
        self.assertEqual(result["Old Category"], "TRANSFER OUT")

    def test_fallback_stays_inside_approved_taxonomy(self):
        result = classify_one("UNRECOGNIZED LOCAL ENTRY", debits=123)
        self.assertEqual(result["Category"], "TRANSFER OUT")
        self.assertTrue(result["Review Required"])
        self.assertIn(result["Category"], APPROVED_CATEGORY_SET)

    def test_all_approved_categories_have_representative_paths(self):
        cases = {
            "ACH BOUNCED CHARGES": ("ACH BOUNCED CHARGES MANDATE", 118, None),
            "ATM DEPOSIT": ("ATM CASH DEPOSIT", None, 5000),
            "ATM WITHDRAWAL": ("ATM WDL BDCCB018", 10000, None),
            "AUTO SWEEP": ("AUTO SWEEP TRANSFER", 2000, None),
            "BANK CHARGES": ("Chrg: IMPS Transaction Dated On 30-Jul-2024", 5.9, None),
            "CASH DEPOSIT": ("CASH DEPOSIT BY SELF", None, 5000),
            "CASH WITHDRAWAL": ("CASH WITHDRAWAL BY SELF", 5000, None),
            "CHEQUE BOUNCE - NON TECHNICAL": ("I/W CHQ RTN:38:FUNDSINSUFFICIENT", None, 30000),
            "CHEQUE BOUNCE - TECHNICAL": ("I/W CHQ RTN SIGNATURE MISMATCH", None, 30000),
            "CHEQUE CASH WITHDRAWAL": ("CHEQUE CASH WITHDRAWAL SELF", 25000, None),
            "CHEQUE DEPOSIT": ("BY CLG INST 11029 HDFC LUCKNOW", None, 19780),
            "CHEQUE WITHDRAWAL": ("CLG TO SHIVAJI TRADERS BANK OF INDIA", 23400, None),
            "CREDIT CARD PAYMENT": ("CREDIT CARD PAYMENT HDFC", 9000, None),
            "DEBIT CARD TRANSFER IN": ("DEBIT CARD CREDIT VISA", None, 500),
            "DEBIT CARD TRANSFER OUT": ("DEBIT CARD POS PURCHASE", 500, None),
            "DEMAND DRAFT": ("DEMAND DRAFT ISSUE", 1000, None),
            "E-COMMERCE": ("UPI/FLIPKART/123456789/NA", 380, None),
            "ECS BOUNCED CHARGES": ("ECS BOUNCED CHARGES", 250, None),
            "ELECTRONIC FUND TRANSFER": ("UPI/RRN 412288007493/UPI", 240, None),
            "FIXED DEPOSIT": ("SWEEP TRANSFER TO [1771652141]", 300000, None),
            "FUEL": ("UPI/SUPER FILLINGS/425547609685/NA", 2000, None),
            "IMPS BOUNCE CHARGES": ("IMPS BOUNCE CHARGES", 100, None),
            "IMPS BOUNCE": ("IMPS BOUNCE", None, 100),
            "INSURANCE": ("APY-PREMIUM FOR PRAN 500415537723", 76, None),
            "INTEREST": ("CREDIT INTEREST", None, 68),
            "INVESTMENTS": ("Investment", 21500, None),
            "LOAN": ("DIRECT DEBIT-DR-BAJAJ FINANCELTD-P456PDB12589723", 18026, None),
            "NEFT BOUNCE": ("NEFT BOUNCE RETURNED", None, 100),
            "PAYMENT GATEWAY": ("RAZORPAY SETTLEMENT", None, 5000),
            "RECHARGE": ("UPI/Jio Postpaid Bi/422685380758/NA", 470, None),
            "REFUND OR REVERSAL": ("UPI/REV 416057667127/ ORIGINAL RRN 416057667127", None, 10000),
            "RTGS BOUNCE": ("RTGS BOUNCE RETURNED", None, 100),
            "SALARY PAID": ("SALARY PAYROLL", 100000, None),
            "SALARY RECEIVED": ("SALARY PAYROLL", None, 100000),
            "SALARY": ("SALARY PAYROLL", None, None),
            "TAX": ("GST TAX PAYMENT", 1000, None),
            "TRANSFER IN": ("KOTAKPAYOUT-0795191A0092878-030824", None, 600),
            "TRANSFER OUT": ("FRIEND OR FAMILY", 5000, None),
            "TRAVEL": ("UPI/IRCTC/123456789/NA", 500, None),
            "UTILITY": ("Bill Payment Electricity", 1000, None),
        }

        for expected, (narration, debits, credits) in cases.items():
            with self.subTest(category=expected):
                result = classify_one(narration, debits=debits, credits=credits)
                self.assertEqual(result["Category"], expected)
                self.assertIn(result["Category"], APPROVED_CATEGORY_SET)


if __name__ == "__main__":
    unittest.main()
