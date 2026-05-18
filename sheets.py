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


def save_results_with_details(sheet_id, tab_name, results_df, original_guests_df):
    """
    Сохраняет результаты расселения вместе с тарифом, комментарием.
    """
    client = connect()
    sh = client.open_by_key(sheet_id)
    
    df_to_save = results_df.copy()
    
    # Определяем колонку с ФИО (может быть 'fio' или 'ФИО')
    fio_col = 'fio' if 'fio' in df_to_save.columns else 'ФИО'
    
    # Создаем словари для быстрого поиска тарифа и комментария по ФИО
    tariff_dict = {}
    comment_dict = {}
    
    for idx, row in original_guests_df.iterrows():
        fio = row.get('ФИО', '')
        if fio:
            # Ищем колонку с тарифом
            tariff_value = ''
            for col in original_guests_df.columns:
                if 'тариф' in str(col).lower() or 'проживание' in str(col).lower():
                    tariff_value = row.get(col, '')
                    break
            
            # Ищем колонку с комментарием
            comment_value = ''
            for col in original_guests_df.columns:
                if 'коммент' in str(col).lower():
                    comment_value = row.get(col, '')
                    break
            
            tariff_dict[fio] = tariff_value
            comment_dict[fio] = comment_value
    
    # Добавляем колонки с тарифом и комментарием
    df_to_save['Тариф'] = df_to_save[fio_col].map(tariff_dict).fillna('')
    df_to_save['Комментарий'] = df_to_save[fio_col].map(comment_dict).fillna('')
    
    # Переставляем колонки в удобном порядке (опционально)
    columns_order = ['fio', 'room_id', 'room_capacity', 'Дата заезда', 'Дата отъезда', 'Тариф', 'Комментарий']
    existing_columns = [col for col in columns_order if col in df_to_save.columns]
    other_columns = [col for col in df_to_save.columns if col not in existing_columns]
    df_to_save = df_to_save[existing_columns + other_columns]
    
    # Сохраняем в Google Sheets
    try:
        sheet = sh.worksheet(tab_name)
    except:
        sheet = sh.add_worksheet(title=tab_name, rows=2000, cols=50)
    
    sheet.clear()
    df_to_save = df_to_save.fillna("").astype(str)
    data = [df_to_save.columns.tolist()] + df_to_save.values.tolist()
    sheet.update(data)
    
    return df_to_save
