import streamlit as st
import gspread
import pandas as pd

from google.oauth2.service_account import Credentials


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]


def connect():

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )

    return gspread.authorize(creds)


def load_guests(tab_name):

    client = connect()

    sheet_id = st.secrets["sheets"]["sheet_id"]

    sheet = client.open_by_key(sheet_id).worksheet(tab_name)

    data = sheet.get_all_records()

    return pd.DataFrame(data)


def save_results(tab_name, df):

    client = connect()

    sheet_id = st.secrets["sheets"]["sheet_id"]

    sheet = client.open_by_key(sheet_id).worksheet(tab_name)

    sheet.clear()

    sheet.update(
        [df.columns.values.tolist()] +
        df.values.tolist()
    )
