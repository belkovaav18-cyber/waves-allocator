import pandas as pd
from solver import solve_allocation

def smart_solve(guests, rooms):
    """
    Умное расселение с обработкой всех правил
    
    Args:
        guests: список гостей (словари)
        rooms: список комнат (словари)
    
    Returns:
        result_df: DataFrame с результатами расселения
        debug_info: словарь с отладочной информацией
    """
    
    # Проверяем входные данные
    if not guests:
        return pd.DataFrame({'error': ['Нет гостей для расселения']}), {}
    
    if not rooms:
        return pd.DataFrame({'error': ['Нет комнат для расселения']}), {}
    
    # Создаем копии для работы
    guests_list = guests.copy() if isinstance(guests, list) else guests.to_dict('records')
    rooms_list = rooms.copy() if isinstance(rooms, list) else rooms.to_dict('records')
    
    # Запускаем алгоритм расселения
    try:
        result_df, debug_info = solve_allocation(guests_list, rooms_list)
        
        # Добавляем дополнительную информацию
        if 'comment' in result_df.columns:
            # Отмечаем гостей с комментариями
            result_df['has_comment'] = result_df['comment'].apply(
                lambda x: bool(x and str(x).strip() and str(x).strip() != 'nan')
            )
        
        # Добавляем информацию о членах программного комитета
        program_committee_names = [
            "Козарь А.В.", "Калиш А.Н.", "Архипов Р.М.", "Балакший В.И.",
            "Белотелов В.И.", "Боголюбов А.Н.", "Бородачев Л.В.", "Бугай А.Н.",
            "Денисов В.И.", "Звездин А.К.", "Игнатьева Д.О.", "Короновский А.А.",
            "Котова С.П.", "Макаров В.А.", "Пирогов Ю.А.", "Пятаков А.П.",
            "Руденко О.В.", "Сазонов С.В.", "Сапожников О.А.", "Тимофеев И.В.",
            "Храмов А.Е.", "Цысарь С.А.", "Чашечкин Ю.Д.", "Черепенин В.А.",
            "Шандаров С.М."
        ]
        
        def is_pc_member(fio):
            if pd.isna(fio):
                return False
            fio_str = str(fio).lower().replace('.', '').replace(' ', '')
            for pc_name in program_committee_names:
                pc_normalized = pc_name.lower().replace('.', '').replace(' ', '')
                if pc_normalized in fio_str or fio_str in pc_normalized:
                    return True
            return False
        
        # Используем правильное название колонки - 'ФИО'
        if 'ФИО' in result_df.columns:
            result_df['is_program_committee'] = result_df['ФИО'].apply(is_pc_member)
        elif 'fio' in result_df.columns:
            result_df['is_program_committee'] = result_df['fio'].apply(is_pc_member)
        
        return result_df, debug_info
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return pd.DataFrame({'error': [str(e)]}), {}

def optimize_allocation(result_df, rooms_df):
    """
    Оптимизация расселения после первоначального распределения
    """
    # Создаем словарь занятости комнат
    room_occupancy = {}
    for _, row in result_df.iterrows():
        room_id = row.get('room_id')
        if room_id and room_id != 'не проживает' and room_id != 'нет мест' and room_id != 'требуется ручная обработка':
            if room_id not in room_occupancy:
                room_occupancy[room_id] = []
            # Используем правильное название колонки
            fio = row.get('ФИО', row.get('fio', ''))
            if fio:
                room_occupancy[room_id].append(fio)
    
    # Создаем словарь вместимости комнат
    room_capacity = {r['room_id']: r['вместимость'] for r in rooms_df.to_dict('records')}
    
    # Ищем возможности для оптимизации
    optimizations = []
    
    for room_id, occupants in room_occupancy.items():
        capacity = room_capacity.get(room_id, 2)
        
        # Если комната заполнена не полностью
        if len(occupants) < capacity:
            # Ищем гостей, которых можно сюда добавить
            for _, row in result_df.iterrows():
                other_room = row.get('room_id')
                if other_room and other_room != room_id and other_room != 'не проживает':
                    # Проверяем, можно ли переместить
                    other_occupants = room_occupancy.get(other_room, [])
                    if len(other_occupants) > 1:
                        fio = row.get('ФИО', row.get('fio', ''))
                        optimizations.append({
                            'guest': fio,
                            'from_room': other_room,
                            'to_room': room_id,
                            'reason': f'Оптимизация заполнения комнаты {room_id}'
                        })
    
    return optimizations
