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
    """
    Извлекает даты заезда и отъезда для конкретного гостя по ФИО.
    Возвращает (дата_заезда, дата_отъезда) в формате строки.
    """
    month_map = {
        "мая": 5, "июня": 6, "июля": 7, "августа": 8,
        "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
        "января": 1, "февраля": 2, "марта": 3, "апреля": 4
    }
    
    # Находим строку с этим гостем
    guest_row = None
    for idx, row in raw_df.iterrows():
        if row.get("ФИО") == guest_fio:
            guest_row = row
            break
    
    if guest_row is None:
        return "", ""
    
    # Собираем все ночи, которые гость отмечал
    selected_nights = []
    
    for col in raw_df.columns:
        col_str = str(col)
        if "Комната" in col_str and "ночь" in col_str:
            value = guest_row.get(col, "")
            if pd.notna(value) and str(value).strip().lower() not in ["", "нет", "-", "false", "nan"]:
                selected_nights.append(col_str)
    
    if not selected_nights:
        return "", ""
    
    # Функция для извлечения даты из названия колонки
    def get_date_from_column(col_str):
        match = re.search(r"ночь на (\d+) (\w+)", col_str)
        if match:
            day = int(match.group(1))
            month_name = match.group(2)
            month = month_map.get(month_name, 6)
            return (month, day)
        return (99, 99)
    
    # Сортируем ночи по дате
    selected_nights.sort(key=get_date_from_column)
    
    # Первая ночь = дата заезда
    first_night = selected_nights[0]
    match_first = re.search(r"ночь на (\d+) (\w+)", first_night)
    if match_first:
        day = int(match_first.group(1))
        month_name = match_first.group(2)
        month = month_map.get(month_name, 6)
        year = 2026
        
        # Заезд = день до ночи (если ночь на 1 июня, заезд 31 мая)
        if month == 6 and day == 1:
            check_in = datetime(year, 5, 31)
        else:
            check_in = datetime(year, month, day - 1)
        check_in_str = check_in.strftime("%d.%m.%Y")
    else:
        check_in_str = ""
    
    # Последняя ночь = дата отъезда
    last_night = selected_nights[-1]
    match_last = re.search(r"ночь на (\d+) (\w+)", last_night)
    if match_last:
        day = int(match_last.group(1))
        month_name = match_last.group(2)
        month = month_map.get(month_name, 6)
        year = 2026
        check_out = datetime(year, month, day + 1)
        check_out_str = check_out.strftime("%d.%m.%Y")
    else:
        check_out_str = ""
    
    return check_in_str, check_out_str


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
    
    # Добавляем даты заезда/отъезда к результату
    result_with_dates = []
    for _, row in result.iterrows():
        guest_data = row.to_dict()
        check_in, check_out = extract_dates_from_guest(guest_data["fio"], raw)
        guest_data["Дата заезда"] = check_in
        guest_data["Дата отъезда"] = check_out
        result_with_dates.append(guest_data)
    
    result_df = pd.DataFrame(result_with_dates)
    
    # Обрабатываем нерезидентов
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
    
    # Выбираем нужные колонки для отображения
    display_columns = ['fio', 'room_id', 'room_capacity', 'Дата заезда', 'Дата отъезда']
    existing_display = [col for col in display_columns if col in final_result.columns]
    
    st.subheader("Результат расселения")
    st.dataframe(final_result[existing_display])
    
    st.subheader("Debug информация")
    st.json(debug)
    
    # Сохраняем в Google Sheets (добавит тариф и комментарий автоматически)
    save_results_with_details(
        SHEET_ID, 
        "Result", 
        final_result, 
        raw
    )
    
    st.success("✅ Готово! Результат сохранен в Google Sheets")
