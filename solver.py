import pandas as pd
import re
from collections import defaultdict

# =========================================================
# ПАРСЕР КОММЕНТАРИЕВ (встроенный, без отдельного файла)
# =========================================================

class CommentParser:
    """Парсер комментариев для извлечения пожеланий по расселению"""
    
    def __init__(self):
        self.corpus_keywords = {
            '1': ['красный', 'красном', 'красн', 'корпус №1', 'корпус 1', '1 корпус', '№1', 'красный корпус'],
            '2': ['желтый', 'желтом', 'жёлтый', 'жёлтом', 'корпус №2', 'корпус 2', '2 корпус', '№2', 'желтый корпус']
        }
        self.floor_pattern = r'(\d+)\s*этаж[е]?'
        self.single_keywords = [
            'без подселения', 'без подселен', 'не подселять', 'один', 'одноместный',
            'без соседей', 'одиночный', 'только один'
        ]
    
    def clean_text(self, text):
        if not text or text == 'nan':
            return ''
        text = str(text).lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def extract_corpus(self, text):
        if not text:
            return None
        text = self.clean_text(text)
        for corpus_num, keywords in self.corpus_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return corpus_num
        return None
    
    def extract_floor(self, text):
        if not text:
            return None
        text = self.clean_text(text)
        match = re.search(self.floor_pattern, text)
        if match:
            return match.group(1)
        return None
    
    def extract_single_request(self, text):
        if not text:
            return False
        text = self.clean_text(text)
        for keyword in self.single_keywords:
            if keyword in text:
                return True
        return False
    
    def parse_comment(self, comment, fio):
        if not comment or comment == 'nan':
            return {
                'preferred_building': None,
                'preferred_floor': None,
                'single_request': False
            }
        text = self.clean_text(comment)
        return {
            'preferred_building': self.extract_corpus(text),
            'preferred_floor': self.extract_floor(text),
            'single_request': self.extract_single_request(text)
        }


comment_parser = CommentParser()


# =========================================================
# ОСНОВНОЙ КЛАСС РАССЕЛЕНИЯ
# =========================================================

class RoomAllocator:
    def __init__(self, rooms, guests):
        self.rooms = rooms
        self.guests = guests
        self.room_capacity = {r['room_id']: r['вместимость'] for r in rooms}
        
        # Программный комитет
        self.program_committee = [
            "Козарь А.В.", "Калиш А.Н.", "Архипов Р.М.", "Балакший В.И.",
            "Белотелов В.И.", "Боголюбов А.Н.", "Бородачев Л.В.", "Бугай А.Н.",
            "Денисов В.И.", "Звездин А.К.", "Игнатьева Д.О.", "Короновский А.А.",
            "Котова С.П.", "Макаров В.А.", "Пирогов Ю.А.", "Пятаков А.П.",
            "Руденко О.В.", "Сазонов С.В.", "Сапожников О.А.", "Тимофеев И.В.",
            "Храмов А.Е.", "Цысарь С.А.", "Чашечкин Ю.Д.", "Черепенин В.А.",
            "Шандаров С.М."
        ]
        
        # Организационный комитет
        self.organizing_committee_surnames = [
            "Белокуров", "Макаров", "Федянин", "Калиш", "Безменова", "Дьяконов",
            "Игнатьева", "Князев", "Крохмаль", "Лапина", "Цысарь", "Кабак",
            "Коньков", "Отинова", "Юшков", "Кукушкин", "Левкин", "Трунцов"
        ]
        
        # 1. Предопределенные группы (пары и тройки)
