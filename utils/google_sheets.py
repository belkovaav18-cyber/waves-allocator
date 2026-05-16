import pandas as pd
import streamlit as st
from google.oauth2 import service_account
import gspread


def load_guests_from_gsheet():

    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"]
    )

    client = gspread.authorize(creds)

    # Открываем таблицу по названию
    sheet = client.open("регистрация").sheet1

    data = sheet.get_all_records()

    return pd.DataFrame(data)
