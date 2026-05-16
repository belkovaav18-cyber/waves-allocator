import streamlit as st
import pandas as pd

from allocator import allocate_rooms, build_room_stats
from preprocess import preprocess_guests
from utils.google_sheets import load_guests_from_gsheet, save_allocations_to_gsheet


st.set_page_config(page_title="Расселение", layout="wide")

st.title("🏨 Система расселения")


rooms = pd.read_excel("data/rooms.xlsx", engine="openpyxl")

raw = load_guests_from_gsheet()
guests = preprocess_guests(raw)


st.subheader("Гости (после парсинга)")
st.dataframe(guests)


if st.button("Авторасселение"):

    allocations, rejections, room_state = allocate_rooms(
        guests.to_dict("records"),
        rooms.to_dict("records")
    )

    stats = build_room_stats(room_state)

    st.subheader("📊 Расселение")
    st.dataframe(allocations)

    st.subheader("❌ Не заселены")
    st.dataframe(rejections)

    st.subheader("🏨 Статистика комнат")
    st.dataframe(stats)

    try:
        save_allocations_to_gsheet(allocations)
        st.success("Сохранено в Google Sheets")
    except Exception as e:
        st.error(str(e))
