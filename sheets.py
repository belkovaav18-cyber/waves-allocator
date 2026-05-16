import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def connect():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    return gspread.authorize(creds)


def load_guests(sheet_id, tab_name) -> pd.DataFrame:
    client = connect()
    sheet = client.open_by_key(sheet_id).worksheet(tab_name)
    return pd.DataFrame(sheet.get_all_records())


def save_results(sheet_id, tab_name, df: pd.DataFrame):

    client = connect()
    sh = client.open_by_key(sheet_id)

    try:
        sheet = sh.worksheet(tab_name)
    except:
        sheet = sh.add_worksheet(title=tab_name, rows=2000, cols=50)

    sheet.clear()

    df = df.fillna("").astype(str)

    data = [df.columns.tolist()] + df.values.tolist()

    sheet.update(data)
