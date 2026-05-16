import streamlit as st

from allocator import allocate_rooms

from preprocess import preprocess_guests


from utils.google_sheets import load_guests_from_gsheet
st.set_page_config(
    page_title="Система расселения",
    layout="wide"
)

st.title("Система расселения")

rooms = pd.read_excel("data/rooms.xlsx", engine="openpyxl")

raw_guests = load_guests_from_gsheet()

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
