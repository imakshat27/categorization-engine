import streamlit as st

    DEFAULT_OLLAMA_MODEL,
from engine.ai_refinement import (
    refine_transactions,
)
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

        classification_columns = [
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

        if "Old Category" in processed_df.columns:

            category_index = classification_columns.index(
                "Category"
            )

            classification_columns.insert(
                category_index + 1,
                "Old Category"
            )

        st.dataframe(

            processed_df[classification_columns]

        )


        # =========================
        # AI REFINEMENT
        # =========================

        st.subheader("AI Refinement")

        refinement_threshold = st.slider(
            "Confidence threshold",
            min_value=0.0,
            max_value=1.0,
            value=0.65,
            step=0.01
        )

        refinement_model = st.text_input(
            "Ollama model",
            value=DEFAULT_OLLAMA_MODEL
        )

        refinement_max_rows = st.number_input(
            "Max rows to refine",
            min_value=1,
            max_value=500,
            value=25,
            step=1
        )

        include_old_category_disagreement = st.checkbox(
            "Include old-vs-new category disagreements",
            value=True
        )

        if st.button("AI Refinement"):

            with st.spinner("Running advisory AI refinement..."):

                refinement_results = refine_transactions(
                    processed_df,
                    threshold=refinement_threshold,
                    model=refinement_model,
                    max_rows=int(refinement_max_rows),
                    include_old_category_disagreement=include_old_category_disagreement
                )

            if refinement_results:

                st.dataframe(
                    refinement_results
                )

            else:

                st.info(
                    "No rows matched the AI refinement routing criteria."
                )

    except Exception as e:

        st.error(f"Error: {e}")
