import streamlit as st
import pandas as pd
from datetime import datetime
import re

from sheets import load_guests, save_results_with_details
from preprocess import preprocess_guests
from solver_controller import smart_solve


SHEET_ID = "1lF4SV24wTo5OwsidQ7UPqBVaGzdw_fBSx0OuBJJ4cWg"
TAB = "Sheet"

st.title("🏨 Расселение")

rooms_df = pd.read_excel("data/rooms.xlsx")
rooms = rooms_df.to_dict("records")

raw = load_guests(SHEET_ID, TAB)
guests_df = preprocess_guests(raw)


# =========================================================
# ФУНКЦИИ ДЛЯ РАСЧЕТА ДАТ
# =========================================================
def extract_dates_from_guest(guest_fio, raw_df):
    # ... (оставляем как было)
    pass


# =========================================================
# ФУНКЦИИ ДЛЯ ВИЗУАЛИЗАЦИИ ПЛАНА ЭТАЖЕЙ
# =========================================================

def get_building_and_floor(room_id):
    """
    Извлекает корпус и этаж из ID комнаты.
    Возвращает (building, floor)
    """
    room_str = str(room_id)
    if '-' in room_str:
        parts = room_str.split('-')
        building = parts[0]
        room_num = parts[1]
        # Первая цифра номера комнаты = этаж
        floor = room_num[0] if room_num else '0'
        return building, floor
    else:
        # Если без корпуса, берем первую цифру номера
        floor = room_str[0] if room_str else '0'
        return None, floor


def create_floor_layout(allocation_df, rooms_df):
    """
    Создает словарь с планом этажей.
    
    Структура:
    {
        "1": {  # корпус
            "1": {  # этаж
                "101": {"capacity": 2, "guests": ["Иванов И.И."]},
                "102": {"capacity": 2, "guests": []},
                ...
            },
            "2": {...}
        },
        "2": {...}  # желтый корпус
    }
    """
    # Создаем словарь заселенных
    allocation_dict = {}
    for _, row in allocation_df.iterrows():
        room_id = row.get('room_id')
        fio = row.get('fio')
        if room_id and fio and room_id != "не проживает":
            if room_id not in allocation_dict:
                allocation_dict[room_id] = []
            allocation_dict[room_id].append(fio)
    
    # Строим план
    layout = {}
    
    for _, room in rooms_df.iterrows():
        room_id = room.get('room_id')
        capacity = room.get('вместимость', 1)
        
        building, floor = get_building_and_floor(room_id)
        
        # Определяем корпус (если нет, то по первой цифре ID)
        if building is None:
            # Пробуем определить по формату: если ID начинается с 1 или 2
            if str(room_id).startswith('1'):
                building = '1'
            elif str(room_id).startswith('2'):
                building = '2'
            else:
                building = 'unknown'
        
        # Инициализируем структуру
        if building not in layout:
            layout[building] = {}
        if floor not in layout[building]:
            layout[building][floor] = {}
        
        # Заполняем данные комнаты
        layout[building][floor][room_id] = {
            'capacity': capacity,
            'guests': allocation_dict.get(room_id, []),
            'free_spots': capacity - len(allocation_dict.get(room_id, []))
        }
    
    return layout


def render_floor_plan(layout, selected_building=None):
    """
    Отрисовывает план этажей с помощью HTML/CSS
    """
    if selected_building:
        buildings = [selected_building]
    else:
        buildings = sorted(layout.keys())
    
    for building in buildings:
        if building not in layout:
            continue
            
        st.markdown(f"### 🏢 Корпус {building}")
        
        floors = sorted(layout[building].keys(), key=int)
        
        for floor in floors:
            st.markdown(f"#### 📍 Этаж {floor}")
            
            rooms = layout[building][floor]
            
            # Сортируем комнаты по номеру
            sorted_rooms = sorted(rooms.items(), key=lambda x: int(re.sub(r'\D', '', x[0])))
            
            # Создаем сетку (4 колонки для комнат)
            cols = st.columns(4)
            
            for idx, (room_id, room_data) in enumerate(sorted_rooms):
                col = cols[idx % 4]
                
                # Определяем цвет в зависимости от заполненности
                if room_data['free_spots'] == 0:
                    status_color = "#28a745"  # зеленый - полная
                    status_text = "✅ Полностью"
                elif room_data['free_spots'] == room_data['capacity']:
                    status_color = "#dc3545"  # красный - пустая
                    status_text = "❌ Пустая"
                else:
                    status_color = "#ffc107"  # желтый - частично
                    status_text = f"⚠️ Свободно: {room_data['free_spots']}"
                
                # Формируем список гостей
                guests_list = "<br>".join(room_data['guests']) if room_data['guests'] else "—"
                
                # Создаем карточку комнаты
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
                                🛏️ {room_data['capacity']} места
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


