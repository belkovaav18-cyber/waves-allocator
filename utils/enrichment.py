import pandas as pd
from typing import Dict, Optional
import re
from datetime import datetime

def normalize_name(name: str) -> str:
    """Нормализует ФИО для сопоставления"""
    if pd.isna(name):
        return ""
    name = str(name).lower().strip()
    # Удаляем лишние пробелы
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def calculate_age(birth_date):
    """Рассчитывает возраст из даты рождения"""
    if pd.isna(birth_date):
        return None
    
    try:
        # Пробуем разные форматы даты
        if isinstance(birth_date, str):
            for fmt in ['%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y']:
                try:
                    birth_date = datetime.strptime(birth_date, fmt)
                    break
                except:
                    continue
            else:
                return None
        
        today = datetime.now()
        age = today.year - birth_date.year
        if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
            age -= 1
        return age
    except:
        return None

def extract_name_parts_from_booking(fio: str) -> Dict[str, str]:
    """Извлекает фамилию, имя, отчество из ФИО из бронирования"""
    fio = str(fio).strip()
    parts = fio.split()
    
    result = {
        'full_name': fio,
        'surname': '',
        'name': '',
        'patronymic': ''
    }
    
    if len(parts) >= 1:
        result['surname'] = parts[0]
    if len(parts) >= 2:
        result['name'] = parts[1]
    if len(parts) >= 3:
        result['patronymic'] = parts[2]
    
    return result

def extract_name_parts_from_registration(row) -> Dict[str, str]:
    """Извлекает ФИО из отдельных колонок регистрации"""
    surname = str(row.get('Фамилия', '')).strip()
    name = str(row.get('Имя', '')).strip()
    patronymic = str(row.get('Отчество', '')).strip()
    
    return {
        'full_name': f"{surname} {name} {patronymic}".strip(),
        'surname': surname,
        'name': name,
        'patronymic': patronymic
    }

def match_person(booking_name: str, registration_df: pd.DataFrame) -> Optional[Dict]:
    """
    Сопоставляет человека из бронирования с записью в регистрации
    по фамилии, имени и отчеству
    """
    if registration_df is None or registration_df.empty:
        return None
    
    booking_norm = normalize_name(booking_name)
    booking_parts = extract_name_parts_from_booking(booking_norm)
    
    if not booking_parts['surname']:
        return None
    
    best_match = None
    best_score = 0
    
    for idx, reg_row in registration_df.iterrows():
        reg_parts = extract_name_parts_from_registration(reg_row)
        
        if not reg_parts['surname']:
            continue
        
        # Вычисляем score совпадения
        score = 0
        
        # Фамилия (самый важный критерий)
        if booking_parts['surname'] == reg_parts['surname']:
            score += 50
        elif booking_parts['surname'] in reg_parts['surname'] or reg_parts['surname'] in booking_parts['surname']:
            score += 30
        
        # Имя
        if booking_parts['name'] and reg_parts['name']:
            if booking_parts['name'] == reg_parts['name']:
                score += 30
            elif booking_parts['name'][0] == reg_parts['name'][0]:
                score += 15
        
        # Отчество
        if booking_parts['patronymic'] and reg_parts['patronymic']:
            if booking_parts['patronymic'] == reg_parts['patronymic']:
                score += 20
            elif booking_parts['patronymic'][0] == reg_parts['patronymic'][0]:
                score += 10
        
        # Полное совпадение
        if booking_norm == normalize_name(reg_parts['full_name']):
            score = 100
            
        if score > best_score and score >= 50:  # Минимальный порог
            # Получаем возраст из даты рождения
            birth_date = reg_row.get('Дата рождения')
            age = calculate_age(birth_date)
            
            best_match = {
                'age': age,
                'position': reg_row.get('Должность', None),
                'city': reg_row.get('Город', None),
                'organization': reg_row.get('Полное название организации', None),
                'org_short': reg_row.get('Сокращенное название организации', None),
                'degree': reg_row.get('Ученая степень', None),
                'academic_rank': reg_row.get('Ученое звание', None),
                'phone': reg_row.get('Номер телефона для связи', None),
                'email': reg_row.get('Почта', None),
                'gender': reg_row.get('Пол', None),
                'match_score': score
            }
    
    return best_match

def enrich_booking_with_registration(booking_df: pd.DataFrame, registration_df: pd.DataFrame) -> pd.DataFrame:
    """
    Обогащает данные бронирования данными из регистрации
    """
    if registration_df is None or registration_df.empty:
        print("Нет данных регистрации")
        booking_df['age'] = None
        booking_df['position'] = None
        booking_df['city_from_reg'] = None
        booking_df['organization'] = None
        booking_df['degree'] = None
        booking_df['academic_rank'] = None
        booking_df['email'] = None
        booking_df['phone'] = None
        booking_df['gender_from_reg'] = None
        return booking_df
    
    registration_df = registration_df.copy()
    
    print(f"Загружено {len(registration_df)} записей из регистрации")
    
    # Обогащаем каждую запись
    ages = []
    positions = []
    cities = []
    organizations = []
    degrees = []
    academic_ranks = []
    emails = []
    phones = []
    genders = []
    
    matched_count = 0
    
    for idx, row in booking_df.iterrows():
        booking_fio = row.get('ФИО', '')
        if pd.isna(booking_fio) or booking_fio == '':
            ages.append(None)
            positions.append(None)
            cities.append(None)
            organizations.append(None)
            degrees.append(None)
            academic_ranks.append(None)
            emails.append(None)
            phones.append(None)
            genders.append(None)
            continue
        
        match = match_person(booking_fio, registration_df)
        
        if match:
            matched_count += 1
            ages.append(match['age'])
            positions.append(match['position'])
            cities.append(match['city'])
            organizations.append(match.get('organization'))
            degrees.append(match.get('degree'))
            academic_ranks.append(match.get('academic_rank'))
            emails.append(match.get('email'))
            phones.append(match.get('phone'))
            genders.append(match.get('gender'))
        else:
            ages.append(None)
            positions.append(None)
            cities.append(None)
            organizations.append(None)
            degrees.append(None)
            academic_ranks.append(None)
            emails.append(None)
            phones.append(None)
            genders.append(None)
    
    print(f"Сопоставлено {matched_count} из {len(booking_df)} записей")
    
    # Добавляем новые колонки
    booking_df['age'] = ages
    booking_df['position'] = positions
    booking_df['city_from_reg'] = cities
    booking_df['organization'] = organizations
    booking_df['degree'] = degrees
    booking_df['academic_rank'] = academic_ranks
    booking_df['email'] = emails
    booking_df['phone'] = phones
    booking_df['gender_from_reg'] = genders
    
    # Если в бронировании нет города, используем из регистрации
    if 'city' in booking_df.columns:
        booking_df['city'] = booking_df['city'].fillna(booking_df['city_from_reg'])
    else:
        booking_df['city'] = booking_df['city_from_reg']
    
    # Обновляем пол, если его нет в бронировании или он пустой
    if 'gender' in booking_df.columns:
        # Заполняем только пустые значения
        booking_df['gender'] = booking_df.apply(
            lambda row: row['gender_from_reg'] if pd.isna(row.get('gender')) or row.get('gender') == '' else row['gender'],
            axis=1
        )
    else:
        booking_df['gender'] = booking_df['gender_from_reg']
    
    # Удаляем временную колонку
    booking_df = booking_df.drop(columns=['gender_from_reg'])
    
    return booking_df
