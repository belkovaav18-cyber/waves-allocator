import streamlit as st
import pandas as pd
from datetime import datetime
import re
import io
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows

from sheets import load_guests, save_results_with_details, load_registration_data
from preprocess import preprocess_guests
from solver_controller import smart_solve

# =========================================================
# КОНСТАНТЫ (ОПРЕДЕЛЯЕМ В САМОМ НАЧАЛЕ)
# =========================================================
SHEET_ID = "1lF4SV24wTo5OwsidQ7UPqBVaGzdw_fBSx0OuBJJ4cWg"
REGISTRATION_SHEET_ID = "1fHjI0hTtlbjDZxSCWVidzGnJ7aY4joB7UUVXFEB0rxw"
TAB_NAME = "Sheet"

st.title("🏨 Расселение")

# Инициализация session state
if 'layout' not in st.session_state:
    st.session_state.layout = None
if 'final_result_df' not in st.session_state:
    st.session_state.final_result_df = None
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

rooms_df = pd.read_excel("data/rooms.xlsx")
rooms = rooms_df.to_dict("records")

# =========================================================
# ЗАГРУЗКА ДАННЫХ (ТОЛЬКО ОДИН РАЗ)
# =========================================================
if not st.session_state.data_loaded:
    with st.spinner("Загрузка данных..."):
        raw = load_guests(SHEET_ID, TAB_NAME)
        registration_df = load_registration_data(REGISTRATION_SHEET_ID, TAB_NAME)
        guests_df = preprocess_guests(raw, registration_df)
        st.session_state.raw = raw
        st.session_state.registration_df = registration_df
        st.session_state.guests_df = guests_df
        st.session_state.data_loaded = True
else:
    raw = st.session_state.raw
    registration_df = st.session_state.registration_df
    guests_df = st.session_state.guests_df


# =========================================================
# ФУНКЦИИ ДЛЯ РАСЧЕТА ДАТ
# =========================================================
def extract_dates_from_guest(guest_fio, raw_df):
    month_map = {
        "мая": 5, "июня": 6, "июля": 7, "августа": 8,
        "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
        "января": 1, "февраля": 2, "марта": 3, "апреля": 4
    }
    
    guest_row = None
    for idx, row in raw_df.iterrows():
        if row.get("ФИО") == guest_fio:
            guest_row = row
            break
    
    if guest_row is None:
        return "", ""
    
    selected_nights = []
    for col in raw_df.columns:
        col_str = str(col)
        if "Комната" in col_str and "ночь" in col_str:
            value = guest_row.get(col, "")
            if pd.notna(value) and str(value).strip().lower() not in ["", "нет", "-", "false", "nan"]:
                selected_nights.append(col_str)
    
    if not selected_nights:
        return "", ""
    
    def get_date_from_column(col_str):
        match = re.search(r"ночь на (\d+) (\w+)", col_str)
        if match:
            day = int(match.group(1))
            month_name = match.group(2)
            month = month_map.get(month_name, 6)
            year = 2026
            return (month, day, datetime(year, month, day))
        return (99, 99, None)
    
    nights_with_dates = []
    for night in selected_nights:
        month, day, date = get_date_from_column(night)
        if date:
            nights_with_dates.append((date, night, month, day))
    
    nights_with_dates.sort(key=lambda x: x[0])
    
    if not nights_with_dates:
        return "", ""
    
    first_date, first_night, first_month, first_day = nights_with_dates[0]
    
    if first_month == 6 and first_day == 1:
        check_in = datetime(2026, 5, 31)
    else:
        check_in = datetime(2026, first_month, first_day - 1)
    check_in_str = check_in.strftime("%d.%m.%Y")
    
    last_date, last_night, last_month, last_day = nights_with_dates[-1]
    check_out = datetime(2026, last_month, last_day)
    check_out_str = check_out.strftime("%d.%m.%Y")
    
    return check_in_str, check_out_str


