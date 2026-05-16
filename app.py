import streamlit as st
import pandas as pd

from sheets import load_guests, load_rooms, save_results
from preprocess import preprocess_guests
from solver_controller import smart_solve


# =========================
# CONFIG
# =========================
SHEET_ID = "1lF4SV24wTo5OwsidQ7UPqBVaGzdw_fBSx0OuBJJ4cWg"
TAB_GUESTS = "Sheet"
TAB_ROOMS = "Rooms"


st.title("🏨 Расселение")


# =========================
# LOAD DATA
# =========================
raw_guests = load_guests(SHEET_ID, TAB_GUESTS)
raw_rooms = load_rooms(SHEET_ID, TAB_ROOMS)


# =========================
# PREPROCESS
# =========================
guests_df = preprocess_guests(raw_guests)
guests = guests_df.to_dict("records")

rooms_df = pd.read_excel("data/rooms.xlsx")
rooms = rooms_df.to_dict("records")


# =========================
# PREVIEW
# =========================
st.subheader("Комнаты")
st.dataframe(rooms_df)

st.subheader("Гости")
st.dataframe(guests_df)


# =========================
# RUN
# =========================
if st.button("🚀 Расселить"):

    result, debug = smart_solve(guests, rooms)

    st.subheader("Result")

    if result is None or len(result) == 0:
        st.error("Нет решения")
    else:
        st.dataframe(result)

        # save local
        result.to_excel("data/result.xlsx", index=False)

        # save to sheets
        save_results(SHEET_ID, "Result", result)

        st.success("Готово")


    # =========================
    # DEBUG PANEL
    # =========================
    st.subheader("🧠 Debug system")
    st.json(debug)


    # =========================
    # PROBLEMS
    # =========================
    st.subheader("⚠️ Невозможные группы")
    st.write(debug.get("impossible_groups", []))


    st.subheader("❌ Причины незаселения")
    st.write(debug.get("fail_reasons", []))
