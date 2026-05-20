import pandas as pd
import re
from collections import defaultdict

class RoomAllocator:
    def __init__(self, rooms, guests):
        self.rooms = rooms
        self.guests = guests
        self.room_capacity = {r['room_id']: r['вместимость'] for r in rooms}
        
        # Программный комитет (полные ФИО)
        self.program_committee = [
            "Козарь А.В.", "Калиш А.Н.", "Архипов Р.М.", "Балакший В.И.",
            "Белотелов В.И.", "Боголюбов А.Н.", "Бородачев Л.В.", "Бугай А.Н.",
            "Денисов В.И.", "Звездин А.К.", "Игнатьева Д.О.", "Короновский А.А.",
            "Котова С.П.", "Макаров В.А.", "Пирогов Ю.А.", "Пятаков А.П.",
            "Руденко О.В.", "Сазонов С.В.", "Сапожников О.А.", "Тимофеев И.В.",
            "Храмов А.Е.", "Цысарь С.А.", "Чашечкин Ю.Д.", "Черепенин В.А.",
            "Шандаров С.М."
        ]
        
        # Организационный комитет (фамилии из скрина)
        self.organizing_committee_surnames = [
            "Белокуров", "Макаров", "Федянин", "Калиш", "Безменова", "Дьяконов",
            "Игнатьева", "Князев", "Крохмаль", "Лапина", "Цысарь", "Кабак",
            "Коньков", "Отинова", "Юшков", "Кукушкин", "Левкин", "Трунцов"
        ]
        
        # Предопределенные группы (пары и тройки из комментариев)
        self.predefined_groups = [
            {'guests': ['Вьюгинова Алена Александровна (докладчик), Новик Александр Александрович (сопровожд.), Вьюгинов Сергей Николаевич (сопровожд.)',
                        'Новик Александр Александрович', 'Вьюгинов Сергей Николаевич'], 'size': 3},
            {'guests': ['Очиров Артем Александрович', 'Белоножко Дмитрий Федорович'], 'size': 2},
            {'guests': ['Толстых Алина Дмитриевна', 'Очкина Варвара Алексеевна', 'Манышева Анна Андреевна'], 'size': 3},
            {'guests': ['Камчатнов Анатолий Михайлович', 'Камчатнова Валентина Александровна'], 'size': 2},
            {'guests': ['Балуян Тигран Григорьевич', 'Попкова Анна Андреевна'], 'size': 2},
            {'guests': ['Сапожников Максим Викторович', 'Сапожникова Мария Александровна'], 'size': 2},
            {'guests': ['Мороков Егор Степанович', 'Володарский Александр Борисович'], 'size': 2},
            {'guests': ['Евсеев Дмитрий Александрович', 'Лапин Виктор Анатольевич'], 'size': 2},
            {'guests': ['Федулов Игорь Николаевич', 'Ковалёв Александр Александрович'], 'size': 2},
            {'guests': ['Солянов Алексей Александрович', 'Яснев Никита Юрьевич'], 'size': 2},
            {'guests': ['Ким Пётр Николаевич', 'Пыхтин Дмитрий Алексеевич'], 'size': 2},
            {'guests': ['Брулев Артем Игоревич', 'Горшков Артём Александрович'], 'size': 2},
            {'guests': ['Калиш Андрей Николаевич', 'Цысарь Сергей Алексеевич'], 'size': 2},
            {'guests': ['Юровская Софья Константиновна', 'Булдакова Анастасия Вячеславовна'], 'size': 2}
        ]
        
        # Сбор информации о гостях
        self.guest_info = {}
        self.org_guests = []      # Оргкомитет
        self.pc_guests_single = []   # ПК с запросом на одноместный
        self.pc_guests_regular = []  # ПК без запроса
        self.tariff_high = []      # Тариф 5000/6100
        self.tariff_low = []       # Тариф 3782/3100
        self.regular = []          # Остальные
        
        for guest in guests:
            fio = guest.get('ФИО', guest.get('fio', ''))
            if not fio:
                continue
            
            # Базовая информация
            self.guest_info[fio] = {
                'fio': fio,
                'surname': self._extract_surname(fio),
                'age': guest.get('возраст', 0) or 0,
                'city': guest.get('город', 'не указан'),
                'gender': guest.get('пол', 'не указан'),
                'position': guest.get('должность', ''),
                'organization': guest.get('организация', ''),
                'comment': str(guest.get('comment', '')),
                'tariff': guest.get('тариф', 0) or 0,
                'nights': guest.get('число_ночей', 0) or 0,
                'cost': guest.get('стоимость', 0) or 0,
                'single_request': False,
                'preferred_building': None,
                'preferred_floor': None
            }
            
            comment = self.guest_info[fio]['comment'].lower()
            
            # Пожелание по этажу - ищем цифру перед словом "этаж"
            floor_match = re.search(r'(\d+)\s*этаж', comment)
            if floor_match:
                self.guest_info[fio]['preferred_floor'] = floor_match.group(1)
            
            # Пожелание по корпусу
            if 'красный' in comment or 'корпус №1' in comment or 'корпус 1' in comment or 'красном' in comment:
                self.guest_info[fio]['preferred_building'] = '1'
            if 'желтый' in comment or 'корпус №2' in comment or 'корпус 2' in comment or 'желтом' in comment:
                self.guest_info[fio]['preferred_building'] = '2'
            
            # Запрос на одноместное размещение
            if any(w in comment for w in ['без подселения', 'одноместный', 'не подселять', 'без подселен']):
                self.guest_info[fio]['single_request'] = True
            
            # Категоризация
            is_org = self._is_organizing_committee(fio)
            is_pc = self._is_program_committee(fio)
            
            if is_org:
                # Оргкомитет → желтый корпус
                self.org_guests.append(fio)
                self.guest_info[fio]['preferred_building'] = '2'
            elif is_pc:
                if self.guest_info[fio]['single_request']:
                    self.pc_guests_single.append(fio)
                else:
                    self.pc_guests_regular.append(fio)
            elif self.guest_info[fio]['tariff'] in [5000, 6100]:
                self.tariff_high.append(fio)
                self.guest_info[fio]['single_request'] = True
            elif self.guest_info[fio]['tariff'] in [3782, 3100]:
                self.tariff_low.append(fio)
            else:
                self.regular.append(fio)
    
    def _extract_surname(self, fio):
        """Извлекает фамилию из ФИО"""
        if not fio:
            return ""
        # Убираем текст в скобках
        fio = re.sub(r'\([^)]*\)', '', str(fio))
        # Берем первое слово
        parts = fio.strip().split()
        return parts[0] if parts else ""
    
    def _is_organizing_committee(self, fio):
        """Проверка, входит ли гость в оргкомитет (по фамилии)"""
        surname = self._extract_surname(fio)
        for org_surname in self.organizing_committee_surnames:
            if org_surname.lower() == surname.lower():
                return True
        return False
    
    def _is_program_committee(self, fio):
        """Проверка, входит ли гость в программный комитет"""
        normalized_fio = self._normalize_name(fio)
        for pc_name in self.program_committee:
            if self._normalize_name(pc_name) in normalized_fio or normalized_fio in self._normalize_name(pc_name):
                return True
        return False
    
    def _normalize_name(self, name):
        if not name:
            return ""
        name = str(name).lower()
        name = re.sub(r'[^\w\s]', '', name)
        return name.replace(' ', '').replace('ё', 'е')
    
    def _get_rooms_by_capacity(self, capacity, building=None, floor=None, exclude=None):
        """Получить комнаты по критериям"""
        rooms = [r for r in self.rooms if r['вместимость'] == capacity]
        if building:
            rooms = [r for r in rooms if str(r['room_id']).startswith(building)]
        if floor:
            # Проверяем этаж (первая цифра после дефиса)
            rooms = [r for r in rooms if '-' in str(r['room_id']) and str(r['room_id']).split('-')[1].startswith(floor)]
        if exclude:
            rooms = [r for r in rooms if r['room_id'] not in exclude]
        return rooms
    
    def _find_best_room(self, guest, used_rooms, prefer_single=False, force_building=None):
        """Находит лучшую комнату для гостя с учетом всех пожеланий"""
        preferred_building = force_building or self.guest_info[guest].get('preferred_building')
        preferred_floor = self.guest_info[guest].get('preferred_floor')
        
        # Приоритеты вместимости
        if prefer_single:
            capacities = [1, 2]
        else:
            capacities = [2, 3, 1]
        
        # Сначала ищем с учетом и корпуса, и этажа
        if preferred_building and preferred_floor:
            for cap in capacities:
                rooms_avail = self._get_rooms_by_capacity(cap, preferred_building, preferred_floor, used_rooms)
                if rooms_avail:
                    return rooms_avail[0]
        
        # Только с корпусом
        if preferred_building:
            for cap in capacities:
                rooms_avail = self._get_rooms_by_capacity(cap, preferred_building, None, used_rooms)
                if rooms_avail:
                    return rooms_avail[0]
        
        # Только с этажом
        if preferred_floor:
            for cap in capacities:
                rooms_avail = self._get_rooms_by_capacity(cap, None, preferred_floor, used_rooms)
                if rooms_avail:
                    return rooms_avail[0]
        
        # Без предпочтений
        for cap in capacities:
            rooms_avail = self._get_rooms_by_capacity(cap, None, None, used_rooms)
            if rooms_avail:
                return rooms_avail[0]
        
        return None
    
    def _add_allocation(self, allocations, guest, room):
        """Добавляет запись о расселении"""
        allocations.append({
            'ФИО': guest,
            'room_id': room['room_id'] if room else 'нет мест',
            'room_capacity': room['вместимость'] if room else 0,
            'comment': self.guest_info[guest]['comment'],
            'возраст': self.guest_info[guest]['age'],
            'пол': self.guest_info[guest]['gender'],
            'должность': self.guest_info[guest]['position'],
            'город': self.guest_info[guest]['city'],
            'организация': self.guest_info[guest]['organization'],
            'тариф': self.guest_info[guest]['tariff'],
            'число_ночей': self.guest_info[guest]['nights'],
            'стоимость': self.guest_info[guest]['cost']
        })
    
    def solve(self):
        allocations = []
        used_rooms = set()
        allocated = set()
        
        # 1. Предопределенные группы (пары и тройки)
        for group in self.predefined_groups:
            group_guests = [g for g in group['guests'] if g in self.guest_info and g not in allocated]
            if not group_guests:
                continue
            
            # Ищем комнату подходящего размера с учетом пожеланий первого гостя
            first_guest = group_guests[0]
            room = self._find_best_room(first_guest, used_rooms, prefer_single=False)
            
            # Если не нашли, ищем без учета пожеланий
            if not room:
                for cap in [group['size'], 3, 2]:
                    rooms_avail = self._get_rooms_by_capacity(cap, exclude=used_rooms)
                    if rooms_avail:
                        room = rooms_avail[0]
                        break
            
            if room:
                used_rooms.add(room['room_id'])
                for guest in group_guests:
                    self._add_allocation(allocations, guest, room)
                    allocated.add(guest)
            else:
                for guest in group_guests:
                    self._add_allocation(allocations, guest, None)
                    allocated.add(guest)
        
        # 2. Оргкомитет (желтый корпус 2)
        for guest in self.org_guests:
            if guest in allocated:
                continue
            room = self._find_best_room(guest, used_rooms, force_building='2')
            if room:
                used_rooms.add(room['room_id'])
            self._add_allocation(allocations, guest, room)
            allocated.add(guest)
        
        # 3. Программный комитет с запросом на одноместный
        for guest in self.pc_guests_single:
            if guest in allocated:
                continue
            room = self._find_best_room(guest, used_rooms, prefer_single=True)
            if room:
                used_rooms.add(room['room_id'])
            self._add_allocation(allocations, guest, room)
            allocated.add(guest)
        
        # 4. Программный комитет без запроса
        for guest in self.pc_guests_regular:
            if guest in allocated:
                continue
            room = self._find_best_room(guest, used_rooms, prefer_single=False)
            if room:
                used_rooms.add(room['room_id'])
            self._add_allocation(allocations, guest, room)
            allocated.add(guest)
        
        # 5. Высокий тариф (5000/6100) - без подселения
        for guest in self.tariff_high:
            if guest in allocated:
                continue
            room = self._find_best_room(guest, used_rooms, prefer_single=True)
            if room:
                used_rooms.add(room['room_id'])
            self._add_allocation(allocations, guest, room)
            allocated.add(guest)
        
        # 6. Остальные (низкий тариф и обычные) - группировка по полу, городу, возрасту
        remaining = [g for g in self.tariff_low + self.regular if g not in allocated]
        
        # Группируем по полу и городу
        male_by_city = defaultdict(list)
        female_by_city = defaultdict(list)
        
        for fio in remaining:
            gender = self.guest_info[fio]['gender']
            city = self.guest_info[fio]['city']
            age = self.guest_info[fio]['age']
            if gender == 'Ж':
                female_by_city[city].append((fio, age))
            else:  # 'М' или 'не указан' - в мужские
                male_by_city[city].append((fio, age))
        
        # Доступные комнаты (2-х и 3-х местные)
        available_rooms = [r for r in self.rooms if r['room_id'] not in used_rooms and r['вместимость'] >= 2]
        available_rooms.sort(key=lambda x: x['вместимость'])
        room_idx = 0
        
        def allocate_by_gender(groups):
            nonlocal room_idx
            for city, guests_list in groups.items():
                # Сортируем по возрасту
                guests_list.sort(key=lambda x: x[1])
                i = 0
                while i < len(guests_list):
                    if room_idx >= len(available_rooms):
                        # Нет комнат - заселяем по одному
                        for j in range(i, len(guests_list)):
                            fio, _ = guests_list[j]
                            self._add_allocation(allocations, fio, None)
                        return
                    
                    room = available_rooms[room_idx]
                    capacity = room['вместимость']
                    group = []
                    j = i
                    while len(group) < capacity and j < len(guests_list):
                        group.append(guests_list[j][0])
                        j += 1
                    
                    for fio in group:
                        self._add_allocation(allocations, fio, room)
                    
                    room_idx += 1
                    i = j
        
        allocate_by_gender(male_by_city)
        allocate_by_gender(female_by_city)
        
        # 7. Нерезиденты
        for guest in self.guests:
            fio = guest.get('ФИО', guest.get('fio', ''))
            if fio and fio not in [a['ФИО'] for a in allocations]:
                allocations.append({
                    'ФИО': fio,
                    'room_id': 'не проживает',
                    'room_capacity': 0,
                    'comment': guest.get('comment', ''),
                    'возраст': self.guest_info.get(fio, {}).get('age', ''),
                    'пол': self.guest_info.get(fio, {}).get('gender', ''),
                    'должность': self.guest_info.get(fio, {}).get('position', ''),
                    'город': self.guest_info.get(fio, {}).get('city', ''),
                    'организация': self.guest_info.get(fio, {}).get('organization', ''),
                    'тариф': self.guest_info.get(fio, {}).get('tariff', ''),
                    'число_ночей': self.guest_info.get(fio, {}).get('nights', ''),
                    'стоимость': self.guest_info.get(fio, {}).get('cost', '')
                })
        
        return pd.DataFrame(allocations)
    
    def get_debug_info(self):
        return {
            'org_guests': len(self.org_guests),
            'org_list': self.org_guests[:10],
            'pc_single': len(self.pc_guests_single),
            'pc_regular': len(self.pc_guests_regular),
            'tariff_high': len(self.tariff_high),
            'tariff_low': len(self.tariff_low),
            'regular': len(self.regular)
        }


def solve_allocation(guests, rooms):
    allocator = RoomAllocator(rooms, guests)
    result_df = allocator.solve()
    debug_info = allocator.get_debug_info()
    return result_df, debug_info