# =========================================================
# ФУНКЦИИ ДЛЯ ВИЗУАЛИЗАЦИИ ПЛАНА ЭТАЖЕЙ
# =========================================================
def get_building_and_floor(room_id):
    room_str = str(room_id)
    if '-' in room_str:
        parts = room_str.split('-')
        building = parts[0]
        room_num = parts[1]
        floor = room_num[0] if room_num else '0'
        return building, floor
    else:
        floor = room_str[0] if room_str else '0'
        return None, floor


def create_floor_layout(allocation_df, rooms_df):
    allocation_dict = {}
    for _, row in allocation_df.iterrows():
        room_id = row.get('room_id')
        fio = row.get('fio')
        if room_id and fio and room_id != "не проживает":
            if room_id not in allocation_dict:
                allocation_dict[room_id] = []
            allocation_dict[room_id].append(fio)
    
    layout = {}
    
    for _, room in rooms_df.iterrows():
        room_id = room.get('room_id')
        capacity = room.get('вместимость', 1)
        
        building, floor = get_building_and_floor(room_id)
        
        if building is None or building == 'None':
            if str(room_id).startswith('1'):
                building = '1'
            elif str(room_id).startswith('2'):
                building = '2'
            else:
                building = 'unknown'
        
        if building not in layout:
            layout[building] = {}
        if floor not in layout[building]:
            layout[building][floor] = {}
        
        layout[building][floor][room_id] = {
            'capacity': capacity,
            'guests': allocation_dict.get(room_id, []),
            'free_spots': capacity - len(allocation_dict.get(room_id, []))
        }
    
    return layout


