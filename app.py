import streamlit as st

from engine.loader import load_transactions
from engine.pipeline import process_transactions


# =========================
# PAGE CONFIG
# =========================

st.set_page_config(
    page_title="Categorization Engine",
    layout="wide"
)


# =========================
# TITLE
# =========================

st.title("Transaction Categorization Engine")


# =========================
# FILE UPLOAD
# =========================

uploaded_file = st.file_uploader(
    "Upload Excel File",
    type=["xlsx"]
)


# =========================
# SHEET NAME INPUT
# =========================

sheet_name = st.text_input(
    "Enter Sheet Name",
    value="Xns Transactions"
)


# =========================
# LOAD + PROCESS
# =========================

if uploaded_file and sheet_name:

    try:

        # load raw dataframe
        df = load_transactions(
            uploaded_file,
            sheet_name
        )

        st.success("File Loaded Successfully")


        # =========================
        # RAW DATA
        # =========================

        st.subheader("Raw Transactions")

        st.dataframe(df)


        # =========================
        # PROCESS PIPELINE
        # =========================

        processed_df = process_transactions(df)


        # =========================
        # NORMALIZED OUTPUT
        # =========================

        # st.subheader("Normalized Transactions")

        # st.dataframe(

        #     processed_df[
        #         [
        #             "Narration",
        #             "Normalized Narration"
        #         ]
        #     ]

        # )


        # =========================
        # PARSER OUTPUT
        # =========================

        st.subheader("Transaction Parsing Output")

        st.dataframe(

            processed_df[
                [
                    "Normalized Narration",

                    "Transaction Prefix",
                    "Transaction Subtype",
                    "Protocol Family",

                    "Reference ID",

                    "Entity Name",
                    "Bank Name",

                    "UPI ID",
                    "UPI Handle",
                    "Parser Rule",
                    "Parser Confidence"
                ]
            ]

        )
        


        # =========================
        # FINAL OUTPUT
        # =========================

        st.subheader("Classification Output")

        st.dataframe(

            processed_df[
                [
                    "Narration",
                    "Normalized Narration",

                    "Direction",
                    "Mode",

                    "Entity Name",
                    "UPI ID",
                    "UPI Handle",
                    "Parse Quality",
                    "Protocol Family",
                    "Parser Rule",
                    "Parser Confidence",
                    "Instrument Type",
                    "Intent Tags",
                    "Movement Tags",
                    "Bank Family",
                    "Merchant",

                    "Bounce Flag",
                    "Charge Flag",
                    "Reversal Flag",
                    "Salary Flag",
                    "Tax Flag",
                    "Cash Flag",
                    "Deposit Flag",
                    "Withdrawal Flag",
                    "ATM Flag",
                    "Cheque Flag",
                    "Investment Flag",
                    "Insurance Flag",
                    "Recharge Flag",
                    "Travel Flag",
                    "Utility Flag",
                    "Loan Flag",
                    "Entity Type",
                    "Entity Confidence",
                    "Transaction Prefix",
                    "Transaction Subtype",
                    "Reference ID",
                    "Bank Name",
                    "Confidence",
                    "Decision Path",
                    "Conflicts",
                    "Ranked Candidates",
                    "Alternative Categories",
                    "Review Required",
                    "Review Reason",
                    "Evidence Summary",
                    "Category",
                    "Matched Rule",
                ]
            ]

        )

    except Exception as e:

        st.error(f"Error: {e}")
