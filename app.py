import streamlit as st
import pandas as pd

from allocator import allocate_rooms, build_room_stats
from preprocess import preprocess_guests
from utils.google_sheets import load_guests_from_gsheet


st.set_page_config(page_title="Расселение", layout="wide")

st.title("🏨 Авторасселение")

rooms = pd.read_excel("data/rooms.xlsx")

raw = load_guests_from_gsheet()
guests = preprocess_guests(raw)

st.subheader("Гости")
st.dataframe(guests)

if st.button("Расселить"):

    allocations, rejections, state = allocate_rooms(
        guests.to_dict("records"),
        rooms.to_dict("records")
    )

    st.subheader("Расселение")
    st.dataframe(allocations)

    st.subheader("Отказы")
    st.dataframe(rejections)

    st.subheader("Комнаты")
    st.dataframe(build_room_stats(state))
