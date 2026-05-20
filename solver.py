import pandas as pd
from collections import defaultdict

def solve_allocation(guests, rooms):
    """
    Простая функция расселения
    """
    print(f"DEBUG solve_allocation: гостей={len(guests)}, комнат={len(rooms)}")
    
    if not guests:
        return pd.DataFrame(), {}
    
    # Сортируем комнаты по вместимости
    rooms_sorted = sorted(rooms, key=lambda x: x.get('вместимость', 2))
    
    allocations = []
    room_index = 0
    
    for guest in guests:
        if room_index >= len(rooms_sorted):
            # Нет больше комнат
            allocations.append({
                'ФИО': guest.get('ФИО', ''),
                'room_id': 'нет мест',
                'room_capacity': 0,
                'comment': guest.get('comment', '')
            })
        else:
            room = rooms_sorted[room_index]
            allocations.append({
                'ФИО': guest.get('ФИО', ''),
                'room_id': room['room_id'],
                'room_capacity': room.get('вместимость', 2),
                'comment': guest.get('comment', '')
            })
            room_index += 1
    
    debug_info = {
        'total_guests': len(guests),
        'total_rooms': len(rooms),
        'allocated': len(allocations)
    }
    
    return pd.DataFrame(allocations), debug_info
