import streamlit as st
import pandas as pd

from sheets import load_guests, save_results
from preprocess import preprocess_guests
from solver import solve


SHEET_ID = "1lF4SV24wTo5OwsidQ7UPqBVaGzdw_fBSx0OuBJJ4cWg"
TAB = "Sheet"

st.title("🏨 Расселение")

rooms = pd.read_excel("data/rooms.xlsx")

st.subheader("Комнаты")
st.dataframe(rooms)

raw = load_guests(SHEET_ID, TAB)
guests = preprocess_guests(raw)

st.subheader("Гости")
st.dataframe(guests)


if st.button("🚀 Расселить"):

    result = solve(guests, rooms)

    st.subheader("Result")
    st.dataframe(result)

    result.to_excel("data/result.xlsx", index=False)

    save_results(SHEET_ID, "Result", result)

    st.success("Готово")
