import streamlit as st
import pandas as pd
from datetime import datetime
import re
import io
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

from sheets import load_guests, save_results_with_details, load_registration_data
from preprocess import preprocess_guests
from solver_controller import smart_solve
from comment_engine import process_comments, display_comments_report
from feasibility import check_feasibility, display_feasibility_report

SHEET_ID = "1lF4SV24wTo5OwsidQ7UPqBVaGzdw_fBSx0OuBJJ4cWg"
REGISTRATION_SHEET_ID = "1fHjI0hTtlbjDZxSCWVidzGnJ7aY4joB7UUVXFEB0rxw"
TAB_NAME = "Sheet"

st.set_page_config(page_title="Система расселения", layout="wide")
st.title("🏨 Система расселения в Доме отдыха")

# Session state
if 'layout' not in st.session_state:
    st.session_state.layout = None
if 'final_result_df' not in st.session_state:
    st.session_state.final_result_df = None
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

# Загрузка комнат
try:
    rooms_df = pd.read_excel("data/rooms.xlsx")
    rooms = rooms_df.to_dict("records")
    st.success(f"✅ Загружено {len(rooms)} комнат")
except Exception as e:
    st.error(f"❌ Ошибка загрузки комнат: {e}")
    st.stop()

# Загрузка данных
if not st.session_state.data_loaded:
    with st.spinner("Загрузка данных..."):
        raw = load_guests(SHEET_ID, TAB_NAME)
        registration_df = load_registration_data(REGISTRATION_SHEET_ID, TAB_NAME)
        if raw.empty:
            st.error("❌ Не удалось загрузить данные")
            st.stop()
        guests_df = preprocess_guests(raw, registration_df)
        st.session_state.raw = raw
        st.session_state.guests_df = guests_df
        st.session_state.data_loaded = True
else:
    raw = st.session_state.raw
    guests_df = st.session_state.guests_df

def fix_df(df):
    if df is None or df.empty:
        return df
    df = df.copy()
    for col in df.columns:
        if col in ['возраст', 'тариф', 'число_ночей', 'стоимость', 'room_capacity']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        else:
            df[col] = df[col].astype(str).replace('nan', '').replace('None', '')
    return df

# Разделяем
non_residents = guests_df[guests_df["resident"] == False].copy()
residents = guests_df[guests_df["resident"] == True].copy()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Всего гостей", len(guests_df))
with col2:
    st.metric("Резиденты", len(residents))
with col3:
    st.metric("Нерезиденты", len(non_residents))

# Кнопка расселения
if st.button("🚀 Расселить", type="primary", width="stretch"):
    with st.spinner("Идет расселение..."):
        result, debug = smart_solve(residents.to_dict("records"), rooms)
    
    if "error" in result.columns:
        st.error(f"❌ Ошибка: {result.iloc[0]['error']}")
        st.stop()
    
    if len(result) == 0:
        st.error("❌ Не удалось найти решение")
        st.stop()
    
    st.session_state.final_result_df = result
    st.success("✅ Расселение выполнено!")
    st.rerun()

# Отображение результатов
if st.session_state.final_result_df is not None:
    st.subheader("📋 Результат расселения")
    st.dataframe(fix_df(st.session_state.final_result_df), width="stretch")
    
    csv = st.session_state.final_result_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Скачать CSV", csv, "raselenie.csv", "text/csv")
