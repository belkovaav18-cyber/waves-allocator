import streamlit as st
import pandas as pd

from sheets import load_guests, save_results
from preprocess import preprocess
from solver import solve


SHEET_ID = "1lF4SV24wTo5OwsidQ7UPqBVaGzdw_fBSx0OuBJJ4cWg"
TAB = "Sheet"

st.set_page_config(layout="wide")

st.title("🏨 Система расселения")


# ---------------------------------------------------
# LOAD ROOMS
# ---------------------------------------------------
rooms = pd.read_excel(
    "data/rooms.xlsx",
    engine="openpyxl"
)

st.subheader("Комнаты")
st.dataframe(rooms)


# ---------------------------------------------------
# LOAD GUESTS
# ---------------------------------------------------
raw = load_guests(SHEET_ID, TAB)

guests = preprocess(raw)

st.subheader("Гости")
st.dataframe(guests)


# ---------------------------------------------------
# BUTTON
# ---------------------------------------------------
if st.button("🚀 Расселить"):

    try:

        result = solve(guests, rooms)

        st.subheader("Result")

        st.dataframe(result)

        # -----------------------------------------
        # excel
        # -----------------------------------------
        result.to_excel(
            "data/result.xlsx",
            index=False
        )

        # -----------------------------------------
        # google sheets
        # -----------------------------------------
        save_results(
            SHEET_ID,
            "Result",
            result
        )

        st.success("Готово")

    except Exception as e:

        st.exception(e)
