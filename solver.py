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
        self.guest_info = {}  # Информация о каждом госте
        self.together_groups = []  # Группы для совместного проживания
        self.single_requests = []  # Запросы на одноместное размещение
        self.building_requests = {}  # Запросы на конкретный корпус
        self.special_rooms = {}  # Особые комнаты (двуспальные и т.д.)
        
        self._parse_all_comments()
        
        # Разделяем гостей на категории
        self.pc_members = []
        self.regular_guests = []
        
        for guest in guests:
            fio = guest.get('ФИО', guest.get('fio', ''))
            if not fio:
                continue
                
            normalized = self._normalize_name(fio)
            is_pc = any(pc in normalized or normalized in pc for pc in self.pc_normalized)
            
            if is_pc:
                self.pc_members.append(guest)
            else:
                self.regular_guests.append(guest)
    
    def _normalize_name(self, name):
        if not name:
            return ""
        name = str(name).lower()
        name = re.sub(r'[^\w\s]', '', name)  # Убираем знаки препинания
        name = name.replace(' ', '').replace('ё', 'е')
        return name
    
    def _extract_names_from_comment(self, text):
        """Извлекает имена из комментария"""
        if not text:
            return []
        
        names = []
        # Паттерны для поиска русских имен
        patterns = [
            r'([А-Я][а-я]+(?:\s+[А-Я][а-я]+(?:\s+[А-Я][а-я]+)?))',  # Полное имя
            r'([А-Я][а-я]+(?:\s+[А-Я]\.(?:[А-Я]\.)?))',  # Фамилия и инициалы
            r'с\s+([А-Я][а-я]+(?:\s+[А-Я][а-я]+)?)',  # "с Ивановым"
            r'вместе\s+с\s+([А-Я][а-я]+(?:\s+[А-Я][а-я]+)?)',  # "вместе с Петровым"
            r'подселить\s+к\s+([А-Я][а-я]+(?:\s+[А-Я][а-я]+)?)',  # "подселить к Сидорову"
            r'совместно\s+с\s+([А-Я][а-я]+(?:\s+[А-Я][а-я]+)?)',  # "совместно с Ивановым"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                match = match.strip()
                if len(match) > 3 and match.lower() not in [n.lower() for n in names]:
                    names.append(match)
        
        return names
    
    def _parse_all_comments(self):
        """Парсит комментарии всех гостей"""
        together_map = defaultdict(set)
        
        for guest in self.guests:
            fio = guest.get('ФИО', guest.get('fio', ''))
            comment = str(guest.get('comment', '')).lower()
            
            # Сохраняем оригинальную информацию
            self.guest_info[fio] = {
                'comment': comment,
                'age': guest.get('возраст', 0),
                'city': guest.get('город', 'не указан'),
                'position': guest.get('должность', ''),
                'fio': fio
            }
            
            # Проверка на одноместное размещение
            if any(word in comment for word in ['без подселения', 'один', 'одноместный', 'не подселять']):
                self.single_requests.append(fio)
            
            # Проверка на двухместное размещение
            if 'двухместный' in comment or 'вдвоем' in comment:
                self.guest_info[fio]['preferred_capacity'] = 2
            
            # Проверка на трехместное
            if 'трехместный' in comment or 'втроем' in comment:
                self.guest_info[fio]['preferred_capacity'] = 3
            
            # Проверка на корпус
            if 'красный' in comment or 'корпус №1' in comment or 'корпус 1' in comment:
                self.building_requests[fio] = '1'
            if 'желтый' in comment or 'корпус №2' in comment or 'корпус 2' in comment:
                self.building_requests[fio] = '2'
            
            # Извлекаем имена для совместного проживания
            extracted_names = self._extract_names_from_comment(comment)
            for name in extracted_names:
                if name.lower() not in fio.lower():
                    together_map[fio].add(name)
        
        # Формируем группы для совместного проживания
        processed = set()
        
        for fio, partners in together_map.items():
            if fio in processed:
                continue
            
            # Собираем полную группу
            group = set([fio])
            to_process = list(partners)
            
            while to_process:
                partner = to_process.pop()
                if partner not in processed:
                    group.add(partner)
                    # Добавляем партнеров этого партнера
                    for p in together_map.get(partner, []):
                        if p not in group:
                            to_process.append(p)
            
            if len(group) > 1:
                # Определяем предпочтительный тип комнаты
                preferred_capacity = 2
                for g in group:
                    if self.guest_info.get(g, {}).get('preferred_capacity') == 3:
                        preferred_capacity = 3
                        break
                    elif self.guest_info.get(g, {}).get('preferred_capacity') == 2:
                        preferred_capacity = 2
                
                # Определяем предпочтительный корпус
                building = None
                for g in group:
                    if g in self.building_requests:
                        building = self.building_requests[g]
                        break
                
                self.together_groups.append({
                    'guests': list(group),
                    'size': len(group),
                    'preferred_capacity': preferred_capacity,
                    'building': building
                })
                
                for g in group:
                    processed.add(g)
        
        # Убираем из single_requests тех, кто уже в группах
        grouped_guests = set()
        for group in self.together_groups:
            grouped_guests.update(group['guests'])
        self.single_requests = [s for s in self.single_requests if s not in grouped_guests]
    
    def _get_rooms_by_capacity(self, capacity, building=None, exclude_rooms=None):
        """Получает комнаты определенной вместимости"""
        rooms = [r for r in self.rooms if r['вместимость'] == capacity]
        if building:
            rooms = [r for r in rooms if str(r['room_id']).startswith(building)]
        if exclude_rooms:
            rooms = [r for r in rooms if r['room_id'] not in exclude_rooms]
        return rooms
    
    def allocate_groups(self, used_rooms):
        """Расселяет группы по комнатам"""
        allocations = []
        
        # Сортируем группы: сначала большие, потом с предпочтениями
        self.together_groups.sort(key=lambda x: (-x['size'], -x['preferred_capacity']))
        
        for group in self.together_groups:
            group_size = len(group['guests'])
            preferred = group['preferred_capacity']
            building = group.get('building')
            
            # Ищем комнату
            room = None
            
            # Сначала ищем комнату нужной вместимости
            for capacity in [preferred, group_size, 3, 2]:
                rooms_available = self._get_rooms_by_capacity(capacity, building, used_rooms)
                if rooms_available:
                    room = rooms_available[0]
                    break
            
            if room:
                used_rooms.add(room['room_id'])
                for guest in group['guests']:
                    allocations.append({
                        'ФИО': guest,
                        'room_id': room['room_id'],
                        'room_capacity': room['вместимость'],
                        'comment': self.guest_info.get(guest, {}).get('comment', '')
                    })
            else:
                # Нет подходящей комнаты
                for guest in group['guests']:
                    allocations.append({
                        'ФИО': guest,
                        'room_id': 'требуется ручная обработка',
                        'room_capacity': 0,
                        'comment': self.guest_info.get(guest, {}).get('comment', '')
                    })
        
        return allocations
    
    def allocate_singles(self, used_rooms):
        """Расселяет желающих жить одних"""
        allocations = []
        single_rooms = self._get_rooms_by_capacity(1, exclude_rooms=used_rooms)
        
        for guest in self.single_requests:
            if guest in [a['ФИО'] for a in allocations]:
                continue
                
            if single_rooms:
                room = single_rooms.pop(0)
                used_rooms.add(room['room_id'])
                allocations.append({
                    'ФИО': guest,
                    'room_id': room['room_id'],
                    'room_capacity': 1,
                    'comment': self.guest_info.get(guest, {}).get('comment', '')
                })
            else:
                allocations.append({
                    'ФИО': guest,
                    'room_id': 'нет одноместных комнат',
                    'room_capacity': 0,
                    'comment': self.guest_info.get(guest, {}).get('comment', '')
                })
        
        return allocations
    
    def allocate_remaining(self, used_rooms):
        """Расселяет оставшихся гостей"""
        allocations = []
        
        # Собираем всех еще не расселенных гостей
        allocated_fios = set([a['ФИО'] for a in allocations])
        remaining = []
        
        for guest in self.pc_members + self.regular_guests:
            fio = guest.get('ФИО', guest.get('fio', ''))
            if fio and fio not in allocated_fios:
                if fio not in self.single_requests:
                    if not any(fio in g['guests'] for g in self.together_groups):
                        remaining.append(guest)
        
        # Группируем по городам и возрасту
        city_groups = defaultdict(list)
        for guest in remaining:
            fio = guest.get('ФИО', guest.get('fio', ''))
            city = guest.get('город', 'не указан')
            age = guest.get('возраст', 0) or 0
            city_groups[city].append((fio, age, guest))
        
        # Получаем все доступные комнаты (2-местные и 3-местные)
        available_rooms = [r for r in self.rooms if r['room_id'] not in used_rooms and r['вместимость'] >= 2]
        available_rooms.sort(key=lambda x: x['вместимость'])
        
        room_idx = 0
        
        for city, guests_list in city_groups.items():
            # Сортируем по возрасту
            guests_list.sort(key=lambda x: x[1])
            
            i = 0
            while i < len(guests_list):
                if room_idx >= len(available_rooms):
                    # Нет комнат - заселяем по одному
                    for j in range(i, len(guests_list)):
                        fio, age, guest = guests_list[j]
                        allocations.append({
                            'ФИО': fio,
                            'room_id': 'нет мест',
                            'room_capacity': 0,
                            'comment': guest.get('comment', '')
                        })
                    break
                
                room = available_rooms[room_idx]
                capacity = room['вместимость']
                
                # Берем группу для этой комнаты
                group = []
                group_guests = []
                j = i
                while len(group) < capacity and j < len(guests_list):
                    group.append(guests_list[j][0])
                    group_guests.append(guests_list[j][2])
                    j += 1
                
                # Заселяем группу
                for g_fio, g_guest in zip(group, group_guests):
                    allocations.append({
                        'ФИО': g_fio,
                        'room_id': room['room_id'],
                        'room_capacity': capacity,
                        'comment': g_guest.get('comment', '')
                    })
                
                used_rooms.add(room['room_id'])
                room_idx += 1
                i = j
        
        return allocations
    
    def solve(self):
        """Основной метод расселения"""
        all_allocations = []
        used_rooms = set()
        
        # 1. Расселяем группы
        group_allocations = self.allocate_groups(used_rooms)
        all_allocations.extend(group_allocations)
        
        # 2. Расселяем желающих жить одних
        single_allocations = self.allocate_singles(used_rooms)
        all_allocations.extend(single_allocations)
        
        # 3. Расселяем оставшихся (члены ПК и обычные)
        remaining_allocations = self.allocate_remaining(used_rooms)
        all_allocations.extend(remaining_allocations)
        
        # 4. Добавляем нерезидентов
        for guest in self.guests:
            fio = guest.get('ФИО', guest.get('fio', ''))
            if fio and fio not in [a['ФИО'] for a in all_allocations]:
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
            'groups': [{'guests': g['guests'], 'size': g['size']} for g in self.together_groups],
            'singles_count': len(self.single_requests),
            'pc_members_count': len(self.pc_members),
            'regular_count': len(self.regular_guests)
        }


def solve_allocation(guests, rooms):
    """Основная функция расселения"""
    allocator = RoomAllocator(rooms, guests)
    result_df = allocator.solve()
    debug_info = allocator.get_debug_info()
    return result_df, debug_info
