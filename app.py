import streamlit as st

from allocator import allocate_rooms

from preprocess import preprocess_guests

from utils.excel_loader import (
    load_rooms,
    load_guests
)

st.set_page_config(
    page_title="Система расселения",
    layout="wide"
)

st.title("Система расселения")

rooms = load_rooms(
    "data/rooms.xlsx"
)

raw_guests = load_guests(
    "data/guests.xlsx"
)

guests = preprocess_guests(
    raw_guests
)

st.subheader("Комнаты")

st.dataframe(rooms)

st.subheader("Гости")

st.dataframe(guests)

if st.button("Авторасселение"):

    allocations = allocate_rooms(
        guests,
        rooms
    )

    st.subheader("Результат")

    st.dataframe(allocations)

    allocations.to_excel(
        "data/allocations.xlsx",
        index=False
    )

    st.success(
        "Расселение сохранено в data/allocations.xlsx"
    )
