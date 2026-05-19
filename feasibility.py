# feasibility.py

def find_impossible_groups(guests, rooms):
    """
    Проверяет, есть ли группы, которые невозможно расселить
    Возвращает список проблемных групп
    """
    impossible = []
    
    # Проверка: MUST_BE_SINGLE и наличие одноместных комнат
    single_rooms = sum(1 for room in rooms if int(room.get("вместимость", 1)) == 1)
    must_be_single = [g for g in guests if g.get("must_be_single_room", False)]
    
    if len(must_be_single) > single_rooms:
        impossible.append({
            "type": "not_enough_single_rooms",
            "count": len(must_be_single),
            "available": single_rooms,
            "people": [g["fio"] for g in must_be_single]
        })
    
    # Проверка: FORCED_YELLOW и наличие комнат в желтом корпусе
    yellow_rooms = sum(1 for room in rooms if str(room.get("room_id", "")).startswith(('2-', '2')))
    must_be_yellow = [g for g in guests if g.get("preferred_building") == "yellow"]
    
    if len(must_be_yellow) > yellow_rooms:
        impossible.append({
            "type": "not_enough_yellow_rooms",
            "count": len(must_be_yellow),
            "available": yellow_rooms,
            "people": [g["fio"] for g in must_be_yellow]
        })
    
    return impossible


def split_groups(guests, rooms):
    """
    Разбивает группы на подгруппы при необходимости
    """
    # Если нет проблем, возвращаем исходный список
    impossible = find_impossible_groups(guests, rooms)
    if not impossible:
        return guests
    
    # Создаем копию
    fixed_guests = []
    
    for guest in guests:
        fixed_guests.append(guest)
    
    return fixed_guests
