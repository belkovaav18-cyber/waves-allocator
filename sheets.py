import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import streamlit as st

# Определяем константы здесь, но они будут переопределены в app.py при импорте
SHEET_ID = "1lF4SV24wTo5OwsidQ7UPqBVaGzdw_fBSx0OuBJJ4cWg"
REGISTRATION_SHEET_ID = "1fHjI0hTtlbjDZxSCWVidzGnJ7aY4joB7UUVXFEB0rxw"
TAB_NAME = "Sheet"

def get_google_client():
    """Подключение к Google Sheets"""
    try:
        # Пытаемся получить секреты из st.secrets
        if 'gcp_service_account' in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            scopes = ['https://www.googleapis.com/auth/spreadsheets', 
                     'https://www.googleapis.com/auth/drive']
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            client = gspread.authorize(creds)
            return client
        else:
            # Для локальной разработки используем json файл
            import json
            with open('credentials.json', 'r') as f:
                creds_dict = json.load(f)
            scopes = ['https://www.googleapis.com/auth/spreadsheets', 
                     'https://www.googleapis.com/auth/drive']
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            client = gspread.authorize(creds)
            return client
    except Exception as e:
        st.warning(f"Не удалось подключиться к Google Sheets: {e}")
        return None

def load_guests(sheet_id, tab_name):
    """Загрузить данные гостей из Google Sheets"""
    client = get_google_client()
    if client is None:
        # Если нет подключения, пробуем загрузить из локального файла
        try:
            return pd.read_excel("data/guests.xlsx")
        except:
            return pd.DataFrame()
    
    try:
        sheet = client.open_by_key(sheet_id)
        worksheet = sheet.worksheet(tab_name)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return pd.DataFrame()

def load_registration_data(sheet_id, tab_name):
    """Загрузить данные регистрации из Google Sheets"""
    client = get_google_client()
    if client is None:
        try:
            return pd.read_excel("data/registration.xlsx")
        except:
            return pd.DataFrame()
    
    try:
        sheet = client.open_by_key(sheet_id)
        worksheet = sheet.worksheet(tab_name)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"Ошибка загрузки данных регистрации: {e}")
        return pd.DataFrame()

def save_results_with_details(sheet_id, sheet_name, result_df, raw_df):
    """Сохранить результаты расселения в Google Sheets"""
    client = get_google_client()
    if client is None:
        st.warning("Нет подключения к Google Sheets, результаты не сохранены")
        return
    
    try:
        sheet = client.open_by_key(sheet_id)
        
        try:
            worksheet = sheet.worksheet(sheet_name)
            worksheet.clear()
        except:
            worksheet = sheet.add_worksheet(title=sheet_name, rows="1000", cols="50")
        
        # Подготавливаем данные для сохранения
        save_df = result_df.copy()
        
        # Добавляем колонку с выбранными услугами из raw_df
        # Используем правильное название колонки - 'ФИО'
        fio_col = 'ФИО' if 'ФИО' in save_df.columns else 'fio'
        
        if fio_col in save_df.columns and 'ФИО' in raw_df.columns:
            services = []
            for fio in save_df[fio_col]:
                guest_row = raw_df[raw_df['ФИО'] == fio]
                if len(guest_row) > 0:
                    selected = []
                    for col in raw_df.columns:
                        if 'Комната' in str(col) or 'Завтрак' in str(col) or 'Обед' in str(col) or 'Ужин' in str(col):
                            val = guest_row.iloc[0].get(col, '')
                            if pd.notna(val) and str(val).strip() and str(val).strip().lower() not in ['', 'нет', '-', 'false', 'nan']:
                                selected.append(col)
                    services.append(", ".join(selected) if selected else "нет")
                else:
                    services.append("нет")
            save_df['выбранные_услуги'] = services
        
        # Сохраняем в worksheet
        worksheet.update([save_df.columns.values.tolist()] + save_df.values.tolist())
        
        st.success(f"Результаты сохранены в Google Sheets на листе '{sheet_name}'")
        
    except Exception as e:
        st.error(f"Ошибка сохранения результатов: {e}")

def save_detailed_results(sheet_id, result_df):
    """Сохранить детальные результаты расселения"""
    client = get_google_client()
    if client is None:
        return
    
    try:
        sheet = client.open_by_key(sheet_id)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sheet_name = f"Расселение_{timestamp}"
        
        try:
            worksheet = sheet.add_worksheet(title=sheet_name, rows="1000", cols="50")
        except:
            worksheet = sheet.worksheet(sheet_name)
            worksheet.clear()
        
        # Сохраняем данные
        worksheet.update([result_df.columns.values.tolist()] + result_df.values.tolist())
        
        # Форматируем заголовки
        worksheet.freeze(rows=1)
        
        st.success(f"Детальные результаты сохранены на листе '{sheet_name}'")
        
    except Exception as e:
        st.error(f"Ошибка сохранения детальных результатов: {e}")