def render_simple_floor_plan(layout):
    """
    Упрощенная версия плана этажей (текстовая таблица)
    """
    for building in layout:
        st.markdown(f"## Корпус {building}")
        
        floors = sorted(layout[building].keys(), key=int)
        
        for floor in floors:
            st.markdown(f"### Этаж {floor}")
            
            rooms = layout[building][floor]
            sorted_rooms = sorted(rooms.items(), key=lambda x: int(re.sub(r'\D', '', x[0])))
            
            # Создаем DataFrame для отображения
            table_data = []
            for room_id, room_data in sorted_rooms:
                guests_text = ", ".join(room_data['guests']) if room_data['guests'] else "—"
                table_data.append({
                    "Комната": room_id,
                    "Мест": room_data['capacity'],
                    "Свободно": room_data['free_spots'],
                    "Заселены": guests_text
                })
            
            df_rooms = pd.DataFrame(table_data)
            st.dataframe(df_rooms, use_container_width=True)


# =========================================================
# ОСНОВНОЙ КОД
# =========================================================

# -------------------------
# split
# -------------------------
non_residents = guests_df[guests_df["resident"] == False].copy()
residents = guests_df[guests_df["resident"] == True].copy()

st.subheader("Гости")
st.dataframe(guests_df)

if st.button("🚀 Расселить"):

    result, debug = smart_solve(
        residents.to_dict("records"),
        rooms
    )
    
    # Добавляем даты
    result_with_dates = []
    for _, row in result.iterrows():
        guest_data = row.to_dict()
        check_in, check_out = extract_dates_from_guest(guest_data["fio"], raw)
        guest_data["Дата заезда"] = check_in
        guest_data["Дата отъезда"] = check_out
        result_with_dates.append(guest_data)
    
    result_df = pd.DataFrame(result_with_dates)
    
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
    
    # =========================================================
    # ВИЗУАЛИЗАЦИЯ ПЛАНА ЭТАЖЕЙ
    # =========================================================
    st.subheader("🏠 План этажей с расселением")
    
    # Создаем layout только для расселенных (не нерезидентов)
    allocated_guests = final_result[final_result["room_id"] != "не проживает"]
    
    if len(allocated_guests) > 0:
        layout = create_floor_layout(allocated_guests, rooms_df)
        
        # Выбор корпуса для отображения
        building_filter = st.radio(
            "Выберите корпус:",
            options=["Все", "Красный (1)", "Желтый (2)"],
            horizontal=True
        )
        
        if building_filter == "Красный (1)":
            selected_building = "1"
        elif building_filter == "Желтый (2)":
            selected_building = "2"
        else:
            selected_building = None
        
        # Выбор стиля отображения
        view_style = st.radio(
            "Стиль отображения:",
            options=["Карточки", "Таблица"],
            horizontal=True
        )
        
        if view_style == "Карточки":
            render_floor_plan(layout, selected_building)
        else:
            if selected_building:
                filtered_layout = {selected_building: layout.get(selected_building, {})}
                render_simple_floor_plan(filtered_layout)
            else:
                render_simple_floor_plan(layout)
    else:
        st.info("Нет данных о расселении для отображения")
    
    # =========================================================
    # ТАБЛИЦА С РЕЗУЛЬТАТАМИ
    # =========================================================
    st.subheader("📋 Таблица расселения")
    display_columns = ['fio', 'room_id', 'room_capacity', 'Дата заезда', 'Дата отъезда']
    existing_display = [col for col in display_columns if col in final_result.columns]
    st.dataframe(final_result[existing_display], use_container_width=True)
    
    # Debug
    with st.expander("🔧 Debug информация"):
        st.json(debug)
    
    # Сохраняем
    save_results_with_details(
        SHEET_ID, 
        "Result", 
        final_result, 
        raw
    )
    
    st.success("✅ Готово! Результат сохранен в Google Sheets")
