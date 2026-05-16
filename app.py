import streamlit as st
import pandas as pd

from sheets import load_guests, save_results
from preprocess import preprocess_guests
from solver_controller import smart_solve

SHEET_ID = "1lF4SV24wTo5OwsidQ7UPqBVaGzdw_fBSx0OuBJJ4cWg"
TAB = "Sheet"

st.title("🏨 Расселение")

rooms_df = pd.read_excel("data/rooms.xlsx")
rooms = rooms_df.to_dict("records")

st.subheader("Комнаты")
st.dataframe(rooms_df)

raw = load_guests(SHEET_ID, TAB)
guests_df = preprocess_guests(raw)
non_residents = guests_df[guests_df["resident"] == False]
guests_for_solver = guests_df[guests_df["resident"] == True]

st.subheader("Гости")
st.dataframe(guests_df)

if st.button("🚀 Расселить"):

    result, debug = smart_solve(
        guests_df.to_dict("records"),
        rooms
    )

    st.subheader("Result")
    st.dataframe(result)

    st.subheader("Debug")
    st.json(debug)

    save_results(SHEET_ID, "Result", result)
    st.success("Готово")
