import pandas as pd
import re
from collections import defaultdict

class RoomAllocator:
    def __init__(self, rooms, guests):
        self.rooms = rooms
        self.guests = guests
        self.room_capacity = {r['room_id']: r['вместимость'] for r in rooms}
        
        # Список программного комитета
        self.program_committee = [
            "Козарь А.В.", "Калиш А.Н.", "Архипов Р.М.", "Балакший В.И.",
            "Белотелов В.И.", "Боголюбов А.Н.", "Бородачев Л.В.", "Бугай А.Н.",
            "Денисов В.И.", "Звездин А.К.", "Игнатьева Д.О.", "Короновский А.А.",
            "Котова С.П.", "Макаров В.А.", "Пирогов Ю.А.", "Пятаков А.П.",
            "Руденко О.В.", "Сазонов С.В.", "Сапожников О.А.", "Тимофеев И.В.",
            "Храмов А.Е.", "Цысарь С.А.", "Чашечкин Ю.Д.", "Черепенин В.А.",
            "Шандаров С.М."
        ]
        
        self.pc_normalized = [self._normalize_name(name) for name in self.program_committee]
        
        # Парсим комментарии
        self.guest_preferences = {}
        self.together_groups = []  # Группы, которые хотят жить вместе
        self.single_preferences = []  # Хотят жить одни
        self.room_preferences = {}  # Предпочтения по корпусам/этажам
        
        self._parse_comments()
        
        # Разделяем гостей
        self.pc_members = []
        self.regular_guests = []
        
        for guest in guests:
            guest_fio = guest.get('ФИО', guest.get('fio', ''))
            normalized_guest = self._normalize_name(guest_fio)
            
            is_pc = any(pc in normalized_guest or normalized_guest in pc for pc in self.pc_normalized)
            
            if is_pc:
                self.pc_members.append(guest)
            else:
                self.regular_guests.append(guest)
    
    def _normalize_name(self, name):
        if not name:
            return ""
        return str(name).lower().replace('.', '').replace(' ', '').replace('ё', 'е')
    
    def _extract_names_from_comment(self, text):
        """Извлекает имена из комментария"""
        names = []
        # Ищем русские имена (Фамилия И.О. или Фамилия Имя Отчество)
        patterns = [
            r'([А-Я][а-я]+(?:\s+[А-Я][а-я]+(?:\s+[А-Я][а-я]+)?))',  # Полное имя
            r'([А-Я][а-я]+(?:\s+[А-Я]\.(?:[А-Я]\.)?))',  # Фамилия И.О.
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                match = match.strip()
                if len(match) > 3 and match not in names:
                    names.append(match)
        return names
    
    def _parse_comments(self):
        """Парсит комментарии всех гостей"""
        together_map = defaultdict(list)
        single_rooms = set()
        
        for guest in self.guests:
            fio = guest.get('ФИО', guest.get('fio', ''))
            comment = str(guest.get('comment', '')).lower()
            
            self.guest_preferences[fio] = {
                'together': [],
                'single': False,
                'room_type': None,
                'building': None,
                'floor': None
            }
            
            # Проверка на одноместное размещение
            if 'без подселения' in comment or 'один' in comment or 'одноместный' in comment:
                single_rooms.add(fio)
                self.guest_preferences[fio]['single'] = True
            
            # Проверка на двухместное размещение
            if 'двухместный' in comment or 'вдвоем' in comment:
                self.guest_preferences[fio]['room_type'] = 2
            
            # Проверка на трехместное
            if 'трехместный' in comment or 'втроем' in comment:
                self.guest_preferences[fio]['room_type'] = 3
            
            # Проверка на корпус
            if 'красный' in comment or 'корпус №1' in comment:
                self.guest_preferences[fio]['building'] = '1'
            if 'желтый' in comment or 'корпус №2' in comment:
                self.guest_preferences[fio]['building'] = '2'
            
            # Проверка на этаж
            floor_match = re.search(r'(\d+)\s*этаж', comment)
            if floor_match:
                self.guest_preferences[fio]['floor'] = floor_match.group(1)
            
            # Извлекаем имена для совместного проживания
            names = self._extract_names_from_comment(comment)
            for name in names:
                if name != fio and len(name) > 3:
                    together_map[fio].append(name)
        
        # Формируем группы для совместного проживания
        processed = set()
        for guest, partners in together_map.items():
            if guest in processed:
                continue
            
            group = [guest]
            for partner in partners:
                if partner not in processed:
                    group.append(partner)
                    processed.add(partner)
            
            processed.add(guest)
            if len(group) > 1:
                # Определяем предпочтительный тип комнаты
                room_type = 2
                for g in group:
                    if self.guest_preferences.get(g, {}).get('room_type') == 3:
                        room_type = 3
                        break
                    elif self.guest_preferences.get(g, {}).get('room_type') == 2:
                        room_type = 2
                
                self.together_groups.append({
                    'guests': group,
                    'preferred_room_type': room_type,
                    'building': self._get_common_preference(group, 'building'),
                    'floor': self._get_common_preference(group, 'floor')
                })
        
        # Одинокие гости
        self.single_preferences = list(single_rooms)
    
    def _get_common_preference(self, group, key):
        """Получает общее предпочтение для группы"""
        values = [self.guest_preferences.get(g, {}).get(key) for g in group if self.guest_preferences.get(g, {}).get(key)]
        if values:
            from collections import Counter
            return Counter(values).most_common(1)[0][0]
        return None
    
    def _get_rooms_by_capacity(self, capacity, building=None):
        """Получает комнаты определенной вместимости, опционально в конкретном корпусе"""
        rooms = [r for r in self.rooms if r['вместимость'] == capacity]
        if building:
            rooms = [r for r in rooms if str(r['room_id']).startswith(building)]
        return rooms
    
    def allocate_groups(self):
        """Расселяет группы по комнатам"""
        allocations = []
        used_rooms = set()
        
        # Сортируем группы по размеру и предпочтениям
        self.together_groups.sort(key=lambda x: (-len(x['guests']), x['preferred_room_type']))
        
        for group in self.together_groups:
            group_size = len(group['guests'])
            preferred_type = group['preferred_room_type']
            building = group['building']
            
            # Выбираем комнату
            room = None
            for capacity in [preferred_type, group_size, 3, 2]:
                rooms_available = self._get_rooms_by_capacity(capacity, building)
                for r in rooms_available:
                    if r['room_id'] not in used_rooms:
                        room = r
                        break
                if room:
                    break
            
            if room:
                used_rooms.add(room['room_id'])
                for guest in group['guests']:
                    allocations.append({
                        'ФИО': guest,
                        'room_id': room['room_id'],
                        'room_capacity': room['вместимость'],
                        'comment': self.guest_preferences.get(guest, {}).get('comment', '')
                    })
            else:
                # Нет подходящей комнаты - временное размещение
                for guest in group['guests']:
                    allocations.append({
                        'ФИО': guest,
                        'room_id': 'требуется ручная обработка',
                        'room_capacity': 0,
                        'comment': self.guest_preferences.get(guest, {}).get('comment', '')
                    })
        
        return allocations, used_rooms
    
    def allocate_singles(self, used_rooms):
        """Расселяет гостей, желающих жить одних"""
        allocations = []
        single_rooms = self._get_rooms_by_capacity(1)
        
        for guest in self.single_preferences:
            # Ищем свободную одноместную комнату
            room = None
            for r in single_rooms:
                if r['room_id'] not in used_rooms:
                    room = r
                    break
            
            if room:
                used_rooms.add(room['room_id'])
                allocations.append({
                    'ФИО': guest,
                    'room_id': room['room_id'],
                    'room_capacity': 1,
                    'comment': self.guest_preferences.get(guest, {}).get('comment', '')
                })
            else:
                allocations.append({
                    'ФИО': guest,
                    'room_id': 'нет одноместных комнат',
                    'room_capacity': 0,
                    'comment': self.guest_preferences.get(guest, {}).get('comment', '')
                })
        
        return allocations
    
    def allocate_remaining(self, used_rooms):
        """Расселяет оставшихся гостей (члены ПК + обычные)"""
        allocations = []
        
        # Собираем всех оставшихся гостей
        remaining = []
        for guest in self.pc_members + self.regular_guests:
            fio = guest.get('ФИО', guest.get('fio', ''))
            if fio not in [a['ФИО'] for a in allocations]:
                if fio not in self.single_preferences:
                    if not any(fio in g['guests'] for g in self.together_groups):
                        remaining.append(guest)
        
        # Группируем по городу и возрасту
        city_groups = defaultdict(list)
        for guest in remaining:
            fio = guest.get('ФИО', guest.get('fio', ''))
            city = guest.get('город', 'не указан')
            age = guest.get('возраст', 0) or 0
            city_groups[city].append((fio, age, guest))
        
        # Получаем все доступные комнаты
        available_rooms = [r for r in self.rooms if r['room_id'] not in used_rooms]
        available_rooms.sort(key=lambda x: x['вместимость'])
        
        room_idx = 0
        
        for city, guests_list in city_groups.items():
            # Сортируем по возрасту
            guests_list.sort(key=lambda x: x[1])
            
            i = 0
            while i < len(guests_list):
                fio, age, guest = guests_list[i]
                
                if room_idx >= len(available_rooms):
                    # Нет комнат
                    allocations.append({
                        'ФИО': fio,
                        'room_id': 'нет мест',
                        'room_capacity': 0,
                        'comment': guest.get('comment', '')
                    })
                    i += 1
                    continue
                
                room = available_rooms[room_idx]
                room_capacity = room['вместимость']
                
                # Берем группу для этой комнаты
                group = [fio]
                group_guests = [guest]
                j = i + 1
                while len(group) < room_capacity and j < len(guests_list):
                    group.append(guests_list[j][0])
                    group_guests.append(guests_list[j][2])
                    j += 1
                
                # Заселяем группу
                for g_fio, g_guest in zip(group, group_guests):
                    allocations.append({
                        'ФИО': g_fio,
                        'room_id': room['room_id'],
                        'room_capacity': room_capacity,
                        'comment': g_guest.get('comment', '')
                    })
                
                room_idx += 1
                i = j
        
        return allocations
    
    def solve(self):
        """Основной метод расселения"""
        all_allocations = []
        
        # 1. Расселяем группы по комментариям
        group_allocations, used_rooms = self.allocate_groups()
        all_allocations.extend(group_allocations)
        
        # 2. Расселяем желающих жить одних
        single_allocations = self.allocate_singles(used_rooms)
        all_allocations.extend(single_allocations)
        
        # 3. Расселяем оставшихся
        remaining_allocations = self.allocate_remaining(used_rooms)
        all_allocations.extend(remaining_allocations)
        
        # Добавляем нерезидентов
        for guest in self.guests:
            fio = guest.get('ФИО', guest.get('fio', ''))
            if fio not in [a['ФИО'] for a in all_allocations]:
                all_allocations.append({
                    'ФИО': fio,
                    'room_id': 'не проживает',
                    'room_capacity': 0,
                    'comment': guest.get('comment', '')
                })
        
        return pd.DataFrame(all_allocations)
    
    def get_debug_info(self):
        """Отладочная информация"""
        return {
            'groups_count': len(self.together_groups),
            'groups': self.together_groups,
            'singles_count': len(self.single_preferences),
            'singles': self.single_preferences,
            'pc_members_count': len(self.pc_members),
            'regular_count': len(self.regular_guests)
        }


def solve_allocation(guests, rooms):
    """Основная функция расселения"""
    allocator = RoomAllocator(rooms, guests)
    result_df = allocator.solve()
    debug_info = allocator.get_debug_info()
    return result_df, debug_info
