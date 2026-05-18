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


def save_results_with_details(sheet_id, tab_name, results_df, original_guests_df):
    """
    Сохраняет результаты расселения вместе с тарифом и комментарием из исходной таблицы.
    
    Параметры:
    - sheet_id: ID гугл таблицы
    - tab_name: название листа для сохранения
    - results_df: DataFrame с результатами расселения (должен содержать колонку 'fio' или 'ФИО')
    - original_guests_df: исходный DataFrame с гостями (содержит колонки 'ФИО', 'Выбор тарифа за проживание', 'Комментарий')
    """
    client = connect()
    sh = client.open_by_key(sheet_id)
    
    # Создаем копию results_df, чтобы не изменять оригинал
    df_to_save = results_df.copy()
    
    # Определяем колонку с ФИО (может быть 'fio' или 'ФИО')
    fio_col = 'fio' if 'fio' in df_to_save.columns else 'ФИО'
    
    # Создаем словарь для быстрого поиска тарифа и комментария по ФИО
    tariff_dict = {}
    comment_dict = {}
    
    for idx, row in original_guests_df.iterrows():
        fio = row.get('ФИО', '')
        if fio:
            tariff_dict[fio] = row.get('Выбор тарифа за проживание', '')
            comment_dict[fio] = row.get('Комментарий (например, пожелания по расселению)', '')
    
    # Добавляем колонки в df_to_save
    df_to_save['Выбор тарифа за проживание'] = df_to_save[fio_col].map(tariff_dict).fillna('')
    df_to_save['Комментарий'] = df_to_save[fio_col].map(comment_dict).fillna('')
    
    # Сохраняем в Google Sheets
    try:
        sheet = sh.worksheet(tab_name)
    except:
        sheet = sh.add_worksheet(title=tab_name, rows=2000, cols=50)
    
    sheet.clear()
    
    df_to_save = df_to_save.fillna("").astype(str)
    data = [df_to_save.columns.tolist()] + df_to_save.values.tolist()
    sheet.update(data)
    
    return df_to_save  # возвращаем обогащенный DataFrame на всякий случай


# Оригинальная функция save_results оставлена для обратной совместимости
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
