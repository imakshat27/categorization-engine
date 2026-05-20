import pandas as pd


def load_transactions(file, sheet_name):

    # read excel sheet
    df = pd.read_excel(
        file,
        sheet_name=sheet_name
    )

    # clean column names
    df.columns = [col.strip() for col in df.columns]

    return df