def render_floor_plan(layout, selected_building=None):
    if selected_building:
        buildings = [selected_building]
    else:
        buildings = sorted([b for b in layout.keys() if b != 'unknown'])
        if 'unknown' in layout:
            buildings.append('unknown')
    
    for building in buildings:
        if building not in layout:
            continue
        
        building_name = "Красный" if building == "1" else ("Желтый" if building == "2" else building)
        st.markdown(f"### 🏢 Корпус {building_name}")
        
        floors = sorted(layout[building].keys(), key=int)
        
        for floor in floors:
            st.markdown(f"#### 📍 Этаж {floor}")
            
            rooms = layout[building][floor]
            sorted_rooms = sorted(rooms.items(), key=lambda x: int(re.sub(r'\D', '', x[0])))
            
            cols = st.columns(4)
            
            for idx, (room_id, room_data) in enumerate(sorted_rooms):
                col = cols[idx % 4]
                
                if room_data['free_spots'] == 0:
                    status_color = "#28a745"
                    status_text = "✅ Полная"
                elif room_data['free_spots'] == room_data['capacity']:
                    status_color = "#dc3545"
                    status_text = "❌ Пустая"
                else:
                    status_color = "#ffc107"
                    status_text = f"⚠️ Свободно: {room_data['free_spots']}"
                
                guests_list = "<br>".join(room_data['guests']) if room_data['guests'] else "—"
                
                with col:
                    st.markdown(
                        f"""
                        <div style="
                            border: 2px solid {status_color};
                            border-radius: 10px;
                            padding: 10px;
                            margin: 5px;
                            background-color: #f8f9fa;
                        ">
                            <h3 style="text-align: center; margin: 0; color: {status_color};">
                                {room_id}
                            </h3>
                            <p style="text-align: center; margin: 5px 0;">
                                🛏️ {room_data['capacity']} {'место' if room_data['capacity'] == 1 else 'места'}
                            </p>
                            <p style="text-align: center; margin: 5px 0;">
                                📊 {status_text}
                            </p>
                            <hr style="margin: 5px 0;">
                            <div style="font-size: 12px;">
                                <strong>👥 Заселены:</strong><br>
                                {guests_list}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            
            st.markdown("---")


# =========================================================
# ФУНКЦИЯ ЭКСПОРТА В EXCEL
# =========================================================
def export_to_excel_with_styles(layout):
    """Экспортирует план этажей в Excel с цветами ячеек"""
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for building in layout:
            if building == 'unknown':
                continue
            
            building_name = "Красный_корпус" if building == "1" else "Желтый_корпус" if building == "2" else f"Корпус_{building}"
            
            floors = sorted(layout[building].keys(), key=int)
            
            for floor in floors:
                sheet_name = f"{building_name}_этаж_{floor}"[:31]
                
                rooms = layout[building][floor]
                sorted_rooms = sorted(rooms.items(), key=lambda x: int(re.sub(r'\D', '', x[0])))
                
                data = []
                row_data = []
                max_rooms_in_row = 4
                rooms_info = {}
                
                for idx, (room_id, room_data) in enumerate(sorted_rooms):
                    guests_text = "\n".join(room_data['guests']) if room_data['guests'] else "—"
                    cell_text = f"{room_id}\nМест: {room_data['capacity']}\nСвободно: {room_data['free_spots']}\n\nЗаселены:\n{guests_text}"
                    row_data.append(cell_text)
                    rooms_info[(idx // max_rooms_in_row, idx % max_rooms_in_row)] = room_data
                    
                    if len(row_data) == max_rooms_in_row:
                        data.append(row_data)
                        row_data = []
                
                if row_data:
                    while len(row_data) < max_rooms_in_row:
                        row_data.append("")
                    data.append(row_data)
                
                df = pd.DataFrame(data)
                df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
                
                workbook = writer.book
                worksheet = writer.sheets[sheet_name]
                
                green_fill = PatternFill(start_color="28A745", end_color="28A745", fill_type="solid")
                yellow_fill = PatternFill(start_color="FFC107", end_color="FFC107", fill_type="solid")
                red_fill = PatternFill(start_color="DC3545", end_color="DC3545", fill_type="solid")
                
                center_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                border = Border(
                    left=Side(style='thin'),
                    right=Side(style='thin'),
                    top=Side(style='thin'),
                    bottom=Side(style='thin')
                )
                
                for row_idx, row in enumerate(data, start=1):
                    for col_idx, cell_value in enumerate(row, start=1):
                        cell = worksheet.cell(row=row_idx, column=col_idx)
                        room_key = (row_idx - 1, col_idx - 1)
                        if room_key in rooms_info:
                            room_data = rooms_info[room_key]
                            if room_data['free_spots'] == 0:
                                cell.fill = green_fill
                                cell.font = Font(color="FFFFFF", bold=True)
                            elif room_data['free_spots'] == room_data['capacity']:
                                cell.fill = red_fill
                                cell.font = Font(color="FFFFFF", bold=True)
                            else:
                                cell.fill = yellow_fill
                                cell.font = Font(color="000000", bold=True)
                        else:
                            cell.fill = red_fill
                            cell.font = Font(color="FFFFFF", bold=True)
                        
                        cell.alignment = center_alignment
                        cell.border = border
                        col_letter = chr(64 + col_idx) if col_idx <= 26 else chr(64 + (col_idx // 26)) + chr(64 + (col_idx % 26))
                        worksheet.column_dimensions[col_letter].width = 30
                        worksheet.row_dimensions[row_idx].height = 120
    
    output.seek(0)
    return output


# =========================================================
# ФУНКЦИЯ ПРИНУДИТЕЛЬНОГО ПРИМЕНЕНИЯ ПРАВИЛ
# =========================================================
def enforce_manual_rules(result_df, guests_df, rooms_list):
    """
    Принудительное применение правил для конкретных случаев
    """
    result_df = result_df.copy()
    
    # Создаем словари для быстрого поиска
    room_map = {}
    for _, row in result_df.iterrows():
        if row['room_id'] != 'не проживает':
            room_map[row['fio']] = row['room_id']
    
    print("\n=== ПРИМЕНЕНИЕ РУЧНЫХ ПРАВИЛ ===")
    
    # =====================================================
    # ПРАВИЛО 1: Вьюгинова, Новик, Вьюгинов - в трехместный номер
    # =====================================================
    group_fios = [
        "Вьюгинова Алена Александровна",
        "Новик Александр Александрович", 
        "Вьюгинов Сергей Николаевич"
    ]
    
    group_in_result = [f for f in group_fios if f in room_map]
    
    if len(group_in_result) >= 2:
        three_bed_rooms = [r for r in rooms_list if r.get('вместимость') == 3]
        
        if three_bed_rooms:
            target_room = three_bed_rooms[0]['room_id']
            
            for fio in group_fios:
                if fio in room_map:
                    old_room = room_map[fio]
                    result_df.loc[result_df['fio'] == fio, 'room_id'] = target_room
                    result_df.loc[result_df['fio'] == fio, 'room_capacity'] = 3
                    print(f"  {fio}: {old_room} -> {target_room}")
            
            for fio in group_fios:
                if fio in room_map:
                    room_map[fio] = target_room
    
    # =====================================================
    # ПРАВИЛО 2: Солянов и Яснев - вместе
    # =====================================================
    if "Солянов Алексей Александрович" in room_map and "Яснев Никита Юрьевич" in room_map:
        room1 = room_map["Солянов Алексей Александрович"]
        room2 = room_map["Яснев Никита Юрьевич"]
        
        if room1 != room2:
            result_df.loc[result_df['fio'] == "Яснев Никита Юрьевич", 'room_id'] = room1
            print(f"  Яснев перемещен к Солянову в {room1}")
            room_map["Яснев Никита Юрьевич"] = room1
    
    # =====================================================
    # ПРАВИЛО 3: Мороков и Володарский - вместе
    # =====================================================
    if "Мороков Егор Степанович" in room_map and "Володарский Александр Борисович" in room_map:
        room1 = room_map["Мороков Егор Степанович"]
        room2 = room_map["Володарский Александр Борисович"]
        
        if room1 != room2:
            result_df.loc[result_df['fio'] == "Володарский Александр Борисович", 'room_id'] = room1
            print(f"  Володарский перемещен к Морокову в {room1}")
            room_map["Володарский Александр Борисович"] = room1
    
    # =====================================================
    # ПРАВИЛО 4: Евсеев + Лапин - вместе
    # =====================================================
    if "Евсеев Дмитрий Александрович" in room_map and "Лапин Виктор Анатольевич" in room_map:
        room_evseev = room_map["Евсеев Дмитрий Александрович"]
        room_lapin = room_map["Лапин Виктор Анатольевич"]
        
        if room_evseev != room_lapin:
            result_df.loc[result_df['fio'] == "Евсеев Дмитрий Александрович", 'room_id'] = room_lapin
            print(f"  Евсеев перемещен к Лапину в {room_lapin}")
            room_map["Евсеев Дмитрий Александрович"] = room_lapin
    
    # =====================================================
    # ПРАВИЛО 5: Калиш + Цысарь - вместе
    # =====================================================
    if "Калиш Андрей Николаевич" in room_map and "Цысарь Сергей Алексеевич" in room_map:
        room_kalish = room_map["Калиш Андрей Николаевич"]
        room_tsysar = room_map["Цысарь Сергей Алексеевич"]
        
        if room_kalish != room_tsysar:
            three_bed_rooms = [r for r in rooms_list if r.get('вместимость') == 3]
            if three_bed_rooms:
                target_room = three_bed_rooms[0]['room_id']
                result_df.loc[result_df['fio'] == "Калиш Андрей Николаевич", 'room_id'] = target_room
                result_df.loc[result_df['fio'] == "Цысарь Сергей Алексеевич", 'room_id'] = target_room
                print(f"  Калиш и Цысарь перемещены в трехместную {target_room}")
            else:
                result_df.loc[result_df['fio'] == "Цысарь Сергей Алексеевич", 'room_id'] = room_kalish
                print(f"  Цысарь перемещен к Калишу в {room_kalish}")
    
    # =====================================================
    # ПРАВИЛО 6: Трибельский - в красный корпус
    # =====================================================
    if "Трибельский Михаил Исаакович" in room_map:
        current_room = room_map["Трибельский Михаил Исаакович"]
        if not str(current_room).startswith('1'):
            red_rooms = [r for r in rooms_list if str(r.get('room_id', '')).startswith('1')]
            for red_room in red_rooms:
                room_id = red_room['room_id']
                capacity = red_room.get('вместимость', 2)
                current_occupants = len(result_df[result_df['room_id'] == room_id])
                if current_occupants < capacity:
                    result_df.loc[result_df['fio'] == "Трибельский Михаил Исаакович", 'room_id'] = room_id
                    print(f"  Трибельский перемещен в красный корпус: {room_id}")
                    break
    
    # =====================================================
    # ПРАВИЛО 7: Пугач - в красный корпус на 2 этаж
    # =====================================================
    if "Пугач Наталия Григорьевна" in room_map:
        current_room = room_map["Пугач Наталия Григорьевна"]
        is_red = str(current_room).startswith('1')
        floor = str(current_room).split('-')[1][0] if '-' in str(current_room) else None
        
        if not is_red or floor != '2':
            target_rooms = []
            for r in rooms_list:
                room_id = str(r.get('room_id', ''))
                if room_id.startswith('1') and '-' in room_id:
                    floor_num = room_id.split('-')[1][0]
                    if floor_num == '2':
                        target_rooms.append(r)
            
            for target in target_rooms:
                room_id = target['room_id']
                capacity = target.get('вместимость', 2)
                current_occupants = len(result_df[result_df['room_id'] == room_id])
                if current_occupants < capacity:
                    result_df.loc[result_df['fio'] == "Пугач Наталия Григорьевна", 'room_id'] = room_id
                    print(f"  Пугач перемещена в красный корпус 2 этаж: {room_id}")
                    break
    
    # =====================================================
    # ПРАВИЛО 8: Бородачев - одноместный в красном корпусе
    # =====================================================
    if "Бородачев Леонид Васильевич" in room_map:
        current_room = room_map["Бородачев Леонид Васильевич"]
        current_capacity_row = result_df[result_df['fio'] == "Бородачев Леонид Васильевич"]
        current_capacity = current_capacity_row['room_capacity'].iloc[0] if len(current_capacity_row) > 0 else 2
        
        if current_capacity != 1 or not str(current_room).startswith('1'):
            single_red_rooms = []
            for r in rooms_list:
                room_id = str(r.get('room_id', ''))
                capacity = r.get('вместимость', 2)
                if room_id.startswith('1') and capacity == 1:
                    single_red_rooms.append(r)
            
            for target in single_red_rooms:
                room_id = target['room_id']
                if len(result_df[result_df['room_id'] == room_id]) == 0:
                    result_df.loc[result_df['fio'] == "Бородачев Леонид Васильевич", 'room_id'] = room_id
                    result_df.loc[result_df['fio'] == "Бородачев Леонид Васильевич", 'room_capacity'] = 1
                    print(f"  Бородачев перемещен в одноместный красный: {room_id}")
                    break
    
    # =====================================================
    # ПРАВИЛО 9: Ржанов - на 1 этаж
    # =====================================================
    if "Ржанов Алексей Георгиевич" in room_map:
        current_room = room_map["Ржанов Алексей Георгиевич"]
        floor = str(current_room).split('-')[1][0] if '-' in str(current_room) else None
        
        if floor != '1':
            first_floor_rooms = []
            for r in rooms_list:
                room_id = str(r.get('room_id', ''))
                if '-' in room_id:
                    floor_num = room_id.split('-')[1][0]
                    if floor_num == '1':
                        first_floor_rooms.append(r)
            
            for target in first_floor_rooms:
                room_id = target['room_id']
                capacity = target.get('вместимость', 2)
                current_occupants = len(result_df[result_df['room_id'] == room_id])
                if current_occupants < capacity:
                    result_df.loc[result_df['fio'] == "Ржанов Алексей Георгиевич", 'room_id'] = room_id
                    print(f"  Ржанов перемещен на 1 этаж: {room_id}")
                    break
    
    print("===============================\n")
    return result_df


# =========================================================
# ФУНКЦИЯ ИСПРАВЛЕНИЯ ПЕРЕПОЛНЕННЫХ КОМНАТ
# =========================================================
def enforce_capacity_limits(result_df, rooms_list):
    """
    Проверяет и исправляет переполнение комнат
    """
    result_df = result_df.copy()
    
    # Создаем словарь вместимости комнат
    room_capacity = {r['room_id']: r['вместимость'] for r in rooms_list}
    
    # Специальные группы для 2-105
    girls_group = ["Толстых Алина Дмитриевна", "Очкина Варвара Алексеевна", "Манышева Анна Андреевна"]
    vyugin_group = ["Вьюгинова Алена Александровна", "Новик Александр Александрович", "Вьюгинов Сергей Николаевич"]
    
    print("\n=== ПРОВЕРКА ПЕРЕПОЛНЕННЫХ КОМНАТ ===")
    
    # Проверяем каждую комнату
    for room_id, capacity in room_capacity.items():
        occupants = result_df[result_df['room_id'] == room_id]['fio'].tolist()
        
        if len(occupants) > capacity:
            print(f"  Переполнена {room_id}: {len(occupants)}/{capacity}")
            
            # Специальная обработка для 2-105
            if room_id == "2-105":
                # Оставляем группу девочек в 2-105
                for g in girls_group:
                    if g in occupants:
                        pass  # остаются
                
                # Перемещаем группу Вьюгиновых в другую 3-местную
                vyugin_in_room = [v for v in vyugin_group if v in occupants]
                if vyugin_in_room:
                    three_bed_rooms = [r for r in rooms_list if r.get('вместимость') == 3 and r['room_id'] != "2-105"]
                    for r in three_bed_rooms:
                        rid = r['room_id']
                        if len(result_df[result_df['room_id'] == rid]) == 0:
                            for v in vyugin_in_room:
                                result_df.loc[result_df['fio'] == v, 'room_id'] = rid
                                result_df.loc[result_df['fio'] == v, 'room_capacity'] = 3
                            print(f"    Группа Вьюгиновых перемещена в {rid}")
                            break
                        elif len(result_df[result_df['room_id'] == rid]) < 3:
                            # Есть свободное место
                            for v in vyugin_in_room:
                                if len(result_df[result_df['room_id'] == rid]) < 3:
                                    result_df.loc[result_df['fio'] == v, 'room_id'] = rid
                                    result_df.loc[result_df['fio'] == v, 'room_capacity'] = 3
                            print(f"    Группа Вьюгиновых перемещена в {rid} (частично)")
                            break
                
                # Перемещаем остальных (Калиш, Цысарь и др.)
                others = [o for o in occupants if o not in girls_group and o not in vyugin_group]
                for person in others:
                    for r in rooms_list:
                        rid = r['room_id']
                        if rid != room_id and len(result_df[result_df['room_id'] == rid]) < r.get('вместимость', 2):
                            result_df.loc[result_df['fio'] == person, 'room_id'] = rid
                            print(f"    {person} -> {rid}")
                            break
            
            else:
                # Для других комнат - перемещаем лишних
                to_move = occupants[capacity:]
                for person in to_move:
                    for r in rooms_list:
                        rid = r['room_id']
                        if rid != room_id and len(result_df[result_df['room_id'] == rid]) < r.get('вместимость', 2):
                            result_df.loc[result_df['fio'] == person, 'room_id'] = rid
                            print(f"    {person} -> {rid}")
                            break
    
    print("===============================\n")
    return result_df


# =========================================================
# ОСНОВНОЙ КОД
# =========================================================
non_residents = guests_df[guests_df["resident"] == False].copy()
residents = guests_df[guests_df["resident"] == True].copy()

st.subheader("Гости")
st.dataframe(guests_df)

# Кнопка расселения
if st.button("🚀 Расселить"):

    with st.spinner("Идет расселение..."):
        result, debug = smart_solve(
            residents.to_dict("records"),
            rooms
        )
    
    # Проверяем, есть ли ошибка в результате
    if "error" in result.columns:
        st.error(f"❌ Ошибка при расселении: {result.iloc[0]['error']}")
        st.stop()
    
    if len(result) == 0:
        st.error("❌ Не удалось найти решение для расселения")
        st.stop()
    
    # Добавляем даты
    result_with_dates = []
    for _, row in result.iterrows():
        guest_data = row.to_dict()
        if 'fio' not in guest_data:
            st.error(f"❌ В результате нет колонки 'fio'. Доступные колонки: {list(guest_data.keys())}")
            st.stop()
        check_in, check_out = extract_dates_from_guest(guest_data["fio"], raw)
        guest_data["Дата заезда"] = check_in
        guest_data["Дата отъезда"] = check_out
        result_with_dates.append(guest_data)
    
    result_df = pd.DataFrame(result_with_dates)
    
    # ПРИМЕНЯЕМ РУЧНЫЕ ПРАВИЛА
    result_df = enforce_manual_rules(result_df, guests_df, rooms)
    
    # ИСПРАВЛЯЕМ ПЕРЕПОЛНЕННЫЕ КОМНАТЫ
    result_df = enforce_capacity_limits(result_df, rooms)
    
    # Нерезиденты
    non_residents_with_dates = []
    for _, row in non_residents.iterrows():
        guest_data = row.to_dict()
        check_in, check_out = extract_dates_from_guest(guest_data["fio"], raw)
        guest_data["Дата заезда"] = check_in
        guest_data["Дата отъезда"] = check_out
        guest_data["room_id"] = "не проживает"
        non_residents_with_dates.append(guest_data)
    
    non_residents_df = pd.DataFrame(non_residents_with_dates)
    
    # Объединяем
    final_result = pd.concat([result_df, non_residents_df], ignore_index=True)
    st.session_state.final_result_df = final_result
    
    # Создаем layout
    allocated_guests = final_result[final_result["room_id"] != "не проживает"]
    if len(allocated_guests) > 0 and len(rooms_df) > 0:
        st.session_state.layout = create_floor_layout(allocated_guests, rooms_df)
    
    # Сохраняем в Google Sheets
    save_results_with_details(
        SHEET_ID, 
        "Result", 
        final_result, 
        raw
    )
    
    st.success("✅ Готово! Результат сохранен в Google Sheets")
    st.rerun()


# =========================================================
# ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ
# =========================================================
if st.session_state.final_result_df is not None:
    
    # ВИЗУАЛИЗАЦИЯ ПЛАНА ЭТАЖЕЙ
    st.subheader("🏠 План этажей с расселением")
    
    if st.session_state.layout:
        # Выбор корпуса
        building_filter = st.radio(
            "Выберите корпус:",
            options=["Все", "Красный (1)", "Желтый (2)"],
            horizontal=True,
            key="building_filter"
        )
        
        if building_filter == "Красный (1)":
            selected_building = "1"
        elif building_filter == "Желтый (2)":
            selected_building = "2"
        else:
            selected_building = None
        
        render_floor_plan(st.session_state.layout, selected_building)
    
    # ТАБЛИЦА С РЕЗУЛЬТАТАМИ
    st.subheader("📋 Таблица расселения")
    display_columns = ['fio', 'room_id', 'room_capacity', 'Дата заезда', 'Дата отъезда']
    existing_display = [col for col in display_columns if col in st.session_state.final_result_df.columns]
    st.dataframe(st.session_state.final_result_df[existing_display], use_container_width=True)
    
    # Кнопка для экспорта в Excel
    if st.session_state.layout:
        st.markdown("---")
        st.subheader("📊 Экспорт в Excel")
        if st.button("📑 Экспорт всех этажей в Excel", type="primary"):
            with st.spinner("Создание Excel-файла..."):
                try:
                    excel_bytes = export_to_excel_with_styles(st.session_state.layout)
                    st.download_button(
                        label="📥 Скачать план расселения (Excel)",
                        data=excel_bytes,
                        file_name=f"plan_raseleniya_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_excel"
                    )
                    st.success("Excel-файл готов!")
                except Exception as e:
                    st.error(f"Ошибка при создании Excel: {str(e)}")
    
    # Кнопка для сброса
    if st.button("🔄 Новое расселение"):
        st.session_state.final_result_df = None
        st.session_state.layout = None
        st.rerun()
