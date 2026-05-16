import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials


# =========================
# CLEAN DATA FOR GOOGLE SHEETS
# =========================
def clean_for_gsheet(df):

    df = df.copy()

    for col in df.columns:
        df[col] = df[col].apply(
            lambda x: "" if pd.isna(x) else str(x)
        )

    return df


# =========================
# AUTH
# =========================
def get_client():

    credentials_info = dict(st.secrets["gcp_service_account"])

    if "private_key" in credentials_info:
        credentials_info["private_key"] = credentials_info["private_key"].replace("\\n", "\n")

    creds = Credentials.from_service_account_info(
        credentials_info,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )

    return gspread.authorize(creds)


SPREADSHEET_ID = "1lF4SV24wTo5OwsidQ7UPqBVaGzdw_fBSx0OuBJJ4cWg"
SHEET_NAME = "Sheet"


# =========================
# LOAD GUESTS
# =========================
def load_guests_from_gsheet():

    client = get_client()

    sh = client.open_by_key(SPREADSHEET_ID)
    worksheet = sh.worksheet(SHEET_NAME)

    data = worksheet.get_all_records()

    return pd.DataFrame(data)


# =========================
# SAVE RESULTS
# =========================
def save_allocations_to_gsheet(df, sheet_name="Расселение"):

    client = get_client()
    sh = client.open_by_key(SPREADSHEET_ID)

    # open or create sheet
    try:
        worksheet = sh.worksheet(sheet_name)
        worksheet.clear()
    except:
        worksheet = sh.add_worksheet(title=sheet_name, rows="1000", cols="20")

    # 🔥 IMPORTANT: CLEAN DATA
    df = clean_for_gsheet(df)

    values = [df.columns.tolist()] + df.values.tolist()

    worksheet.update(values)
