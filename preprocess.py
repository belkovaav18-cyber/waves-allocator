import pandas as pd
import re
from datetime import datetime

def calculate_age(birth_date):
    """Рассчитать возраст из даты рождения"""
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
    """Извлечь город из данных регистрации"""
    city = registration_row.get('Город', '')
    if pd.isna(city) or city == "":
        return "не указан"
    city = str(city).strip()
    if ',' in city:
        city = city.split(',')[0]
    return city

def extract_position(registration_row):
    """Извлечь должность из данных регистрации"""
    position = registration_row.get('Должность', '')
    if pd.isna(position) or position == "":
        return "не указана"
    return str(position).strip()

def extract_gender(registration_row):
    """Извлечь пол из данных регистрации"""
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
    """Собрать ФИО из отдельных полей"""
    last_name = registration_row.get('Фамилия', '')
    first_name = registration_row.get('Имя', '')
    patronymic = registration_row.get('Отчество', '')
    
    parts = [p for p in [last_name, first_name, patronymic] if pd.notna(p) and p != ""]
    return " ".join(parts) if parts else ""

def normalize_fio(fio):
    """Нормализовать ФИО для сравнения"""
    if pd.isna(fio) or fio == "":
        return ""
    normalized = " ".join(str(fio).lower().split())
    parts = normalized.split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1]}"
    return normalized

def is_resident(guest_row):
    """Определяет, является ли гость резидентом"""
    # Проверяем колонку с тарифом
    tariff_col = None
    for col in guest_row.index:
        if 'Выбор тарифа за проживание' in str(col):
            tariff_col = col
            break
    
    if tariff_col is not None:
        tariff_value = guest_row.get(tariff_col, '')
        if pd.notna(tariff_value) and str(tariff_value).strip():
            tariff_str = str(tariff_value).lower()
            if 'не буду проживать' in tariff_str or 'не проживаю' in tariff_str or 'не нуждаюсь' in tariff_str:
                return False
    
    # Проверяем отметки в колонках с комнатами
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
    """Очищает DataFrame от проблемных типов данных"""
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == 'object':
            try:
                df[col] = df[col].fillna('').astype(str)
            except:
                pass
    return df

def preprocess_guests(raw_df, registration_df):
    """
    Объединяет данные из таблицы бронирования и регистрации
    """
    raw_df = clean_dataframe(raw_df)
    registration_df = clean_dataframe(registration_df)
    
    guests_df = raw_df.copy()
    
    # Создаем словарь для быстрого поиска по ФИО
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
    guests_df['email'] = ""
    guests_df['телефон'] = ""
    guests_df['ученая_степень'] = ""
    guests_df['ученое_звание'] = ""
    guests_df['организация'] = ""
    guests_df['resident'] = True
    
    for idx, guest_row in guests_df.iterrows():
        guest_fio = guest_row.get('ФИО', '')
        if pd.isna(guest_fio) or guest_fio == "":
            guests_df.loc[idx, 'resident'] = False
            continue
        
        is_res = is_resident(guest_row)
        guests_df.loc[idx, 'resident'] = is_res
        
        if not is_res:
            continue
        
        normalized_guest = normalize_fio(guest_fio)
        
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
            guests_df.loc[idx, 'ученая_степень'] = best_match.get('Ученая степень', '')
            guests_df.loc[idx, 'ученое_звание'] = best_match.get('Ученое звание', '')
            guests_df.loc[idx, 'организация'] = best_match.get('Полное название организации', '')
            
            del registration_dict[best_match_key]
    
    if 'Комментарий (например, пожелания по расселению)' in guests_df.columns:
        guests_df['comment'] = guests_df['Комментарий (например, пожелания по расселению)'].astype(str)
    else:
        guests_df['comment'] = ""
    
    if 'Выбор тарифа за проживание' in guests_df.columns:
        guests_df['tariff'] = guests_df['Выбор тарифа за проживание'].astype(str)
    else:
        guests_df['tariff'] = ""
    
    guests_df = guests_df.fillna("")
    
    return guests_df
