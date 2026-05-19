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
    # Удаляем точки
    name = name.replace('.', '')
    # Заменяем ё на е
    name = name.replace('ё', 'е')
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


def match_person(booking_name: str, registration_df: pd.DataFrame) -> Optional[Dict]:
    """
    Сопоставляет человека из бронирования с записью в регистрации
    """
    if registration_df is None or registration_df.empty:
        return None
    
    booking_norm = normalize_name(booking_name)
    booking_parts = booking_norm.split()
    
    if len(booking_parts) < 2:
        return None
    
    booking_surname = booking_parts[0]
    booking_name_first = booking_parts[1] if len(booking_parts) > 1 else ""
    booking_patronymic = booking_parts[2] if len(booking_parts) > 2 else ""
    
    best_match = None
    best_score = 0
    
    for idx, reg_row in registration_df.iterrows():
        surname = str(reg_row.get('Фамилия', '')).lower().strip()
        name = str(reg_row.get('Имя', '')).lower().strip()
        patronymic = str(reg_row.get('Отчество', '')).lower().strip()
        
        if not surname:
            continue
        
        # Нормализуем
        surname = surname.replace('.', '').replace('ё', 'е')
        name = name.replace('.', '').replace('ё', 'е')
        patronymic = patronymic.replace('.', '').replace('ё', 'е')
        
        # Вычисляем score
        score = 0
        
        # Фамилия должна совпадать полностью или почти полностью
        if booking_surname == surname:
            score += 50
        elif booking_surname in surname or surname in booking_surname:
            score += 30
        else:
            continue  # Фамилия не совпадает - пропускаем
        
        # Имя
        if booking_name_first and name:
            if booking_name_first == name:
                score += 30
            elif booking_name_first[0] == name[0]:
                score += 15
            elif booking_name_first in name or name in booking_name_first:
                score += 10
        
        # Отчество (если есть)
        if booking_patronymic and patronymic:
            if booking_patronymic == patronymic:
                score += 20
            elif booking_patronymic[0] == patronymic[0]:
                score += 10
        
        # Проверка: имя из бронирования может быть полным, а в регистрации только первая буква
        if booking_name_first and name and len(name) == 1 and booking_name_first[0] == name[0]:
            score += 15
        
        if score > best_score and score >= 40:  # Порог 40
            birth_date = reg_row.get('Дата рождения')
            age = calculate_age(birth_date)
            
            best_match = {
                'age': age,
                'position': reg_row.get('Должность', None),
                'city': reg_row.get('Город', None),
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
        return booking_df
    
    registration_df = registration_df.copy()
    
    print(f"Загружено {len(registration_df)} записей из регистрации")
    
    # Обогащаем каждую запись
    ages = []
    positions = []
    cities = []
    genders = []
    
    matched_count = 0
    
    for idx, row in booking_df.iterrows():
        booking_fio = row.get('fio', row.get('ФИО', ''))
        if pd.isna(booking_fio) or booking_fio == '':
            ages.append(None)
            positions.append(None)
            cities.append(None)
            genders.append(None)
            continue
        
        match = match_person(booking_fio, registration_df)
        
        if match:
            matched_count += 1
            ages.append(match.get('age'))
            positions.append(match.get('position'))
            cities.append(match.get('city'))
            genders.append(match.get('gender'))
        else:
            ages.append(None)
            positions.append(None)
            cities.append(None)
            genders.append(None)
    
    print(f"Сопоставлено {matched_count} из {len(booking_df)} записей")
    
    # Добавляем новые колонки
    booking_df['age'] = ages
    booking_df['position'] = positions
    booking_df['city_from_reg'] = cities
    booking_df['gender_from_reg'] = genders
    
    # Если в бронировании нет города, используем из регистрации
    if 'city' in booking_df.columns:
        booking_df['city'] = booking_df['city'].fillna(booking_df['city_from_reg'])
    else:
        booking_df['city'] = booking_df['city_from_reg']
    
    # Обновляем пол, если его нет в бронировании или он пустой
    if 'gender' in booking_df.columns:
        booking_df['gender'] = booking_df.apply(
            lambda row: row['gender_from_reg'] if pd.isna(row.get('gender')) or row.get('gender') == '' else row['gender'],
            axis=1
        )
    else:
        booking_df['gender'] = booking_df['gender_from_reg']
    
    # Удаляем временную колонку
    if 'gender_from_reg' in booking_df.columns:
        booking_df = booking_df.drop(columns=['gender_from_reg'])
    
    return booking_df
