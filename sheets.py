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
    """Сохранить результаты расселения в Google Sheets с возрастом и должностью"""
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
        # Создаем словарь для быстрого поиска
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
            # Добавляем колонки с возрастом и должностью
            ages = []
            positions = []
            cities = []
            orgs = []
            emails = []
            phones = []
            
            for fio in save_df[fio_col]:
                info = guests_info.get(fio, {})
                ages.append(info.get('возраст', ''))
                positions.append(info.get('должность', ''))
                cities.append(info.get('город', ''))
                orgs.append(info.get('организация', ''))
                emails.append(info.get('email', ''))
                phones.append(info.get('телефон', ''))
            
            save_df['возраст'] = ages
            save_df['должность'] = positions
            save_df['город'] = cities
            save_df['организация'] = orgs
            save_df['email'] = emails
            save_df['телефон'] = phones
        
        # Добавляем даты заезда/отъезда если их нет
        if 'Дата заезда' not in save_df.columns:
            save_df['Дата заезда'] = ''
        if 'Дата отъезда' not in save_df.columns:
            save_df['Дата отъезда'] = ''
        
        # Выбираем колонки для сохранения в правильном порядке
        columns_order = [fio_col, 'возраст', 'должность', 'город', 'организация', 
                        'room_id', 'room_capacity', 'Дата заезда', 'Дата отъезда', 
                        'comment', 'email', 'телефон']
        
        existing_columns = [col for col in columns_order if col in save_df.columns]
        save_df = save_df[existing_columns]
        
        # Заменяем пустые значения
        save_df = save_df.fillna('')
        
        # Сохраняем в worksheet
        worksheet.update([save_df.columns.values.tolist()] + save_df.values.tolist())
        
        # Форматируем заголовки
        worksheet.freeze(rows=1)
        
        # Устанавливаем ширину колонок
        column_widths = {
            'ФИО': 250,
            'fio': 250,
            'возраст': 60,
            'должность': 200,
            'город': 150,
            'организация': 250,
            'room_id': 80,
            'room_capacity': 100,
            'Дата заезда': 100,
            'Дата отъезда': 100,
            'comment': 300,
            'email': 200,
            'телефон': 120
        }
        
        for i, col in enumerate(save_df.columns, start=1):
            width = column_widths.get(col, 120)
            worksheet.set_column(i, i, width)
        
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
        worksheet.update([result_df.columns.values.tolist()] + result_df.values.tolist())
        
        worksheet.freeze(rows=1)
        
        st.success(f"Детальные результаты сохранены на листе '{sheet_name}'")
        
    except Exception as e:
        st.error(f"Ошибка сохранения детальных результатов: {e}")
