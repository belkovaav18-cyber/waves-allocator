# utils/enrichment.py - улучшенная функция match_person

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


def match_person(booking_name: str, registration_df: pd.DataFrame) -> Optional[Dict]:
    """
    Улучшенное сопоставление человека из бронирования с записью в регистрации
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
        
        if score > best_score and score >= 40:  # Понизил порог до 40
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
