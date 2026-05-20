# Отладочный модуль для солвера

def debug_allocation(allocator):
    """Отладка процесса расселения"""
    
    debug_info = {
        'pc_members': [],
        'comment_guests': [],
        'regular_guests': [],
        'room_usage': {}
    }
    
    # Информация о членах ПК
    for guest in allocator.pc_members:
        debug_info['pc_members'].append({
            'fio': guest['ФИО'],
            'age': guest.get('возраст'),
            'city': guest.get('город'),
            'comment': guest.get('comment_text', '')
        })
    
    # Информация о гостях с комментариями
    for guest in allocator.comment_guests:
        debug_info['comment_guests'].append({
            'fio': guest['ФИО'],
            'age': guest.get('возраст'),
            'city': guest.get('город'),
            'comment': guest.get('comment_text', '')
        })
    
    # Информация об обычных гостях
    for guest in allocator.regular_guests:
        debug_info['regular_guests'].append({
            'fio': guest['ФИО'],
            'age': guest.get('возраст'),
            'city': guest.get('город')
        })
    
    return debug_info

def validate_allocation(result_df, rooms_df):
    """Проверка корректности расселения"""
    
    errors = []
    warnings = []
    
    # Создаем словарь вместимости комнат
    room_capacity = {r['room_id']: r['вместимость'] for _, r in rooms_df.iterrows()}
    
    # Проверяем переполнение комнат
    room_occupants = {}
    for _, row in result_df.iterrows():
        room_id = row.get('room_id')
        if room_id and room_id not in ['не проживает', 'нет мест', 'требуется ручная обработка']:
            if room_id not in room_occupants:
                room_occupants[room_id] = []
            room_occupants[room_id].append(row['fio'])
    
    for room_id, occupants in room_occupants.items():
        capacity = room_capacity.get(room_id, 2)
        if len(occupants) > capacity:
            errors.append(f"Комната {room_id} переполнена: {len(occupants)}/{capacity}")
        elif len(occupants) < capacity:
            warnings.append(f"Комната {room_id} не полностью заполнена: {len(occupants)}/{capacity}")
    
    return errors, warnings
