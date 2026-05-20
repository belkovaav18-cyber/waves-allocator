import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import streamlit as st
import numpy as np

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

def convert_to_serializable(df):
    """Преобразует DataFrame в сериализуемый формат"""
    df = df.copy()
    for col in df.columns:
        if col == 'возраст' or col == 'тариф' or col == 'число_ночей' or col == 'стоимость':
            df[col] = df[col].apply(lambda x: int(x) if pd.notna(x) and str(x).strip() and str(x) != 'nan' else 0)
        else:
            df[col] = df[col].apply(lambda x: str(x) if pd.notna(x) and str(x) != 'nan' else '')
    return df

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
        
        save_df = result_df.copy()
        
        # Добавляем даты если их нет
        if 'Дата заезда' not in save_df.columns:
            save_df['Дата заезда'] = ''
        if 'Дата отъезда' not in save_df.columns:
            save_df['Дата отъезда'] = ''
        
        # Порядок колонок
        column_order = ['ФИО', 'пол', 'возраст', 'должность', 'город', 'организация',
                       'room_id', 'room_capacity', 'Дата заезда', 'Дата отъезда',
                       'число_ночей', 'тариф', 'стоимость', 'comment']
        
        existing_cols = [col for col in column_order if col in save_df.columns]
        other_cols = [col for col in save_df.columns if col not in existing_cols]
        final_cols = existing_cols + other_cols
        
        save_df = save_df[final_cols]
        save_df = save_df.fillna('')
        
        # Конвертируем типы
        save_df = convert_to_serializable(save_df)
        
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
        
        # Конвертируем в сериализуемый формат
        result_df = convert_to_serializable(result_df)
        
        # Сохраняем данные
        data = [result_df.columns.values.tolist()] + result_df.values.tolist()
        worksheet.update(data)
        worksheet.freeze(rows=1)
        
        st.success(f"Детальные результаты сохранены на листе '{sheet_name}'")
        
    except Exception as e:
        st.error(f"Ошибка сохранения детальных результатов: {e}")
