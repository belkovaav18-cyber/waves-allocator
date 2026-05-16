import streamlit as st
import pandas as pd

from sheets import load_guests, save_results
from preprocess import preprocess_guests
from solver_controller import smart_solve

SHEET_ID = "1lF4SV24wTo5OwsidQ7UPqBVaGzdw_fBSx0OuBJJ4cWg"
TAB = "Sheet"

st.title("🏨 Расселение")

# =========================================================
# ROOMS
# =========================================================
rooms_df = pd.read_excel("data/rooms.xlsx")
rooms = rooms_df.to_dict("records")

st.subheader("Комнаты")
st.dataframe(rooms_df)

# =========================================================
# GUESTS
# =========================================================
raw = load_guests(SHEET_ID, TAB)
guests_df = preprocess_guests(raw)

non_residents = guests_df[guests_df["resident"] == False].copy()
guests_for_solver = guests_df[guests_df["resident"] == True].copy()

st.subheader("Гости (все)")
st.dataframe(guests_df)

# =========================================================
# SOLVE
# =========================================================
if st.button("🚀 Расселить"):

    result, debug = smart_solve(
        guests_df.to_dict("records"),
        rooms
    )

    non_res = guests_df[~guests_df["resident"]].copy()
    non_res["room_id"] = "не проживает"

    final_result = pd.concat([
        result,
        non_res[["fio", "room_id"]]
    ], ignore_index=True)

    st.dataframe(final_result)

    save_results(SHEET_ID, "Result", final_result)

    st.success("Готово")
