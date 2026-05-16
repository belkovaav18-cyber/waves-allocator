import streamlit as st
import pandas as pd

from sheets import load_guests, save_results
from preprocess import preprocess_guests
from solver import solve

SHEET_ID = "1lF4SV24wTo5OwsidQ7UPqBVaGzdw_fBSx0OuBJJ4cWg"
TAB = "Sheet"

st.title("🏨 Расселение")

rooms_df = pd.read_excel("data/rooms.xlsx")
rooms = rooms_df.to_dict("records")

raw = load_guests(SHEET_ID, TAB)
guests_df = preprocess_guests(raw)

st.subheader("Гости")
st.dataframe(guests_df)

if st.button("🚀 Расселить"):

    result = solve(
        guests_df.to_dict("records"),
        rooms
    )

    st.subheader("Result")
    st.dataframe(result)

    save_results(SHEET_ID, "Result", result)

    st.success("Готово")
