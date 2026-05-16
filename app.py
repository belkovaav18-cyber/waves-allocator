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

    # safe call
    result, debug = smart_solve(
        guests_for_solver.to_dict("records"),
        rooms
    )

    # =====================================================
    # fallback safety
    # =====================================================
    if result is None:
        result = pd.DataFrame(columns=["fio", "room_id"])

    # =====================================================
    # NON-RESIDENTS
    # =====================================================
    non_residents_result = non_residents.copy()
    non_residents_result["room_id"] = "не проживает"

    # keep only needed columns safely
    non_residents_result = non_residents_result[["fio", "room_id"]]

    # =====================================================
    # FINAL MERGE
    # =====================================================
    final_result = pd.concat([result, non_residents_result], ignore_index=True)

    # =====================================================
    # UI
    # =====================================================
    st.subheader("Result")
    st.dataframe(final_result)

    st.subheader("Debug")
    st.json(debug)

    # =====================================================
    # SAVE
    # =====================================================
    save_results(SHEET_ID, "Result", final_result)

    st.success("Готово")
