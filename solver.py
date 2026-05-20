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
        
        # Организационный комитет (из скрина)
        self.organizing_committee = [
            "Белокуров В.В.", "Макаров В.А.", "Федянин А.А.", "Калиш А.Н.",
            "Безменова А.Е.", "Дьяконов Е.А.", "Игнатьева Д.О.", "Князев Г.А.",
            "Крохмаль А.А.", "Лапина А.В.", "Цысарь С.А.", "Кабак Е.В.",
            "Коньков Д.В.", "Отинова А.В.", "Юшков В.В.", "Кукушкин Д.С.",
            "Левкин Г.Ю.", "Трунцов И.Д."
        ]
        
        # Пары (только они могут жить вместе разнополые)
        self.couples = [
            ('Камчатнов Анатолий Михайлович', 'Камчатнова Валентина Александровна'),
            ('Балуян Тигран Григорьевич', 'Попкова Анна Андреевна'),
            ('Сапожников Максим Викторович', 'Сапожникова Мария Александровна'),
            ('Рязанов Валерий Владимирович', 'Рязанова Ирина Вячеславовна')
        ]
        
        # Предопределенные группы
        self.predefined_groups = [
            {'guests': ['Вьюгинова Алена Александровна (докладчик), Новик Александр Александрович (сопровожд.), Вьюгинов Сергей Николаевич (сопровожд.)',
                        'Новик Александр Александрович', 'Вьюгинов Сергей Николаевич'], 'size': 3, 'preferred_capacity': 3},
            {'guests': ['Очиров Артем Александрович', 'Белоножко Дмитрий Федорович'], 'size': 2, 'preferred_capacity': 2},
            {'guests': ['Толстых Алина Дмитриевна', 'Очкина Варвара Алексеевна', 'Манышева Анна Андреевна'], 'size': 3, 'preferred_capacity': 3},
            {'guests': ['Камчатнов Анатолий Михайлович', 'Камчатнова Валентина Александровна'], 'size': 2, 'preferred_capacity': 2},
            {'guests': ['Балуян Тигран Григорьевич', 'Попкова Анна Андреевна'], 'size': 2, 'preferred_capacity': 2},
            {'guests': ['Сапожников Максим Викторович', 'Сапожникова Мария Александровна'], 'size': 2, 'preferred_capacity': 2},
            {'guests': ['Мороков Егор Степанович', 'Володарский Александр Борисович'], 'size': 2, 'preferred_capacity': 2},
            {'guests': ['Евсеев Дмитрий Александрович', 'Лапин Виктор Анатольевич'], 'size': 2, 'preferred_capacity': 2},
            {'guests': ['Федулов Игорь Николаевич', 'Ковалёв Александр Александрович'], 'size': 2, 'preferred_capacity': 2},
            {'guests': ['Солянов Алексей Александрович', 'Яснев Никита Юрьевич'], 'size': 2, 'preferred_capacity': 2},
            {'guests': ['Ким Пётр Николаевич', 'Пыхтин Дмитрий Алексеевич'], 'size': 2, 'preferred_capacity': 2},
            {'guests': ['Брулев Артем Игоревич', 'Горшков Артём Александрович'], 'size': 2, 'preferred_capacity': 2},
            {'guests': ['Калиш Андрей Николаевич', 'Цысарь Сергей Алексеевич'], 'size': 2, 'preferred_capacity': 2},
            {'guests': ['Юровская Софья Константиновна', 'Булдакова Анастасия Вячеславовна'], 'size': 2, 'preferred_capacity': 2}
        ]
        
        # Собираем информацию о гостях
        self.guest_info = {}
        self.pc_guests = []
        self.org_guests = []
        self.tariff_high_guests = []  # Тариф 5000/6100 - без подселения
        self.tariff_low_guests = []   # Тариф 3782/3100 - можно подселять
        self.regular_guests = []
        
        for guest in guests:
            fio = guest.get('ФИО', guest.get('fio', ''))
            if not fio:
                continue
            
            age = guest.get('возраст', 0) or 0
            tariff = guest.get('тариф', 0) or 0
            
            self.guest_info[fio] = {
                'fio': fio, 'age': age, 'city': guest.get('город', 'не указан'),
                'gender': guest.get('пол', 'не указан'), 'comment': str(guest.get('comment', '')),
                'tariff': tariff, 'single_request': False, 'preferred_building': None
            }
            
            comment = self.guest_info[fio]['comment'].lower()
            
            # Проверка на одноместное размещение
            if any(w in comment for w in ['без подселения', 'одноместный', 'не подселять']):
                self.guest_info[fio]['single_request'] = True
            
            # Проверка на корпус
            if 'красный' in comment or 'корпус №1' in comment:
                self.guest_info[fio]['preferred_building'] = '1'
            if 'желтый' in comment or 'корпус №2' in comment:
                self.guest_info[fio]['preferred_building'] = '2'
            
            # Категоризация
            normalized_fio = self._normalize_name(fio)
            
            # Проверка на программный комитет
            is_pc = False
            for pc_name in self.program_committee:
                if self._normalize_name(pc_name) in normalized_fio or normalized_fio in self._normalize_name(pc_name):
                    is_pc = True
                    break
            
            if is_pc:
                self.pc_guests.append(fio)
                continue
            
            # Проверка на организационный комитет
            is_org = False
            for org_name in self.organizing_committee:
                if self._normalize_name(org_name) in normalized_fio or normalized_fio in self._normalize_name(org_name):
                    is_org = True
                    break
            
            if is_org:
                self.org_guests.append(fio)
                self.guest_info[fio]['preferred_building'] = '2'  # Оргкомитет в желтый корпус
                continue
            
            # По тарифам
            if tariff in [5000, 6100]:
                self.tariff_high_guests.append(fio)
                self.guest_info[fio]['single_request'] = True
            elif tariff in [3782, 3100]:
                self.tariff_low_guests.append(fio)
            else:
                self.regular_guests.append(fio)
    
    def _normalize_name(self, name):
        if not name:
            return ""
        name = str(name).lower()
        name = re.sub(r'[^\w\s]', '', name)
        return name.replace(' ', '').replace('ё', 'е')
    
    def _is_couple(self, g1, g2):
        for c1, c2 in self.couples:
            if (g1 == c1 and g2 == c2) or (g1 == c2 and g2 == c1):
                return True
        return False
    
    def _can_share(self, g1, g2):
        g1_gender = self.guest_info.get(g1, {}).get('gender', 'не указан')
        g2_gender = self.guest_info.get(g2, {}).get('gender', 'не указан')
        
        if self._is_couple(g1, g2):
            return True
        if g1_gender == 'не указан' or g2_gender == 'не указан':
            return False
        return g1_gender == g2_gender
    
    def _get_rooms_by_capacity(self, capacity, building=None, exclude=None):
        rooms = [r for r in self.rooms if r['вместимость'] == capacity]
        if building:
            rooms = [r for r in rooms if str(r['room_id']).startswith(building)]
        if exclude:
            rooms = [r for r in rooms if r['room_id'] not in exclude]
        return rooms
    
    def _allocate_group(self, guests_list, used_rooms, building=None):
        allocations = []
        for guest in guests_list:
            # Ищем комнату
            room = None
            for capacity in [1, 2, 3]:
                rooms_avail = self._get_rooms_by_capacity(capacity, building, used_rooms)
                if rooms_avail:
                    room = rooms_avail[0]
                    break
            
            if room:
                used_rooms.add(room['room_id'])
                allocations.append({
                    'ФИО': guest,
                    'room_id': room['room_id'],
                    'room_capacity': room['вместимость'],
                    'comment': self.guest_info.get(guest, {}).get('comment', '')
                })
            else:
                allocations.append({
                    'ФИО': guest,
                    'room_id': 'нет мест',
                    'room_capacity': 0,
                    'comment': self.guest_info.get(guest, {}).get('comment', '')
                })
        return allocations
    
    def solve(self):
        allocations = []
        used_rooms = set()
        allocated = set()
        
        # 1. Предопределенные группы (пары и тройки)
        for group in self.predefined_groups:
            group_guests = [g for g in group['guests'] if g in self.guest_info]
            if not group_guests:
                continue
            
            # Проверка совместимости
            ok = True
            for i in range(len(group_guests)):
                for j in range(i+1, len(group_guests)):
                    if not self._can_share(group_guests[i], group_guests[j]):
                        ok = False
                        break
            
            if not ok:
                for g in group_guests:
                    allocations.append({'ФИО': g, 'room_id': 'ошибка: несовместимы', 'room_capacity': 0, 'comment': ''})
                    allocated.add(g)
                continue
            
            # Ищем комнату
            room = None
            for cap in [group['preferred_capacity'], group['size'], 3, 2]:
                rooms_avail = self._get_rooms_by_capacity(cap, exclude=used_rooms)
                if rooms_avail:
                    room = rooms_avail[0]
                    break
            
            if room:
                used_rooms.add(room['room_id'])
                for g in group_guests:
                    allocations.append({'ФИО': g, 'room_id': room['room_id'], 'room_capacity': room['вместимость'], 'comment': self.guest_info[g]['comment']})
                    allocated.add(g)
            else:
                for g in group_guests:
                    allocations.append({'ФИО': g, 'room_id': 'требуется ручная обработка', 'room_capacity': 0, 'comment': self.guest_info[g]['comment']})
                    allocated.add(g)
        
        # 2. Программный комитет (с учетом пожеланий)
        pc_not_allocated = [g for g in self.pc_guests if g not in allocated]
        for guest in pc_not_allocated:
            room = None
            building = self.guest_info[guest].get('preferred_building')
            for cap in [1, 2]:
                rooms_avail = self._get_rooms_by_capacity(cap, building, used_rooms)
                if rooms_avail:
                    room = rooms_avail[0]
                    break
            
            if room:
                used_rooms.add(room['room_id'])
                allocations.append({'ФИО': guest, 'room_id': room['room_id'], 'room_capacity': room['вместимость'], 'comment': self.guest_info[guest]['comment']})
                allocated.add(guest)
            else:
                allocations.append({'ФИО': guest, 'room_id': 'нет мест', 'room_capacity': 0, 'comment': self.guest_info[guest]['comment']})
                allocated.add(guest)
        
        # 3. Организационный комитет (в желтый корпус)
        org_not_allocated = [g for g in self.org_guests if g not in allocated]
        org_alloc = self._allocate_group(org_not_allocated, used_rooms, building='2')
        for a in org_alloc:
            allocated.add(a['ФИО'])
        allocations.extend(org_alloc)
        
        # 4. Высокий тариф (5000/6100) - без подселения
        high_not_allocated = [g for g in self.tariff_high_guests if g not in allocated]
        high_alloc = self._allocate_group(high_not_allocated, used_rooms)
        for a in high_alloc:
            allocated.add(a['ФИО'])
        allocations.extend(high_alloc)
        
        # 5. Низкий тариф и остальные - группируем по полу, городу, возрасту
        remaining = [g for g in self.tariff_low_guests + self.regular_guests if g not in allocated]
        
        # Группируем по полу и городу
        male_by_city = defaultdict(list)
        female_by_city = defaultdict(list)
        
        for fio in remaining:
            gender = self.guest_info[fio]['gender']
            city = self.guest_info[fio]['city']
            age = self.guest_info[fio]['age']
            if gender == 'М':
                male_by_city[city].append((fio, age))
            elif gender == 'Ж':
                female_by_city[city].append((fio, age))
            else:
                male_by_city[city].append((fio, age))  # Неизвестный пол - в мужские
        
        # Сортируем комнаты
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
                            allocations.append({'ФИО': fio, 'room_id': 'нет мест', 'room_capacity': 0, 'comment': self.guest_info[fio]['comment']})
                        return
                    room = available_rooms[room_idx]
                    capacity = room['вместимость']
                    group = []
                    j = i
                    while len(group) < capacity and j < len(guests_list):
                        group.append(guests_list[j][0])
                        j += 1
                    for fio in group:
                        allocations.append({'ФИО': fio, 'room_id': room['room_id'], 'room_capacity': capacity, 'comment': self.guest_info[fio]['comment']})
                    room_idx += 1
                    i = j
        
        allocate_by_gender(male_by_city)
        allocate_by_gender(female_by_city)
        
        # 6. Нерезиденты
        for guest in self.guests:
            fio = guest.get('ФИО', guest.get('fio', ''))
            if fio and fio not in [a['ФИО'] for a in allocations]:
                allocations.append({'ФИО': fio, 'room_id': 'не проживает', 'room_capacity': 0, 'comment': guest.get('comment', '')})
        
        return pd.DataFrame(allocations)
    
    def get_debug_info(self):
        return {
            'pc_guests': len(self.pc_guests),
            'org_guests': len(self.org_guests),
            'tariff_high': len(self.tariff_high_guests),
            'tariff_low': len(self.tariff_low_guests),
            'regular': len(self.regular_guests)
        }


def solve_allocation(guests, rooms):
    allocator = RoomAllocator(rooms, guests)
    result_df = allocator.solve()
    debug_info = allocator.get_debug_info()
    return result_df, debug_info
