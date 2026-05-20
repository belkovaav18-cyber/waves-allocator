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
        
        # Предопределенные группы (ручное сопоставление)
        self.predefined_groups = self._get_predefined_groups()
        
        # Разделяем гостей
        self.pc_members = []
        self.regular_guests = []
        self.guest_info = {}
        
        for guest in guests:
            fio = guest.get('ФИО', guest.get('fio', ''))
            if not fio:
                continue
            
            self.guest_info[fio] = {
                'fio': fio,
                'age': guest.get('возраст', 0),
                'city': guest.get('город', 'не указан'),
                'position': guest.get('должность', ''),
                'comment': str(guest.get('comment', '')),
                'single_request': False,
                'preferred_building': None
            }
            
            comment = self.guest_info[fio]['comment'].lower()
            
            # Проверка на одноместное размещение
            if any(word in comment for word in ['без подселения', 'одноместный', 'не подселять']):
                self.guest_info[fio]['single_request'] = True
            
            # Проверка на корпус
            if 'красный' in comment or 'корпус №1' in comment:
                self.guest_info[fio]['preferred_building'] = '1'
            if 'желтый' in comment or 'корпус №2' in comment:
                self.guest_info[fio]['preferred_building'] = '2'
            
            # Проверка на членство в ПК
            normalized_fio = self._normalize_name(fio)
            is_pc = any(pc in normalized_fio or normalized_fio in pc for pc in [self._normalize_name(name) for name in self.program_committee])
            
            if is_pc:
                self.pc_members.append(guest)
            else:
                self.regular_guests.append(guest)
    
    def _normalize_name(self, name):
        if not name:
            return ""
        name = str(name).lower()
        name = re.sub(r'[^\w\s]', '', name)
        name = name.replace(' ', '').replace('ё', 'е')
        return name
    
    def _get_predefined_groups(self):
        """Предопределенные группы из комментариев"""
        groups = []
        
        # Группа 1: Вьюгинова, Новик, Вьюгинов (3 человека)
        groups.append({
            'guests': ['Вьюгинова Алена Александровна (докладчик), Новик Александр Александрович (сопровожд.), Вьюгинов Сергей Николаевич (сопровожд.)',
                       'Новик Александр Александрович',
                       'Вьюгинов Сергей Николаевич'],
            'size': 3,
            'preferred_capacity': 3
        })
        
        # Группа 2: Очиров, Белоножко, Чернов (3 человека)
        groups.append({
            'guests': ['Очиров Артем Александрович', 'Белоножко Дмитрий Федорович'],
            'size': 2,
            'preferred_capacity': 2
        })
        
        # Группа 3: Толстых, Очкина, Манышева (3 девушки)
        groups.append({
            'guests': ['Толстых Алина Дмитриевна', 'Очкина Варвара Алексеевна', 'Манышева Анна Андреевна'],
            'size': 3,
            'preferred_capacity': 3
        })
        
        # Группа 4: Камчатнов и Камчатнова (пара)
        groups.append({
            'guests': ['Камчатнов Анатолий Михайлович', 'Камчатнова Валентина Александровна'],
            'size': 2,
            'preferred_capacity': 2
        })
        
        # Группа 5: Балуян и Попкова (пара)
        groups.append({
            'guests': ['Балуян Тигран Григорьевич', 'Попкова Анна Андреевна'],
            'size': 2,
            'preferred_capacity': 2
        })
        
        # Группа 6: Сапожников и Сапожникова (пара)
        groups.append({
            'guests': ['Сапожников Максим Викторович', 'Сапожникова Мария Александровна'],
            'size': 2,
            'preferred_capacity': 2
        })
        
        # Группа 7: Мороков и Володарский
        groups.append({
            'guests': ['Мороков Егор Степанович', 'Володарский Александр Борисович'],
            'size': 2,
            'preferred_capacity': 2
        })
        
        # Группа 8: Евсеев и Лапин
        groups.append({
            'guests': ['Евсеев Дмитрий Александрович', 'Лапин Виктор Анатольевич'],
            'size': 2,
            'preferred_capacity': 2
        })
        
        # Группа 9: Федулов и Ковалёв
        groups.append({
            'guests': ['Федулов Игорь Николаевич', 'Ковалёв Александр Александрович'],
            'size': 2,
            'preferred_capacity': 2
        })
        
        # Группа 10: Солянов и Яснев
        groups.append({
            'guests': ['Солянов Алексей Александрович', 'Яснев Никита Юрьевич'],
            'size': 2,
            'preferred_capacity': 2
        })
        
        # Группа 11: Ким и Пыхтин
        groups.append({
            'guests': ['Ким Пётр Николаевич', 'Пыхтин Дмитрий Алексеевич'],
            'size': 2,
            'preferred_capacity': 2
        })
        
        # Группа 12: Брулев и Горшков
        groups.append({
            'guests': ['Брулев Артем Игоревич', 'Горшков Артём Александрович'],
            'size': 2,
            'preferred_capacity': 2
        })
        
        # Группа 13: Калиш и Цысарь
        groups.append({
            'guests': ['Калиш Андрей Николаевич', 'Цысарь Сергей Алексеевич'],
            'size': 2,
            'preferred_capacity': 2
        })
        
        return groups
    
    def _get_rooms_by_capacity(self, capacity, building=None, exclude_rooms=None):
        rooms = [r for r in self.rooms if r['вместимость'] == capacity]
        if building:
            rooms = [r for r in rooms if str(r['room_id']).startswith(building)]
        if exclude_rooms:
            rooms = [r for r in rooms if r['room_id'] not in exclude_rooms]
        return rooms
    
    def solve(self):
        """Основной метод расселения"""
        allocations = []
        used_rooms = set()
        allocated_guests = set()
        
        # 1. Расселяем предопределенные группы
        for group in self.predefined_groups:
            group_guests = [g for g in group['guests'] if g in self.guest_info]
            if not group_guests:
                continue
            
            # Ищем комнату
            room = None
            for capacity in [group['preferred_capacity'], group['size'], 3, 2]:
                rooms_available = self._get_rooms_by_capacity(capacity, exclude_rooms=used_rooms)
                if rooms_available:
                    room = rooms_available[0]
                    break
            
            if room:
                used_rooms.add(room['room_id'])
                for guest in group_guests:
                    allocations.append({
                        'ФИО': guest,
                        'room_id': room['room_id'],
                        'room_capacity': room['вместимость'],
                        'comment': self.guest_info.get(guest, {}).get('comment', '')
                    })
                    allocated_guests.add(guest)
        
        # 2. Расселяем желающих жить одних
        single_rooms = self._get_rooms_by_capacity(1, exclude_rooms=used_rooms)
        single_guests = [fio for fio, info in self.guest_info.items() 
                        if info.get('single_request') and fio not in allocated_guests]
        
        for guest in single_guests:
            if single_rooms:
                room = single_rooms.pop(0)
                used_rooms.add(room['room_id'])
                allocations.append({
                    'ФИО': guest,
                    'room_id': room['room_id'],
                    'room_capacity': 1,
                    'comment': self.guest_info.get(guest, {}).get('comment', '')
                })
                allocated_guests.add(guest)
        
        # 3. Расселяем членов ПК
        pc_rooms = self._get_rooms_by_capacity(2, exclude_rooms=used_rooms)
        for guest in self.pc_members:
            fio = guest.get('ФИО', guest.get('fio', ''))
            if fio in allocated_guests:
                continue
            
            if pc_rooms:
                room = pc_rooms.pop(0)
                used_rooms.add(room['room_id'])
                allocations.append({
                    'ФИО': fio,
                    'room_id': room['room_id'],
                    'room_capacity': 2,
                    'comment': self.guest_info.get(fio, {}).get('comment', '')
                })
                allocated_guests.add(fio)
        
        # 4. Расселяем оставшихся по городам
        remaining = [fio for fio in self.guest_info.keys() if fio not in allocated_guests]
        
        # Группируем по городам
        city_groups = defaultdict(list)
        for fio in remaining:
            city = self.guest_info[fio]['city']
            age = self.guest_info[fio]['age']
            city_groups[city].append((fio, age))
        
        # Сортируем комнаты
        available_rooms = [r for r in self.rooms if r['room_id'] not in used_rooms and r['вместимость'] >= 2]
        available_rooms.sort(key=lambda x: x['вместимость'])
        
        room_idx = 0
        for city, guests_list in city_groups.items():
            guests_list.sort(key=lambda x: x[1])
            i = 0
            while i < len(guests_list):
                if room_idx >= len(available_rooms):
                    # Нет комнат
                    for j in range(i, len(guests_list)):
                        fio, _ = guests_list[j]
                        allocations.append({
                            'ФИО': fio,
                            'room_id': 'нет мест',
                            'room_capacity': 0,
                            'comment': self.guest_info.get(fio, {}).get('comment', '')
                        })
                    break
                
                room = available_rooms[room_idx]
                capacity = room['вместимость']
                
                group = []
                j = i
                while len(group) < capacity and j < len(guests_list):
                    group.append(guests_list[j][0])
                    j += 1
                
                for g_fio in group:
                    allocations.append({
                        'ФИО': g_fio,
                        'room_id': room['room_id'],
                        'room_capacity': capacity,
                        'comment': self.guest_info.get(g_fio, {}).get('comment', '')
                    })
                
                room_idx += 1
                i = j
        
        # 5. Добавляем нерезидентов
        for guest in self.guests:
            fio = guest.get('ФИО', guest.get('fio', ''))
            if fio and fio not in [a['ФИО'] for a in allocations]:
                allocations.append({
                    'ФИО': fio,
                    'room_id': 'не проживает',
                    'room_capacity': 0,
                    'comment': guest.get('comment', '')
                })
        
        return pd.DataFrame(allocations)
    
    def get_debug_info(self):
        return {
            'total_guests': len(self.guest_info),
            'predefined_groups': len(self.predefined_groups),
            'pc_members': len(self.pc_members),
            'single_requests': len([i for i in self.guest_info.values() if i.get('single_request')])
        }


def solve_allocation(guests, rooms):
    allocator = RoomAllocator(rooms, guests)
    result_df = allocator.solve()
    debug_info = allocator.get_debug_info()
    return result_df, debug_info
