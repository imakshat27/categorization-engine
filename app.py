import streamlit as st

from engine.loader import load_transactions


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
# LOAD DATA
# =========================

if uploaded_file and sheet_name:

    try:

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

    except Exception as e:

        st.error(f"Error: {e}")