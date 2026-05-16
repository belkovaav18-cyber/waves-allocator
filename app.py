import streamlit as st
import pandas as pd

from allocator import allocate_rooms, build_room_stats
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
# STATE
# =========================
if "allocations" not in st.session_state:
    st.session_state.allocations = None

if "rejections" not in st.session_state:
    st.session_state.rejections = None


# =========================
# BUTTON
# =========================
if st.button("Авторасселение"):

    allocations, rejections = allocate_rooms(
      guests.to_dict("records"),
      rooms.to_dict("records")
  )

room_stats = build_room_stats(allocations, rooms)

    st.session_state.allocations = allocations
    st.session_state.rejections = rejections

    st.subheader("Результат")
    st.dataframe(allocations)

    # save google sheets
    try:
        save_allocations_to_gsheet(allocations)
        st.success("Сохранено в Google Sheets")
    except Exception as e:
        st.error(f"Google Sheets ошибка: {e}")

    # save local
    try:
        allocations.to_excel("data/allocations.xlsx", index=False)
        st.success("Сохранено в Excel")
    except Exception as e:
        st.warning(f"Excel ошибка: {e}")


# =========================
# SHOW REJECTIONS
# =========================
if st.session_state.rejections is not None:

    st.subheader("❌ Не заселены")

    st.dataframe(st.session_state.rejections)

    for r in st.session_state.rejections.to_dict("records"):
        st.write("—")
        st.write(f"👤 {r['fio']}")
        st.write("Причины:")
        for reason in r["reasons"]:
            st.write(f"• {reason}")


# =========================
# LAST RESULT
# =========================
if st.session_state.allocations is not None:
    st.subheader("Последнее расселение")
    st.dataframe(st.session_state.allocations)
    st.subheader("🏨 Загруженность комнат")

    st.dataframe(room_stats)

    st.bar_chart(room_stats.set_index("room_id")["occupied"])
