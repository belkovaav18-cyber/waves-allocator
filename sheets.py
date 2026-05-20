import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import streamlit as st

def get_google_client():
    """Подключение к Google Sheets"""
    try:
        if 'gcp_service_account' in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            scopes = ['https://www.googleapis.com/auth/spreadsheets', 
                     'https://www.googleapis.com/auth/drive']
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            client = gspread.authorize(creds)
            return client
        else:
            import json
            try:
                with open('credentials.json', 'r') as f:
                    creds_dict = json.load(f)
                scopes = ['https://www.googleapis.com/auth/spreadsheets', 
                         'https://www.googleapis.com/auth/drive']
                creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
                client = gspread.authorize(creds)
                return client
            except:
                return None
    except Exception as e:
        st.warning(f"Не удалось подключиться к Google Sheets: {e}")
        return None

def load_guests(sheet_id, tab_name):
    """Загрузить данные гостей из Google Sheets"""
    client = get_google_client()
    if client is None:
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

def save_results_with_details(sheet_id, sheet_name, result_df, raw_df, guests_df):
    """Сохранить результаты расселения в Google Sheets"""
    client = get_google_client()
    if client is None:
        st.warning("Нет подключения к Google Sheets, результаты не сохранены")
        return
    
    try:
        sheet = client.open_by_key(sheet_id)
        
        # Удаляем старый лист если есть
        try:
            old_worksheet = sheet.worksheet(sheet_name)
            sheet.del_worksheet(old_worksheet)
        except:
            pass
        
        # Создаем новый лист
        worksheet = sheet.add_worksheet(title=sheet_name, rows="1000", cols="50")
        
        # Подготавливаем данные для сохранения
        save_df = result_df.copy()
        
        # Добавляем возраст и должность из guests_df
        guests_info = {}
        for _, row in guests_df.iterrows():
            fio = row.get('ФИО', '')
            if fio:
                guests_info[fio] = {
                    'возраст': row.get('возраст', ''),
                    'должность': row.get('должность', ''),
                    'город': row.get('город', ''),
                    'организация': row.get('организация', ''),
                    'email': row.get('email', ''),
                    'телефон': row.get('телефон', '')
                }
        
        # Определяем колонку с ФИО
        fio_col = 'ФИО' if 'ФИО' in save_df.columns else 'fio' if 'fio' in save_df.columns else None
        
        if fio_col:
            # Добавляем колонки
            ages = [guests_info.get(fio, {}).get('возраст', '') for fio in save_df[fio_col]]
            positions = [guests_info.get(fio, {}).get('должность', '') for fio in save_df[fio_col]]
            cities = [guests_info.get(fio, {}).get('город', '') for fio in save_df[fio_col]]
            orgs = [guests_info.get(fio, {}).get('организация', '') for fio in save_df[fio_col]]
            emails = [guests_info.get(fio, {}).get('email', '') for fio in save_df[fio_col]]
            phones = [guests_info.get(fio, {}).get('телефон', '') for fio in save_df[fio_col]]
            
            # Вставляем колонки после ФИО
            save_df.insert(1, 'возраст', ages)
            save_df.insert(2, 'должность', positions)
            save_df.insert(3, 'город', cities)
            save_df.insert(4, 'организация', orgs)
            save_df.insert(5, 'email', emails)
            save_df.insert(6, 'телефон', phones)
        
        # Добавляем даты если их нет
        if 'Дата заезда' not in save_df.columns:
            save_df['Дата заезда'] = ''
        if 'Дата отъезда' not in save_df.columns:
            save_df['Дата отъезда'] = ''
        
        # Заполняем пустые значения
        save_df = save_df.fillna('')
        
        # Сохраняем в worksheet
        data = [save_df.columns.values.tolist()] + save_df.values.tolist()
        worksheet.update(data)
        
        # Замораживаем заголовки
        worksheet.freeze(rows=1)
        
        st.success(f"Результаты сохранены в Google Sheets на листе '{sheet_name}'")
        
    except Exception as e:
        st.error(f"Ошибка сохранения результатов: {e}")
        import traceback
        traceback.print_exc()

def save_detailed_results(sheet_id, result_df):
    """Сохранить детальные результаты расселения"""
    client = get_google_client()
    if client is None:
        return
    
    try:
        sheet = client.open_by_key(sheet_id)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sheet_name = f"Расселение_{timestamp}"
        
        worksheet = sheet.add_worksheet(title=sheet_name, rows="1000", cols="50")
        
        # Сохраняем данные
        data = [result_df.columns.values.tolist()] + result_df.values.tolist()
        worksheet.update(data)
        worksheet.freeze(rows=1)
        
        st.success(f"Детальные результаты сохранены на листе '{sheet_name}'")
        
    except Exception as e:
        st.error(f"Ошибка сохранения детальных результатов: {e}")
