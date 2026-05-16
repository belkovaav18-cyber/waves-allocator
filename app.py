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

st.subheader("Комнаты")
st.dataframe(rooms_df)

raw = load_guests(SHEET_ID, TAB)
guests_df = preprocess_guests(raw)

non_residents = guests_df[guests_df["resident"] == False].copy()
guests_for_solver = guests_df[guests_df["resident"] == True].copy()

st.subheader("Гости")
st.dataframe(guests_df)

if st.button("🚀 Расселить"):

    result = solve(
        guests_for_solver.to_dict("records"),
        rooms
    )

    non_res = non_residents.copy()
    non_res["room_id"] = "не проживает"

    final_result = pd.concat([
        result,
        non_res[["fio", "room_id"]]
    ])

    st.subheader("Result")
    st.dataframe(final_result)

    save_results(SHEET_ID, "Result", final_result)

    st.success("Готово")
