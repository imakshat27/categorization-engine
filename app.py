import pandas as pd
import streamlit as st
from engine.ai_refinement import DEFAULT_OLLAMA_MODEL, DEFAULT_ROUTING_POLICY, refine_transactions
# from engine.huggingface_refinement import (
#     DEFAULT_HUGGINGFACE_MODEL,
#     HUGGINGFACE_MODEL_OPTIONS,
#     refine_transactions_with_huggingface,
# )
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

        refinement_routing_policy = st.selectbox(
            "AI routing policy",
            options=["balanced", "strict", "exploratory"],
            index=["balanced", "strict", "exploratory"].index(DEFAULT_ROUTING_POLICY)
        )

        include_old_category_disagreement = st.checkbox(
            "Include old-vs-new category disagreements",
            value=True
        )

        refinement_audit_logging = st.checkbox(
            "Full audit logging",
            value=False
        )

        if st.button("AI Refinement"):

            with st.spinner("Running advisory AI refinement..."):

                refinement_results = refine_transactions(
                    processed_df,
                    threshold=refinement_threshold,
                    model=refinement_model,
                    max_rows=int(refinement_max_rows),
                    include_old_category_disagreement=include_old_category_disagreement,
                    routing_policy=refinement_routing_policy,
                    log_skipped="summary",
                    log_detail="audit" if refinement_audit_logging else "summary"
                )

            if refinement_results:

                refinement_df = pd.DataFrame(refinement_results)
                outcome_counts = refinement_df["AI Outcome"].value_counts()
                metric_columns = st.columns(4)
                metric_columns[0].metric("Reviewed", len(refinement_df))
                metric_columns[1].metric(
                    "Engine fixes",
                    int(outcome_counts.get("ENGINE_FIX_NEEDED", 0))
                )
                metric_columns[2].metric(
                    "Change candidates",
                    int(outcome_counts.get("CATEGORY_CHANGE_SUGGESTED", 0))
                )
                metric_columns[3].metric(
                    "Confirmed",
                    int(outcome_counts.get("CATEGORY_CONFIRMED", 0))
                )

                display_columns = [
                    "Row Index",
                    "Narration",
                    "Old Category",
                    "Category",
                    "Confidence",
                    "AI Outcome",
                    "AI Suggested Category",
                    "AI Mentioned Category",
                    "AI Finding",
                    "AI Proposed Action",
                    "AI Missing Signal",
                    "AI Confidence Advisory",
                    "AI Routing Reason",
                ]
                display_columns = [
                    column for column in display_columns
                    if column in refinement_df.columns
                ]

                st.dataframe(
                    refinement_df[display_columns]
                )

                rejected_df = refinement_df[
                    refinement_df["Validation Status"] == "REJECTED"
                ]

                if not rejected_df.empty:
                    with st.expander("Rejected model outputs"):
                        rejected_columns = [
                            "Row Index",
                            "Narration",
                            "AI Decision",
                            "AI Suggested Category",
                            "AI Mentioned Category",
                            "Validation Errors",
                        ]
                        rejected_columns = [
                            column for column in rejected_columns
                            if column in rejected_df.columns
                        ]

                        st.dataframe(
                            rejected_df[rejected_columns]
                        )

            else:

                st.info(
                    "No rows matched the AI refinement routing criteria."
                )


        # =========================
        # HUGGING FACE AI REFINEMENT
        # =========================
        #
        # st.subheader("Hugging Face AI Refinement")
        #
        # hf_refinement_threshold = st.slider(
        #     "Low-confidence threshold",
        #     min_value=0.0,
        #     max_value=1.0,
        #     value=0.65,
        #     step=0.01,
        #     key="hf_refinement_threshold"
        # )
        #
        # hf_model_preset = st.selectbox(
        #     "Hugging Face model route",
        #     options=HUGGINGFACE_MODEL_OPTIONS + ["Custom"],
        #     index=HUGGINGFACE_MODEL_OPTIONS.index(DEFAULT_HUGGINGFACE_MODEL),
        #     key="hf_model_preset"
        # )
        #
        # hf_custom_model = st.text_input(
        #     "Custom Hugging Face model route",
        #     value="",
        #     disabled=hf_model_preset != "Custom",
        #     key="hf_custom_model"
        # )
        # st.caption(
        #     "Use a model route supported by an enabled provider. If Custom is selected, paste the exact string from the Hugging Face Playground."
        # )
        #
        # hf_refinement_model = (
        #     hf_custom_model.strip()
        #     if hf_model_preset == "Custom" and hf_custom_model.strip()
        #     else hf_model_preset
        # )
        #
        # hf_access_token = st.text_input(
        #     "Hugging Face access token",
        #     type="password",
        #     key="hf_access_token"
        # )
        #
        # hf_refinement_max_rows = st.number_input(
        #     "Max rows to refine",
        #     min_value=1,
        #     max_value=500,
        #     value=25,
        #     step=1,
        #     key="hf_refinement_max_rows"
        # )
        #
        # hf_include_old_category_disagreement = st.checkbox(
        #     "Include old-vs-new category disagreements",
        #     value=False,
        #     key="hf_include_old_category_disagreement"
        # )
        #
        # hf_request_json_response = st.checkbox(
        #     "Request provider JSON mode",
        #     value=False,
        #     key="hf_request_json_response"
        # )
        # st.caption(
        #     "Leave this off if the hosted provider returns 400 for response_format. The local validator still extracts and validates JSON."
        # )
        #
        # if st.button(
        #     "Hugging Face Refinement",
        #     key="hf_refinement_button"
        # ):
        #
        #     with st.spinner("Running Hugging Face refinement..."):
        #
        #         hf_refinement_results = refine_transactions_with_huggingface(
        #             processed_df,
        #             threshold=hf_refinement_threshold,
        #             model=hf_refinement_model,
        #             token=hf_access_token.strip() or None,
        #             max_rows=int(hf_refinement_max_rows),
        #             include_old_category_disagreement=hf_include_old_category_disagreement,
        #             request_json_response=hf_request_json_response
        #         )
        #
        #     if hf_refinement_results:
        #
        #         st.dataframe(
        #             hf_refinement_results
        #         )
        #
        #     else:
        #
        #         st.info(
        #             "No rows matched the Hugging Face refinement routing criteria."
        #         )

    except Exception as e:

        st.error(f"Error: {e}")
