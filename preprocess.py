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
    # Убираем все лишнее, оставляем только фамилию и имя
    fio = str(fio).lower()
    # Убираем скобки и содержимое в скобках
    fio = re.sub(r'\([^)]*\)', '', fio)
    # Убираем знаки препинания
    fio = re.sub(r'[^\w\s]', '', fio)
    # Убираем лишние пробелы
    fio = " ".join(fio.split())
    # Берем только первые два слова (фамилия и имя)
    parts = fio.split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1]}"
    return fio

def extract_surname(fio):
    """Извлекает только фамилию"""
    if pd.isna(fio) or fio == "":
        return ""
    fio = str(fio).lower()
    fio = re.sub(r'\([^)]*\)', '', fio)
    fio = re.sub(r'[^\w\s]', '', fio)
    parts = fio.split()
    return parts[0] if parts else ""

def extract_tariff(guest_row):
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
    tariff = extract_tariff(guest_row)
    if tariff == 0:
        return False
    for col in guest_row.index:
        col_str = str(col)
        if 'Комната' in col_str and 'ночь' in col_str:
            value = guest_row.get(col, '')
            if pd.notna(value) and str(value).strip():
                val_str = str(value).strip().lower()
                if val_str not in ['', 'нет', '-', 'false', 'nan', 'не буду проживать']:
                    return True
    return False

def calculate_nights(guest_row):
    nights = 0
    for col in guest_row.index:
        col_str = str(col)
        if 'Комната' in col_str and 'ночь' in col_str:
            value = guest_row.get(col, '')
            if pd.notna(value) and str(value).strip():
                val_str = str(value).strip().lower()
                if val_str not in ['', 'нет', '-', 'false', 'nan', 'не буду проживать']:
                    nights += 1
    return nights

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
    
    # Создаем словарь для быстрого поиска по фамилии и по ФИО
    registration_by_surname = {}
    registration_by_fullname = {}
    
    for _, reg_row in registration_df.iterrows():
        full_name = extract_full_name(reg_row)
        if full_name:
            normalized_full = normalize_fio(full_name)
            surname = extract_surname(full_name)
            registration_by_fullname[normalized_full] = reg_row
            if surname not in registration_by_surname:
                registration_by_surname[surname] = []
            registration_by_surname[surname].append((normalized_full, reg_row))
    
    # Добавляем колонки
    guests_df['возраст'] = None
    guests_df['город'] = "не указан"
    guests_df['должность'] = "не указана"
    guests_df['пол'] = "не указан"
    guests_df['тариф'] = None
    guests_df['число_ночей'] = 0
    guests_df['стоимость'] = 0
    guests_df['email'] = ""
    guests_df['телефон'] = ""
    guests_df['организация'] = ""
    guests_df['resident'] = True
    
    for idx, guest_row in guests_df.iterrows():
        guest_fio = guest_row.get('ФИО', '')
        if pd.isna(guest_fio) or guest_fio == "":
            guests_df.loc[idx, 'resident'] = False
            continue
        
        # Тариф и ночи
        tariff = extract_tariff(guest_row)
        nights = calculate_nights(guest_row)
        guests_df.loc[idx, 'тариф'] = tariff
        guests_df.loc[idx, 'число_ночей'] = nights
        if tariff and nights:
            guests_df.loc[idx, 'стоимость'] = tariff * nights
        
        # Резидент
        is_res = is_resident(guest_row)
        guests_df.loc[idx, 'resident'] = is_res
        
        if not is_res:
            continue
        
        normalized_guest = normalize_fio(guest_fio)
        guest_surname = extract_surname(guest_fio)
        
        best_match = None
        
        # 1. Пробуем точное совпадение по нормализованному ФИО
        if normalized_guest in registration_by_fullname:
            best_match = registration_by_fullname[normalized_guest]
        else:
            # 2. Пробуем поиск по фамилии
            if guest_surname in registration_by_surname:
                for reg_full, reg_row in registration_by_surname[guest_surname]:
                    # Проверяем, что имя начинается с той же буквы
                    guest_name_parts = normalized_guest.split()
                    reg_name_parts = reg_full.split()
                    if len(guest_name_parts) >= 2 and len(reg_name_parts) >= 2:
                        if guest_name_parts[0] == reg_name_parts[0]:
                            # Фамилии совпадают, проверяем инициалы имени
                            guest_init = guest_name_parts[1][0] if len(guest_name_parts[1]) > 0 else ''
                            reg_init = reg_name_parts[1][0] if len(reg_name_parts[1]) > 0 else ''
                            if guest_init == reg_init:
                                best_match = reg_row
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
    
    # Комментарий
    if 'Комментарий (например, пожелания по расселению)' in guests_df.columns:
        guests_df['comment'] = guests_df['Комментарий (например, пожелания по расселению)'].astype(str)
    else:
        guests_df['comment'] = ""
    
    guests_df = guests_df.fillna("")
    
    return guests_df
