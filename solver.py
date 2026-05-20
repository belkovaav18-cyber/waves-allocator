import pandas as pd
import numpy as np
from itertools import combinations
from collections import defaultdict

class RoomAllocator:
    def __init__(self, rooms, guests):
        self.rooms = rooms
        self.guests = guests
        self.room_capacity = {r['room_id']: r['вместимость'] for r in rooms}
        self.room_corpus = {r['room_id']: r.get('корпус', str(r['room_id'])[0] if '-' in str(r['room_id']) else '1') for r in rooms}
        
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
        
        # Нормализованные имена для проверки
        self.pc_normalized = [self._normalize_name(name) for name in self.program_committee]
        
        # Разделяем гостей на категории
        self.pc_members = []
        self.comment_guests = []
        self.regular_guests = []
        
        for guest in guests:
            # Получаем ФИО
            guest_fio = guest.get('ФИО', guest.get('fio', ''))
            guest['comment_text'] = str(guest.get('comment', ''))
            
            # Нормализуем для проверки
            normalized_guest = self._normalize_name(guest_fio)
            
            # Проверяем, член ли программного комитета
            is_pc = False
            for pc_name in self.pc_normalized:
                if pc_name in normalized_guest or normalized_guest in pc_name:
                    is_pc = True
                    break
            
            if is_pc:
                self.pc_members.append(guest)
            elif guest['comment_text'] and guest['comment_text'].strip() and guest['comment_text'] != 'nan':
                self.comment_guests.append(guest)
            else:
                self.regular_guests.append(guest)
        
        # Отладочный вывод
        print(f"DEBUG: Всего гостей: {len(guests)}")
        print(f"DEBUG: Члены ПК: {len(self.pc_members)}")
        print(f"DEBUG: С комментариями: {len(self.comment_guests)}")
        print(f"DEBUG: Обычные: {len(self.regular_guests)}")
        print(f"DEBUG: Комнат всего: {len(rooms)}")
        print(f"DEBUG: Одноместных: {len(self._get_single_rooms())}")
        print(f"DEBUG: Двухместных: {len(self._get_double_rooms())}")
        
        for guest in guests:
            guest['comment_text'] = guest.get('comment', '')
            if pd.isna(guest['comment_text']):
                guest['comment_text'] = ''
            
            # Проверяем, является ли гость членом программного комитета
            guest_fio = guest.get('ФИО', guest.get('fio', ''))
            normalized_guest = self._normalize_name(guest_fio)
            
            is_pc = False
            for pc_name in self.pc_normalized:
                if pc_name in normalized_guest or normalized_guest in pc_name:
                    is_pc = True
                    break
            
            if is_pc:
                self.pc_members.append(guest)
            elif guest['comment_text'] and str(guest['comment_text']).strip():
                self.comment_guests.append(guest)
            else:
                self.regular_guests.append(guest)
    
    def _normalize_name(self, name):
        """Нормализация имени для сравнения"""
        if not name:
            return ""
        name = str(name).lower()
        name = name.replace('.', '').replace(' ', '')
        return name
    
    def _get_single_rooms(self):
        """Получить список одноместных комнат"""
        return [r for r in self.rooms if r['вместимость'] == 1]
    
    def _get_double_rooms(self):
        """Получить список двухместных комнат"""
        return [r for r in self.rooms if r['вместимость'] == 2]
    
    def _get_rooms_by_capacity(self, capacity):
        """Получить комнаты определенной вместимости"""
        return [r for r in self.rooms if r['вместимость'] == capacity]
    
    def _get_guest_name(self, guest):
        """Получить имя гостя из разных возможных ключей"""
        return guest.get('ФИО', guest.get('fio', ''))
    
    def allocate_pc_members(self):
        """Расселить членов программного комитета"""
        allocations = []
        single_rooms = self._get_single_rooms()
        
        for i, guest in enumerate(self.pc_members):
            guest_name = self._get_guest_name(guest)
            if i < len(single_rooms):
                room = single_rooms[i]
                allocations.append({
                    'ФИО': guest_name,
                    'room_id': room['room_id'],
                    'room_capacity': room['вместимость'],
                    'comment': guest.get('comment_text', '')
                })
            else:
                double_rooms = self._get_double_rooms()
                if i - len(single_rooms) < len(double_rooms):
                    room = double_rooms[i - len(single_rooms)]
                    allocations.append({
                        'ФИО': guest_name,
                        'room_id': room['room_id'],
                        'room_capacity': room['вместимость'],
                        'comment': guest.get('comment_text', '')
                    })
                else:
                    allocations.append({
                        'ФИО': guest_name,
                        'room_id': 'не размещен',
                        'room_capacity': 0,
                        'comment': guest.get('comment_text', '')
                    })
        
        return allocations
    
    def allocate_by_city_and_age(self, guests):
        """Расселить гостей по городам и возрасту"""
        if not guests:
            return []
        
        city_groups = defaultdict(list)
        for guest in guests:
            city = guest.get('город', 'не указан')
            city_groups[city].append(guest)
        
        allocations = []
        used_rooms = set()
        double_rooms = self._get_double_rooms()
        double_rooms = sorted(double_rooms, key=lambda x: x['room_id'])
        
        for city, city_guests in city_groups.items():
            city_guests.sort(key=lambda x: x.get('возраст', 0) or 0)
            
            for i in range(0, len(city_guests), 2):
                room = None
                for r in double_rooms:
                    if r['room_id'] not in used_rooms:
                        room = r
                        break
                
                if room is None:
                    for guest in city_guests[i:i+2]:
                        allocations.append({
                            'ФИО': self._get_guest_name(guest),
                            'room_id': 'нет мест',
                            'room_capacity': 0,
                            'comment': guest.get('comment_text', '')
                        })
                else:
                    used_rooms.add(room['room_id'])
                    pair = city_guests[i:i+2]
                    for guest in pair:
                        allocations.append({
                            'ФИО': self._get_guest_name(guest),
                            'room_id': room['room_id'],
                            'room_capacity': room['вместимость'],
                            'comment': guest.get('comment_text', '')
                        })
        
        return allocations
    
    def allocate_with_comments(self, guests):
        """Обработать гостей с комментариями"""
        allocations = []
        
        for guest in guests:
            allocations.append({
                'ФИО': self._get_guest_name(guest),
                'room_id': 'требуется ручная обработка',
                'room_capacity': 0,
                'comment': guest.get('comment_text', ''),
                'comment_priority': True
            })
        
        return allocations
    
  def solve(self):
    """Основной метод расселения"""
    all_allocations = []
    
    # 1. Расселяем членов программного комитета
    if self.pc_members:
        pc_allocations = self.allocate_pc_members()
        all_allocations.extend(pc_allocations)
        print(f"DEBUG: Расселено членов ПК: {len(pc_allocations)}")
    
    # 2. Обрабатываем гостей с комментариями
    if self.comment_guests:
        comment_allocations = self.allocate_with_comments(self.comment_guests)
        all_allocations.extend(comment_allocations)
        print(f"DEBUG: Обработано с комментариями: {len(comment_allocations)}")
    
    # 3. Расселяем остальных по городам и возрасту
    if self.regular_guests:
        regular_allocations = self.allocate_by_city_and_age(self.regular_guests)
        all_allocations.extend(regular_allocations)
        print(f"DEBUG: Расселено обычных: {len(regular_allocations)}")
    
    print(f"DEBUG: Всего allocation записей: {len(all_allocations)}")
    
    if not all_allocations:
        # Если никого не расселили, создаем пустой DataFrame с правильными колонками
        return pd.DataFrame(columns=['ФИО', 'room_id', 'room_capacity', 'comment'])
    
    return pd.DataFrame(all_allocations)
    
    def get_debug_info(self):
        """Получить отладочную информацию"""
        return {
            'pc_members_count': len(self.pc_members),
            'pc_members': [self._get_guest_name(g) for g in self.pc_members],
            'comment_guests_count': len(self.comment_guests),
            'comment_guests': [{'fio': self._get_guest_name(g), 'comment': g['comment_text']} for g in self.comment_guests],
            'regular_guests_count': len(self.regular_guests),
            'single_rooms_count': len(self._get_single_rooms()),
            'double_rooms_count': len(self._get_double_rooms())
        }

def solve_allocation(guests, rooms):
    """Основная функция расселения"""
    allocator = RoomAllocator(rooms, guests)
    result_df = allocator.solve()
    debug_info = allocator.get_debug_info()
    return result_df, debug_info