for group in self.predefined_groups:
    group_guests = [g for g in group['guests'] if g in self.guest_info and g not in allocated]
    if not group_guests:
        continue
    
    group_size = len(group_guests)
    
    # Проверяем, нужна ли трехместная комната
    min_capacity_needed = group_size  # Минимум вместимость = размер группы
    
    # Ищем комнату подходящего размера
    room = None
    
    # Для группы из 3 человек - сначала ищем 3-местные комнаты
    if group_size >= 3:
        capacities_to_try = [3, 4, 2]  # 3-местные, потом 4-местные, потом 2-местные (но это плохо)
    else:
        capacities_to_try = [group_size, 2, 3, 4]
    
    for cap in capacities_to_try:
        rooms_avail = self._get_rooms_by_capacity(cap, exclude=used_rooms)
        if rooms_avail:
            # Проверяем, что комната не будет переполнена
            room_candidate = rooms_avail[0]
            if room_candidate['вместимость'] >= group_size:
                room = room_candidate
                break
    
    if room:
        used_rooms.add(room['room_id'])
        for guest in group_guests:
            self._add_allocation(allocations, guest, room)
            allocated.add(guest)
        # Отладочный вывод
        print(f"Группа {group_guests} ({group_size} чел) заселена в {room['room_id']} (вм:{room['вместимость']})")
    else:
        # Не найдена подходящая комната
        for guest in group_guests:
            self._add_allocation(allocations, guest, None)
            allocated.add(guest)
        st.warning(f"Не найдена комната для группы {len(group_guests)} человек: {group_guests}")
        
        # Сбор информации о гостях
        self.guest_info = {}
        self.org_guests = []
        self.pc_guests_single = []
        self.pc_guests_regular = []
        self.tariff_high = []
        self.tariff_low = []
        self.regular = []
        self.all_single_requests = []
        
        for guest in guests:
            fio = guest.get('ФИО', guest.get('fio', ''))
            if not fio:
                continue
            
            comment = str(guest.get('comment', ''))
            parsed = comment_parser.parse_comment(comment, fio)
            
            self.guest_info[fio] = {
                'fio': fio,
                'surname': self._extract_surname(fio),
                'age': guest.get('возраст', 0) or 0,
                'city': guest.get('город', 'не указан'),
                'gender': guest.get('пол', 'не указан'),
                'position': guest.get('должность', ''),
                'organization': guest.get('организация', ''),
                'comment': comment,
                'tariff': guest.get('тариф', 0) or 0,
                'nights': guest.get('число_ночей', 0) or 0,
                'cost': guest.get('стоимость', 0) or 0,
                'single_request': parsed['single_request'],
                'preferred_building': parsed['preferred_building'],
                'preferred_floor': parsed['preferred_floor']
            }
            
            # Категоризация
            is_org = self._is_organizing_committee(fio)
            is_pc = self._is_program_committee(fio)
            
            if is_org:
                self.org_guests.append(fio)
                self.guest_info[fio]['preferred_building'] = '2'
            elif is_pc:
                if self.guest_info[fio]['single_request']:
                    self.pc_guests_single.append(fio)
                    self.all_single_requests.append(fio)
                else:
                    self.pc_guests_regular.append(fio)
            elif self.guest_info[fio]['tariff'] in [5000, 6100]:
                self.tariff_high.append(fio)
                self.guest_info[fio]['single_request'] = True
                self.all_single_requests.append(fio)
            elif self.guest_info[fio]['tariff'] in [3782, 3100]:
                self.tariff_low.append(fio)
            else:
                self.regular.append(fio)
            
            if self.guest_info[fio]['single_request'] and fio not in self.all_single_requests:
                self.all_single_requests.append(fio)
    
    def _extract_surname(self, fio):
        if not fio:
            return ""
        fio = re.sub(r'\([^)]*\)', '', str(fio))
        parts = fio.strip().split()
        return parts[0] if parts else ""
    
    def _is_organizing_committee(self, fio):
        surname = self._extract_surname(fio)
        for org_surname in self.organizing_committee_surnames:
            if org_surname.lower() == surname.lower():
                return True
        return False
    
    def _is_program_committee(self, fio):
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
        rooms = [r for r in self.rooms if r['вместимость'] == capacity]
        if building:
            rooms = [r for r in rooms if str(r['room_id']).startswith(building)]
        if floor:
            rooms = [r for r in rooms if '-' in str(r['room_id']) and str(r['room_id']).split('-')[1].startswith(floor)]
        if exclude:
            rooms = [r for r in rooms if r['room_id'] not in exclude]
        return rooms
    
    def _find_best_room(self, guest, used_rooms, prefer_single=False, force_building=None):
        preferred_building = force_building or self.guest_info[guest].get('preferred_building')
        preferred_floor = self.guest_info[guest].get('preferred_floor')
        single_request = self.guest_info[guest].get('single_request', False)
        
        if single_request or prefer_single:
            capacities = [1, 2]
        else:
            capacities = [2, 3, 1]
        
        # С корпусом и этажом
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
            # Проверка вместимости перед добавлением
    if room:
        current_occupants = sum(1 for a in allocations if a['room_id'] == room['room_id'])
        if current_occupants >= room['вместимость']:
            print(f"ОШИБКА: Комната {room['room_id']} переполнена! Вместимость {room['вместимость']}, уже {current_occupants} чел, пытаемся добавить {guest}")
            room = None  # Не добавляем в переполненную комнату
    
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
        
        # 1. Предопределенные группы
        for group in self.predefined_groups:
            group_guests = [g for g in group['guests'] if g in self.guest_info and g not in allocated]
            if not group_guests:
                continue
            
            first_guest = group_guests[0]
            room = self._find_best_room(first_guest, used_rooms, prefer_single=False)
            
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
        
        # 2. Оргкомитет (желтый корпус)
        for guest in self.org_guests:
            if guest in allocated:
                continue
            room = self._find_best_room(guest, used_rooms, force_building='2')
            if room:
                used_rooms.add(room['room_id'])
            self._add_allocation(allocations, guest, room)
            allocated.add(guest)
        
        # 3. ВСЕ с запросом на одноместное
        single_not_allocated = [g for g in self.all_single_requests if g not in allocated]
        
        for guest in single_not_allocated:
            single_rooms = self._get_rooms_by_capacity(1, exclude=used_rooms)
            if single_rooms:
                room = single_rooms[0]
            else:
                room = self._find_best_room(guest, used_rooms, prefer_single=True)
            
            if room:
                used_rooms.add(room['room_id'])
            self._add_allocation(allocations, guest, room)
            allocated.add(guest)
        
        # 4. ПК без запроса
        pc_regular_not_allocated = [g for g in self.pc_guests_regular if g not in allocated]
        for guest in pc_regular_not_allocated:
            room = self._find_best_room(guest, used_rooms, prefer_single=False)
            if room:
                used_rooms.add(room['room_id'])
            self._add_allocation(allocations, guest, room)
            allocated.add(guest)
        
        # 5. Остальные
        remaining = [g for g in self.tariff_low + self.regular if g not in allocated]
        
        male_by_city = defaultdict(list)
        female_by_city = defaultdict(list)
        
        for fio in remaining:
            gender = self.guest_info[fio]['gender']
            city = self.guest_info[fio]['city']
            age = self.guest_info[fio]['age']
            if gender == 'Ж':
                female_by_city[city].append((fio, age))
            else:
                male_by_city[city].append((fio, age))
        
        available_rooms = [r for r in self.rooms if r['room_id'] not in used_rooms and r['вместимость'] >= 2]
        available_rooms.sort(key=lambda x: x['вместимость'])
        room_idx = 0
        
        def allocate_by_gender(groups):
            nonlocal room_idx
            for city, guests_list in groups.items():
                guests_list.sort(key=lambda x: x[1])
                i = 0
                while i < len(guests_list):
                    if room_idx >= len(available_rooms):
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
        
        # 6. Нерезиденты
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
            'single_requests': len(self.all_single_requests),
            'single_list': self.all_single_requests[:10],
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
