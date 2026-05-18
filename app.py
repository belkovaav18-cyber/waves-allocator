import streamlit as st
import pandas as pd
from datetime import datetime
import re
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import tempfile
import os

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
    """
    Извлекает даты заезда и отъезда для конкретного гостя по ФИО.
    Возвращает (дата_заезда, дата_отъезда) в формате строки.
    """
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
    """Извлекает корпус и этаж из ID комнаты."""
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
    """Создает словарь с планом этажей."""
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


# =========================================================
# ФУНКЦИИ ДЛЯ ЭКСПОРТА В PDF
# =========================================================

def create_floor_pdf(layout, building, floor, output_filename):
    """
    Создает PDF-файл для одного этажа одного корпуса.
    """
    # Регистрируем русский шрифт
    try:
        pdfmetrics.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
        font_name = 'DejaVu'
    except:
        font_name = 'Helvetica'
    
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=landscape(A4),
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=1*cm,
        bottomMargin=1*cm
    )
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='RussianStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10
    ))
    styles.add(ParagraphStyle(
        name='TitleStyle',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=16,
        alignment=1  # Center
    ))
    styles.add(ParagraphStyle(
        name='FloorStyle',
        parent=styles['Heading2'],
        fontName=font_name,
        fontSize=14,
        alignment=1
    ))
    
    story = []
    
    # Заголовок
    building_name = "Красный корпус" if building == "1" else ("Желтый корпус" if building == "2" else f"Корпус {building}")
    title = Paragraph(f"{building_name} - Этаж {floor}", styles['TitleStyle'])
    story.append(title)
    story.append(Spacer(1, 0.5*cm))
    
    # Получаем комнаты на этаже
    rooms = layout[building][floor]
    sorted_rooms = sorted(rooms.items(), key=lambda x: int(re.sub(r'\D', '', x[0])))
    
    # Создаем таблицу (4 колонки для комнат)
    table_data = []
    row = []
    
    for idx, (room_id, room_data) in enumerate(sorted_rooms):
        # Формируем содержимое ячейки
        guests_text = "\n".join(room_data['guests']) if room_data['guests'] else "—"
        
        cell_content = f"""
        <b>{room_id}</b><br/>
        🛏️ {room_data['capacity']} мест<br/>
        🟢 Свободно: {room_data['free_spots']}<br/>
        <br/>
        <b>Заселены:</b><br/>
        {guests_text}
        """
        
        row.append(Paragraph(cell_content, styles['RussianStyle']))
        
        if len(row) == 4:
            table_data.append(row)
            row = []
    
    # Добавляем последний ряд
    if row:
        while len(row) < 4:
            row.append(Paragraph("", styles['RussianStyle']))
        table_data.append(row)
    
    # Создаем таблицу
    table = Table(table_data, colWidths=[6*cm, 6*cm, 6*cm, 6*cm])
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(table)
    
    # Дата генерации
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(
        f"Дата генерации: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        styles['RussianStyle']
    ))
    
    doc.build(story)


def export_all_floors_to_pdf(layout):
    """
    Экспортирует все этажи всех корпусов в отдельные PDF-файлы.
    Возвращает словарь {название_файла: путь_к_файлу}
    """
    pdf_files = {}
    
    for building in layout:
        if building == 'unknown':
            continue
        
        building_name = "red" if building == "1" else "yellow" if building == "2" else building
        
        for floor in layout[building]:
            filename = f"floor_{building_name}_{floor}.pdf"
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                create_floor_pdf(layout, building, floor, tmp.name)
                pdf_files[f"Корпус {building_name} Этаж {floor}"] = tmp.name
    
    return pdf_files


def render_floor_plan(layout, selected_building=None):
    """Отрисовывает план этажей с помощью HTML/CSS"""
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
# ОСНОВНОЙ КОД
# =========================================================

non_residents = guests_df[guests_df["resident"] == False].copy()
residents = guests_df[guests_df["resident"] == True].copy()

st.subheader("Гости")
st.dataframe(guests_df)

if st.button("🚀 Расселить"):

    with st.spinner("Идет расселение..."):
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
    
    allocated_guests = final_result[final_result["room_id"] != "не проживает"]
    
    if len(allocated_guests) > 0 and len(rooms_df) > 0:
        layout = create_floor_layout(allocated_guests, rooms_df)
        
        if layout:
            # Выбор корпуса
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
            
            # Выбор стиля
            view_style = st.radio(
                "Стиль отображения:",
                options=["Карточки", "Таблица"],
                horizontal=True
            )
            
            if view_style == "Карточки":
                render_floor_plan(layout, selected_building)
            else:
                if selected_building:
                    if selected_building in layout:
                        filtered_layout = {selected_building: layout[selected_building]}
                        render_simple_floor_plan(filtered_layout)
                    else:
                        st.warning(f"Корпус {selected_building} не найден")
                else:
                    render_simple_floor_plan(layout)
            
            # =========================================================
            # ЭКСПОРТ В PDF
            # =========================================================
            st.markdown("---")
            st.subheader("📄 Экспорт в PDF")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📑 Экспорт всех этажей в PDF", type="primary"):
                    with st.spinner("Создание PDF-файлов..."):
                        try:
                            pdf_files = export_all_floors_to_pdf(layout)
                            
                            if pdf_files:
                                st.success(f"Создано {len(pdf_files)} PDF-файлов!")
                                
                                # Показываем кнопки скачивания для каждого файла
                                for name, filepath in pdf_files.items():
                                    with open(filepath, 'rb') as f:
                                        pdf_data = f.read()
                                    
                                    st.download_button(
                                        label=f"📥 Скачать {name}",
                                        data=pdf_data,
                                        file_name=f"{name.replace(' ', '_')}.pdf",
                                        mime="application/pdf",
                                        key=f"download_{name}"
                                    )
                                    
                                    # Удаляем временный файл
                                    os.unlink(filepath)
                            else:
                                st.warning("Нет этажей для экспорта")
                        except Exception as e:
                            st.error(f"Ошибка при создании PDF: {str(e)}")
            
            with col2:
                st.info("💡 Будет создан отдельный PDF-файл для каждого этажа каждого корпуса")
        else:
            st.info("Нет данных для отображения плана этажей")
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
