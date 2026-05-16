import streamlit as st
import gspread
import pandas as pd

from google.oauth2.service_account import Credentials


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


# =========================
# CONNECT
# =========================
def connect():

    if "gcp_service_account" not in st.secrets:
        raise RuntimeError(
            "Missing st.secrets['gcp_service_account']"
        )

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )

    return gspread.authorize(creds)


# =========================
# LOAD GENERIC SHEET
# =========================
def load_sheet(sheet_id: str, tab_name: str) -> pd.DataFrame:

    client = connect()

    sh = client.open_by_key(sheet_id)

    try:
        ws = sh.worksheet(tab_name)
    except Exception:
        return pd.DataFrame()

    data = ws.get_all_records()

    return pd.DataFrame(data)


# =========================
# ALIASES (ВАЖНО!)
# =========================
def load_guests(sheet_id: str, tab_name: str):
    return load_sheet(sheet_id, tab_name)


def load_rooms(sheet_id: str, tab_name: str):
    return load_sheet(sheet_id, tab_name)


# =========================
# SAVE RESULTS
# =========================
def save_results(sheet_id: str, tab_name: str, df: pd.DataFrame):

    if df is None or len(df) == 0:
        return

    client = connect()
    sh = client.open_by_key(sheet_id)

    tabs = [ws.title for ws in sh.worksheets()]

    if tab_name not in tabs:
        sh.add_worksheet(
            title=tab_name,
            rows=2000,
            cols=50
        )

    ws = sh.worksheet(tab_name)
    ws.clear()

    df = df.fillna("").astype(str)

    data = [df.columns.tolist()] + df.values.tolist()

    ws.update(values=data)
