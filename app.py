import streamlit as st
import pandas as pd

from allocator import allocate_rooms
from preprocess import preprocess_guests
from utils.google_sheets import (
    load_guests_from_gsheet,
    save_allocations_to_gsheet
)

st.set_page_config(
    page_title="Система расселения",
    layout="wide"
)

st.title("Система расселения")

# =========================
# LOAD DATA
# =========================
rooms = pd.read_excel("data/rooms.xlsx", engine="openpyxl")

raw_guests = load_guests_from_gsheet()
guests = preprocess_guests(raw_guests)

st.subheader("Комнаты")
st.dataframe(rooms)

st.subheader("Гости")
st.dataframe(guests)

# =========================
# STATE (ВАЖНО для Streamlit)
# =========================
if "allocations" not in st.session_state:
    st.session_state.allocations = None

# =========================
# BUTTON
# =========================
if st.button("Авторасселение"):

    allocations = allocate_rooms(
     guests,
     rooms
 )

    st.session_state.allocations = allocations

    st.subheader("Результат")
    st.dataframe(allocations)

    # save to Google Sheets
    try:
        save_allocations_to_gsheet(allocations)
        st.success("Сохранено в Google Sheets")
    except Exception as e:
        st.error(f"Ошибка сохранения в Google Sheets: {e}")

    # save local excel (safe for cloud)
    try:
        allocations.to_excel("data/allocations.xlsx", index=False)
        st.success("Сохранено в Excel")
    except Exception as e:
        st.warning(f"Excel не сохранён: {e}")

# =========================
# SHOW LAST RESULT
# =========================
if st.session_state.allocations is not None:
    st.subheader("Последнее расселение")
    st.dataframe(st.session_state.allocations)
