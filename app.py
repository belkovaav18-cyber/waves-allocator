import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
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
def extract_dates_from_guest(row, raw_df):
    """
    Извлекает даты заезда и отъезда для конкретного гостя.
    Возвращает (дата_заезда, дата_отъезда) в формате строки.
    """
    # Словарь для преобразования названий месяцев
    month_map = {
        "мая": 5, "июня": 6, "июля": 7, "августа": 8,
        "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
        "января": 1, "февраля": 2, "марта": 3, "апреля": 4
    }
    
    # Ищем колонки с комнатами
    room_columns = []
    for col in raw_df.columns:
        col_str = str(col)
        if "Комната" in col_str and "ночь" in col_str:
            room_columns.append(col)
    
    # Получаем ФИО гостя
    guest_fio = row.get("fio", "")
    
    # Находим строку с этим гостем в исходной таблице
    guest_row = None
    for idx, r in raw_df.iterrows():
        if r.get("ФИО") == guest_fio:
            guest_row = r
            break
    
    if guest_row is None:
        return "", ""
    
    # Собираем все ночи, которые гость отмечал
    selected_nights = []
    
    for col in room_columns:
        value = guest_row.get(col, "")
        if pd.notna(value) and str(value).strip().lower() not in ["", "нет", "-", "false"]:
            selected_nights.append(col)
    
    if not selected_nights:
        return "", ""
    
    # Сортируем ночи по дате
    def get_date_from_column(col_str):
        # Ищем "ночь на (число) (месяц)"
        match = re.search(r"ночь на (\d+) (\w+)", col_str)
        if match:
            day = int(match.group(1))
            month_name = match.group(2)
            month = month_map.get(month_name, 6)
            year = 2026  # или нужный год
            return datetime(year, month, day)
        return datetime.max
    
    sorted_nights = sorted(selected_nights, key=get_date_from_column)
    
    # Первая ночь = дата заезда (день до ночи)
    first_night_col = sorted_nights[0]
    match_first = re.search(r"ночь на (\d+) (\w+)", first_night_col)
    if match_first:
        day = int(match_first.group(1))
        month_name = match_first.group(2)
        month = month_map.get(month_name, 6)
        year = 2026
        # Заезд = день, когда ночуем (например, 31 мая для ночи на 1 июня)
        # Проверяем: если ночь на 1 июня, то заезд 31 мая
        if month == 6 and day == 1:
            check_in = datetime(year, 5, 31)
        elif month == 6 and day == 2:
            check_in = datetime(year, 6, 1)
        elif month == 6 and day == 3:
            check_in = datetime(year, 6, 2)
        elif month == 6 and day == 4:
            check_in = datetime(year, 6, 3)
        elif month == 6 and day == 5:
            check_in = datetime(year, 6, 4)
        else:
            check_in = datetime(year, month, day - 1)
        
        check_in_str = check_in.strftime("%d.%m.%Y")
    else:
        check_in_str = ""
    
    # Последняя ночь = дата отъезда (день после ночи)
    last_night_col = sorted_nights[-1]
    match_last = re.search(r"ночь на (\d+) (\w+)", last_night_col)
    if match_last:
        day = int(match_last.group(1))
        month_name = match_last.group(2)
        month = month_map.get(month_name, 6)
        year = 2026
        # Отъезд = день после ночи
        check_out = datetime(year, month, day + 1)
        check_out_str = check_out.strftime("%d.%m.%Y")
    else:
        check_out_str = ""
    
    return check_in_str, check_out_str


def get_dates_for_all_guests(guests_list, raw_df):
    """
    Добавляет даты заезда и отъезда к каждому гостю.
    Возвращает обновленный список гостей.
    """
    result = []
    for guest in guests_list:
        guest_copy = guest.copy()
        check_in, check_out = extract_dates_from_guest(guest, raw_df)
        guest_copy["Дата заезда"] = check_in
        guest_copy["Дата отъезда"] = check_out
        result.append(guest_copy)
    return result


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
    
    # Преобразуем результат в список словарей
    result_list = result.to_dict("records")
    
    # Добавляем даты заезда/отъезда для расселенных
    result_with_dates = get_dates_for_all_guests(result_list, raw)
    result_df = pd.DataFrame(result_with_dates)
    
    # Добавляем даты для нерезидентов
    non_residents_list = non_residents.to_dict("records")
    non_residents_with_dates = get_dates_for_all_guests(non_residents_list, raw)
    non_residents_result = pd.DataFrame(non_residents_with_dates)
    non_residents_result["room_id"] = "не проживает"
    
    # Объединяем
    final_result = pd.concat([result_df, non_residents_result], ignore_index=True)
    
    st.subheader("Result")
    st.dataframe(final_result)
    
    st.subheader("Debug")
    st.json(debug)
    
    # Сохраняем с тарифом и комментариями
    save_results_with_details(
        SHEET_ID, 
        "Result", 
        final_result, 
        raw
    )
    
    st.success("Готово")
