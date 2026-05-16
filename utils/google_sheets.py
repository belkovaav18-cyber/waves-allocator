import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials


SPREADSHEET_ID = "10cBNkDQ3fOCajBIjeAsaCPsivEfVShGZ-BHmLcC6l5s"
SHEET_NAME = "Лист1"


def load_guests_from_gsheet():

    credentials_info = dict(st.secrets["gcp_service_account"])

    # FIX private key
    if "private_key" in credentials_info:
        credentials_info["private_key"] = credentials_info["private_key"].replace("\\n", "\n")

    creds = Credentials.from_service_account_info(
        credentials_info,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )

    client = gspread.authorize(creds)

    sh = client.open_by_key(SPREADSHEET_ID)
    worksheet = sh.worksheet(SHEET_NAME)

    data = worksheet.get_all_records()

    return pd.DataFrame(data)
def save_allocations_to_gsheet(df, sheet_name="Расселение"):

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

    client = gspread.authorize(creds)

    sh = client.open_by_key("10cBNkDQ3fOCajBIjeAsaCPsivEfVShGZ-BHmLcC6l5s")

    # пробуем открыть лист
    try:
        worksheet = sh.worksheet(sheet_name)
        worksheet.clear()
    except:
        worksheet = sh.add_worksheet(title=sheet_name, rows="1000", cols="20")

    # записываем данные
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())
