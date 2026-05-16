import streamlit as st
import pandas as pd

from sheets import load_guests, save_results
from preprocess import preprocess
from solver import solve

SHEET_ID = "1lF4SV24wTo5OwsidQ7UPqBVaGzdw_fBSx0OuBJJ4cWg"
TAB = "Sheet"

raw = load_guests(SHEET_ID, TAB)



st.title("🏨 OR-Tools расселение")

rooms = pd.read_excel("data/rooms.xlsx")


guests = preprocess(raw)

st.subheader("Гости")
st.dataframe(guests)

if st.button("🚀 Оптимизировать расселение"):

    result = solve(guests, rooms)

    st.subheader("Результат")
    st.dataframe(result)

    result.to_excel("data/output.xlsx", index=False)

    try:
        save_results("Result", result)
        st.success("Сохранено в Google Sheets")
    except Exception as e:
        st.error(str(e))
