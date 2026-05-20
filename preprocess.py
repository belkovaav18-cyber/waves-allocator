import pandas as pd
import re
from datetime import datetime

def calculate_age(birth_date):
    if pd.isna(birth_date) or birth_date == "":
        return None
    try:
        if isinstance(birth_date, str):
            for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d']:
                try:
                    birth_date = datetime.strptime(birth_date, fmt)
                    break
                except:
                    continue
            if isinstance(birth_date, str):
                return None
        today = datetime(2026, 5, 31)
        age = today.year - birth_date.year
        if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
            age -= 1
        return age
    except:
        return None

def extract_city(registration_row):
    city = registration_row.get('Город', '')
    if pd.isna(city) or city == "":
        return "не указан"
    city = str(city).strip()
    if ',' in city:
        city = city.split(',')[0]
    return city

def extract_position(registration_row):
    position = registration_row.get('Должность', '')
    if pd.isna(position) or position == "":
        return "не указана"
    return str(position).strip()

def extract_gender(registration_row):
    gender = registration_row.get('Пол', '')
    if pd.isna(gender) or gender == "":
        return "не указан"
    gender = str(gender).strip().upper()
    if gender in ['М', 'МУЖ', 'МУЖСКОЙ', 'M', 'MALE']:
        return 'М'
    elif gender in ['Ж', 'ЖЕН', 'ЖЕНСКИЙ', 'F', 'FEMALE']:
        return 'Ж'
    return "не указан"

def extract_full_name(registration_row):
    last_name = registration_row.get('Фамилия', '')
    first_name = registration_row.get('Имя', '')
    patronymic = registration_row.get('Отчество', '')
    parts = [p for p in [last_name, first_name, patronymic] if pd.notna(p) and p != ""]
    return " ".join(parts) if parts else ""

def normalize_fio(fio):
    if pd.isna(fio) or fio == "":
        return ""
    normalized = " ".join(str(fio).lower().split())
    parts = normalized.split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1]}"
    return normalized

def extract_tariff(guest_row):
    """Извлечь тариф из колонки Выбор тарифа за проживание"""
    for col in guest_row.index:
        if 'Выбор тарифа за проживание' in str(col):
            val = guest_row.get(col, '')
            if pd.notna(val) and str(val).strip():
                val_str = str(val).strip().lower()
                if '5000' in val_str:
                    return 5000
                elif '6100' in val_str:
                    return 6100
                elif '3782' in val_str:
                    return 3782
                elif '3100' in val_str:
                    return 3100
                elif 'не буду' in val_str:
                    return 0
    return None

def is_resident(guest_row):
    # Проверяем тариф
    tariff = extract_tariff(guest_row)
    if tariff == 0:
        return False
    
    # Проверяем отметки комнат
    for col in guest_row.index:
        col_str = str(col)
        if 'Комната' in col_str and 'ночь' in col_str:
            value = guest_row.get(col, '')
            if pd.notna(value) and str(value).strip():
                val_str = str(value).strip().lower()
                if val_str not in ['', 'нет', '-', 'false', 'nan', 'не буду проживать']:
                    return True
    return False

def clean_dataframe(df):
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == 'object':
            try:
                df[col] = df[col].fillna('').astype(str)
            except:
                pass
    return df

def preprocess_guests(raw_df, registration_df):
    raw_df = clean_dataframe(raw_df)
    registration_df = clean_dataframe(registration_df)
    
    guests_df = raw_df.copy()
    
    # Словарь регистрации
    registration_dict = {}
    for _, reg_row in registration_df.iterrows():
        full_name = extract_full_name(reg_row)
        if full_name:
            normalized = normalize_fio(full_name)
            registration_dict[normalized] = reg_row
    
    # Добавляем колонки
    guests_df['возраст'] = None
    guests_df['город'] = "не указан"
    guests_df['должность'] = "не указана"
    guests_df['пол'] = "не указан"
    guests_df['тариф'] = None
    guests_df['email'] = ""
    guests_df['телефон'] = ""
    guests_df['организация'] = ""
    guests_df['resident'] = True
    
    for idx, guest_row in guests_df.iterrows():
        guest_fio = guest_row.get('ФИО', '')
        if pd.isna(guest_fio) or guest_fio == "":
            guests_df.loc[idx, 'resident'] = False
            continue
        
        # Определяем тариф
        tariff = extract_tariff(guest_row)
        guests_df.loc[idx, 'тариф'] = tariff
        
        # Определяем резидента
        is_res = is_resident(guest_row)
        guests_df.loc[idx, 'resident'] = is_res
        
        if not is_res:
            continue
        
        normalized_guest = normalize_fio(guest_fio)
        
        # Ищем в регистрации
        best_match = None
        best_match_key = None
        
        for reg_key, reg_row in registration_dict.items():
            guest_parts = normalized_guest.split()
            reg_parts = reg_key.split()
            if len(guest_parts) >= 2 and len(reg_parts) >= 2:
                if guest_parts[0] == reg_parts[0] and guest_parts[1] == reg_parts[1]:
                    best_match = reg_row
                    best_match_key = reg_key
                    break
        
        if best_match is not None:
            birth_date = best_match.get('Дата рождения')
            age = calculate_age(birth_date)
            city = extract_city(best_match)
            position = extract_position(best_match)
            gender = extract_gender(best_match)
            
            guests_df.loc[idx, 'возраст'] = age
            guests_df.loc[idx, 'город'] = city
            guests_df.loc[idx, 'должность'] = position
            guests_df.loc[idx, 'пол'] = gender
            guests_df.loc[idx, 'email'] = best_match.get('Почта', '')
            guests_df.loc[idx, 'телефон'] = best_match.get('Номер телефона для связи', '')
            guests_df.loc[idx, 'организация'] = best_match.get('Полное название организации', '')
            
            del registration_dict[best_match_key]
    
    # Комментарий
    if 'Комментарий (например, пожелания по расселению)' in guests_df.columns:
        guests_df['comment'] = guests_df['Комментарий (например, пожелания по расселению)'].astype(str)
    else:
        guests_df['comment'] = ""
    
    guests_df = guests_df.fillna("")
    
    return guests_df
