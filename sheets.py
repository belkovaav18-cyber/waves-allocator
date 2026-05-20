import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import streamlit as st

def get_google_client():
    try:
        if 'gcp_service_account' in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            scopes = ['https://www.googleapis.com/auth/spreadsheets', 
                     'https://www.googleapis.com/auth/drive']
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            return gspread.authorize(creds)
    except:
        return None

def load_guests(sheet_id, tab_name):
    client = get_google_client()
    if client is None:
        try:
            return pd.read_excel("data/guests.xlsx")
        except:
            return pd.DataFrame()
    try:
        sheet = client.open_by_key(sheet_id)
        worksheet = sheet.worksheet(tab_name)
        return pd.DataFrame(worksheet.get_all_records())
    except Exception as e:
        st.error(f"Ошибка загрузки: {e}")
        return pd.DataFrame()

def load_registration_data(sheet_id, tab_name):
    client = get_google_client()
    if client is None:
        try:
            return pd.read_excel("data/registration.xlsx")
        except:
            return pd.DataFrame()
    try:
        sheet = client.open_by_key(sheet_id)
        worksheet = sheet.worksheet(tab_name)
        return pd.DataFrame(worksheet.get_all_records())
    except Exception as e:
        st.error(f"Ошибка загрузки: {e}")
        return pd.DataFrame()

def save_results_with_details(sheet_id, sheet_name, result_df, raw_df, guests_df):
    client = get_google_client()
    if client is None:
        st.warning("Нет подключения к Google Sheets")
        return
    try:
        sheet = client.open_by_key(sheet_id)
        try:
            old = sheet.worksheet(sheet_name)
            sheet.del_worksheet(old)
        except:
            pass
        worksheet = sheet.add_worksheet(title=sheet_name, rows="1000", cols="50")
        
        save_df = result_df.copy()
        for col in save_df.columns:
            if col in ['возраст', 'тариф', 'число_ночей', 'стоимость', 'room_capacity']:
                save_df[col] = pd.to_numeric(save_df[col], errors='coerce').fillna(0).astype(int)
            else:
                save_df[col] = save_df[col].astype(str).replace('nan', '').replace('None', '')
        
        data = [save_df.columns.values.tolist()] + save_df.values.tolist()
        worksheet.update(data)
        worksheet.freeze(rows=1)
        st.success(f"Сохранено в Google Sheets")
    except Exception as e:
        st.error(f"Ошибка сохранения: {e}")
