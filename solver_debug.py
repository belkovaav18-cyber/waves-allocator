# Отладочный модуль для солвера
import pandas as pd

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
            'fio': guest.get('ФИО', ''),
            'age': guest.get('возраст'),
            'city': guest.get('город'),
            'comment': guest.get('comment_text', '')
        })
    
    # Информация о гостях с комментариями
    for guest in allocator.comment_guests:
        debug_info['comment_guests'].append({
            'fio': guest.get('ФИО', ''),
            'age': guest.get('возраст'),
            'city': guest.get('город'),
            'comment': guest.get('comment_text', '')
        })
    
    # Информация об обычных гостях
    for guest in allocator.regular_guests:
        debug_info['regular_guests'].append({
            'fio': guest.get('ФИО', ''),
            'age': guest.get('возраст'),
            'city': guest.get('город')
        })
    
    # Информация об использовании комнат
    if hasattr(allocator, 'room_capacity'):
        debug_info['total_rooms'] = len(allocator.rooms)
        debug_info['single_rooms'] = len([r for r in allocator.rooms if r.get('вместимость') == 1])
        debug_info['double_rooms'] = len([r for r in allocator.rooms if r.get('вместимость') == 2])
    
    return debug_info

def validate_allocation(result_df, rooms_df):
    """Проверка корректности расселения"""
    
    errors = []
    warnings = []
    
    if result_df.empty:
        errors.append("Результат расселения пуст")
        return errors, warnings
    
    # Проверяем наличие необходимых колонок
    if 'room_id' not in result_df.columns:
        errors.append("В результате отсутствует колонка 'room_id'")
        return errors, warnings
    
    if 'fio' not in result_df.columns:
        errors.append("В результате отсутствует колонка 'fio'")
        return errors, warnings
    
    # Создаем словарь вместимости комнат
    if rooms_df is not None and not rooms_df.empty:
        room_capacity = {str(r['room_id']): r['вместимость'] for _, r in rooms_df.iterrows()}
        
        # Проверяем переполнение комнат
        room_occupants = {}
        for _, row in result_df.iterrows():
            room_id = str(row.get('room_id', ''))
            fio = row.get('fio', '')
            if room_id and room_id not in ['не проживает', 'нет мест', 'требуется ручная обработка', 'nan', 'None']:
                if room_id not in room_occupants:
                    room_occupants[room_id] = []
                if fio and fio != 'nan':
                    room_occupants[room_id].append(fio)
        
        for room_id, occupants in room_occupants.items():
            capacity = room_capacity.get(room_id, 2)
            if len(occupants) > capacity:
                errors.append(f"Комната {room_id} переполнена: {len(occupants)}/{capacity}")
            elif len(occupants) < capacity and len(occupants) > 0:
                warnings.append(f"Комната {room_id} не полностью заполнена: {len(occupants)}/{capacity}")
    
    return errors, warnings

def solve_simple(guests, rooms):
    """Упрощенная версия солвера для тестирования"""
    from solver import RoomAllocator
    
    allocator = RoomAllocator(rooms, guests)
    result_df = allocator.solve()
    debug_info = debug_allocation(allocator)
    
    return result_df, debug_info
