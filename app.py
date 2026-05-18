import streamlit as st
import pandas as pd

from sheets import load_guests, save_results_with_details  # меняем импорт
from preprocess import preprocess_guests
from solver_controller import smart_solve


SHEET_ID = "1lF4SV24wTo5OwsidQ7UPqBVaGzdw_fBSx0OuBJJ4cWg"
TAB = "Sheet"

st.title("🏨 Расселение")

rooms_df = pd.read_excel("data/rooms.xlsx")
rooms = rooms_df.to_dict("records")

raw = load_guests(SHEET_ID, TAB)
guests_df = preprocess_guests(raw)

# -------------------------
# split
# -------------------------
non_residents = guests_df[guests_df["resident"] == False].copy()
residents = guests_df[guests_df["resident"] == True].copy()

st.subheader("Гости")
st.dataframe(guests_df)

if st.button("🚀 Расселить"):

    result, debug = smart_solve(
        residents.to_dict("records"),
        rooms
    )

    # add non-residents
    non_residents_result = non_residents.copy()
    non_residents_result["room_id"] = "не проживает"

    final_result = pd.concat([
        result,
        non_residents_result[["fio", "room_id"]]
    ])

    st.subheader("Result")
    st.dataframe(final_result)

    st.subheader("Debug")
    st.json(debug)

    # Сохраняем с тарифом и комментариями
    save_results_with_details(
        SHEET_ID, 
        "Result", 
        final_result, 
        raw  # передаем исходную таблицу с тарифом и комментариями
    )

    st.success("Готово")
