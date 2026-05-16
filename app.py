import streamlit as st
import pandas as pd

from sheets import load_guests, save_results
from preprocess import preprocess_guests
from solver import solve


SHEET_ID = "1lF4SV24wTo5OwsidQ7UPqBVaGzdw_fBSx0OuBJJ4cWg"
TAB = "Sheet"

st.title("🏨 Расселение")

rooms = pd.read_excel("data/rooms.xlsx")
rooms = rooms.to_dict("records")

st.subheader("Комнаты")
st.dataframe(rooms)

raw = load_guests(SHEET_ID, TAB)
guests = preprocess_guests(raw).to_dict("records")

st.subheader("Гости")
st.dataframe(guests)


if st.button("🚀 Расселить"):

    from solver_controller import smart_solve


    result, debug = smart_solve(guests, rooms)

    st.subheader("Result")
    st.dataframe(result)

    result.to_excel("data/result.xlsx", index=False)

    save_results(SHEET_ID, "Result", result)

    st.success("Готово")
    st.subheader("🧠 Debug system")

    st.json(debug)

    st.subheader("⚠️ Невозможные группы")
    st.write(debug["impossible_groups"])

    st.subheader("❌ Причины незаселения")
    st.write(debug["unplaced_reasons"])
