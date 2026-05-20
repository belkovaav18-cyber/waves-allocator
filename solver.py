import pandas as pd
import re
from collections import defaultdict

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
        self.org_committee = [
            "Отинова Александра Владимировна", "Зорина Полина Валерьевна",
            "Цысарь Сергей Алексеевич", "Кабак Евгений Владиславович",
            "Снигирев Вячеслав Сергеевич", "Каминский Алексей Сергеевич",
            "Трунцов Иван Дммтриевич", "Дьяконов Евгений Алексеевич",
            "Кукушкин Дионисий Сергеевич", "Коньков Даниил Вячеславович",
            "Останин Григорий Сергеевич"
        ]
        
        # Предопределенные пары
        self.couples = [
            ('Камчатнов Анатолий Михайлович', 'Камчатнова Валентина Александровна'),
            ('Балуян Тигран Григорьевич', 'Попкова Анна Андреевна'),
            ('Сапожников Максим Викторович', 'Сапожникова Мария Александровна'),
            ('Рязанов Валерий Владимирович', 'Рязанова Ирина Вячеславовна')
        ]
        
        # Предопределенные тройки
        self.triples = [
            ['Вьюгинова Алена Александровна (докладчик), Новик Александр Александрович (сопровожд.), Вьюгинов Сергей Николаевич (сопровожд.)',
             'Новик Александр Александрович', 'Вьюгинов Сергей Николаевич'],
            ['Толстых Алина Дмитриевна', 'Очкина Варвара Алексеевна', 'Манышева Анна Андреевна']
        ]
        
        # Сбор информации о гостях
        self.guest_info = {}
        self.pc_members = []
        self.org_members = []
        self.single_requests = []      # Запросы из комментариев
        self.tariff_single = []        # Тариф без подселения (5000, 6100)
        self.regular_guests = []
        
        for guest in guests:
            fio = guest.get('ФИО', '')
            if not fio:
                continue
            
            comment = str(guest.get('comment', '')).lower()
            tariff = guest.get('тариф', 0) or 0
            
            self.guest_info[fio] = {
                'fio': fio,
                'age': guest.get('возраст', 0) or 0,
                'city': guest.get('город', 'не указан'),
                'gender': guest.get('пол', 'не указан'),
                'position': guest.get('должность', ''),
                'organization': guest.get('организация', ''),
                'comment': guest.get('comment', ''),
                'tariff': tariff,
                'nights': guest.get('число_ночей', 0) or 0,
                'cost': guest.get('стоимость', 0) or 0,
                'single_request': False,
                'preferred_building': None,
                'preferred_floor': None
            }
            
            # Парсинг комментария
            if 'без подселения' in comment or 'одноместный' in comment:
                self.guest_info[fio]['single_request'] = True
                self.single_requests.append(fio)
            
            if 'красный' in comment or 'корпус №1' in comment:
                self.guest_info[fio]['preferred_building'] = '1'
            if 'желтый' in comment or 'корпус №2' in comment:
                self.guest_info[fio]['preferred_building'] = '2'
            
            floor_match = re.search(r'(\d+)\s*этаж', comment)
            if floor_match:
                self.guest_info[fio]['preferred_floor'] = floor_match.group(1)
            
            # Тариф без подселения (5000 или 6100)
            if tariff in [5000, 6100]:
                self.tariff_single.append(fio)
                self.guest_info[fio]['single_request'] = True
            
            # Категоризация
            is_pc = False
            for pc in self.program_committee:
                if pc.lower().replace('.', '').replace(' ', '') in fio.lower().replace('.', '').replace(' ', ''):
                    is_pc = True
                    break
            
            is_org = fio in self.org_committee
            
            if is_pc:
                self.pc_members.append(fio)
            elif is_org:
                self.org_members.append(fio)
                self.guest_info[fio]['preferred_building'] = '2'
            else:
                self.regular_guests.append(fio)
    
    def _get_rooms_by_capacity(self, capacity, building=None, floor=None, exclude=None):
        rooms = [r for r in self.rooms if r['вместимость'] == capacity]
        if building:
            rooms = [r for r in rooms if str(r['room_id']).startswith(building)]
        if floor:
            rooms = [r for r in rooms if '-' in str(r['room_id']) and str(r['room_id']).split('-')[1].startswith(floor)]
        if exclude:
            rooms = [r for r in rooms if r['room_id'] not in exclude]
        return rooms
    
    def _find_room(self, guest, used_rooms, prefer_single=False, force_building=None):
        building = force_building or self.guest_info[guest].get('preferred_building')
        floor = self.guest_info[guest].get('preferred_floor')
        
        if prefer_single or self.guest_info[guest]['single_request']:
            # Сначала ищем 1-местные, потом 2-местные (но заселяем одного)
            capacities = [1, 2]
        else:
            capacities = [2, 3, 1]
        
        for cap in capacities:
            rooms = self._get_rooms_by_capacity(cap, building, floor, used_rooms)
            if rooms:
                return rooms[0]
            if floor:
                rooms = self._get_rooms_by_capacity(cap, building, None, used_rooms)
                if rooms:
                    return rooms[0]
        return None
    
    def _add_allocation(self, allocations, guest, room):
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
        
        # 1. Трешки
        for triple in self.triples:
            guests = [g for g in triple if g in self.guest_info and g not in allocated]
            if not guests:
                continue
            
            room = None
            # Ищем 3-местную комнату
            rooms_3 = self._get_rooms_by_capacity(3, exclude=used_rooms)
            if rooms_3:
                room = rooms_3[0]
            
            if room:
                used_rooms.add(room['room_id'])
                for guest in guests:
                    self._add_allocation(allocations, guest, room)
                    allocated.add(guest)
            else:
                for guest in guests:
                    self._add_allocation(allocations, guest, None)
                    allocated.add(guest)
        
        # 2. Пары
        for couple in self.couples:
            guests = [g for g in couple if g in self.guest_info and g not in allocated]
            if not guests:
                continue
            
            room = self._find_room(guests[0], used_rooms, prefer_single=False)
            if not room:
                rooms_2 = self._get_rooms_by_capacity(2, exclude=used_rooms)
                room = rooms_2[0] if rooms_2 else None
            
            if room:
                used_rooms.add(room['room_id'])
                for guest in guests:
                    self._add_allocation(allocations, guest, room)
                    allocated.add(guest)
        
        # 3. Программный комитет (с приоритетом на одноместные)
        for guest in self.pc_members:
            if guest in allocated:
                continue
            # ПК с тарифом без подселения - в однушку
            if guest in self.tariff_single or self.guest_info[guest]['single_request']:
                room = self._find_room(guest, used_rooms, prefer_single=True)
            else:
                room = self._find_room(guest, used_rooms, prefer_single=False)
            if room:
                used_rooms.add(room['room_id'])
            self._add_allocation(allocations, guest, room)
            allocated.add(guest)
        
        # 4. Оргкомитет (желтый корпус)
        for guest in self.org_members:
            if guest in allocated:
                continue
            room = self._find_room(guest, used_rooms, force_building='2')
            if room:
                used_rooms.add(room['room_id'])
            self._add_allocation(allocations, guest, room)
            allocated.add(guest)
        
        # 5. Тариф без подселения (5000, 6100) - селим одного в комнату
        for guest in self.tariff_single:
            if guest in allocated:
                continue
            room = self._find_room(guest, used_rooms, prefer_single=True)
            if room:
                used_rooms.add(room['room_id'])
            self._add_allocation(allocations, guest, room)
            allocated.add(guest)
        
        # 6. Запросы на одноместное из комментариев
        for guest in self.single_requests:
            if guest in allocated:
                continue
            room = self._find_room(guest, used_rooms, prefer_single=True)
            if room:
                used_rooms.add(room['room_id'])
            self._add_allocation(allocations, guest, room)
            allocated.add(guest)
        
        # 7. Остальные - группировка по полу, городу, возрасту
        remaining = [g for g in self.regular_guests if g not in allocated]
        
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
        
        def allocate_group(groups):
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
        
        allocate_group(male_by_city)
        allocate_group(female_by_city)
        
        # 8. Нерезиденты
        for guest in self.guests:
            fio = guest.get('ФИО', '')
            if fio and fio not in [a['ФИО'] for a in allocations]:
                self._add_allocation(allocations, fio, None)
        
        return pd.DataFrame(allocations)
    
    def get_debug_info(self):
        return {
            'pc_members': len(self.pc_members),
            'org_members': len(self.org_members),
            'tariff_single': len(self.tariff_single),
            'single_requests': len(self.single_requests),
            'regular': len(self.regular_guests)
        }


def solve_allocation(guests, rooms):
    allocator = RoomAllocator(rooms, guests)
    result_df = allocator.solve()
    debug_info = allocator.get_debug_info()
    return result_df, debug_info
