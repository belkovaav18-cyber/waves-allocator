import pandas as pd
from datetime import datetime


# =========================
# GENDER
# =========================
def detect_gender(name):

    if pd.isna(name):
        return "M"

    name = str(name).strip().lower()

    female_endings = ["а", "я"]

    if name.endswith(tuple(female_endings)):
        return "F"

    return "M"


# =========================
# AGE
# =========================
def calculate_age(birthdate):

    if pd.isna(birthdate):
        return None

    today = datetime.today()

    return (
        today.year
        - birthdate.year
        - (
            (today.month, today.day)
            < (birthdate.month, birthdate.day)
        )
    )


# =========================
# CITY (очень важно для твоих правил)
# =========================
def detect_city(row):

    # если в таблице есть колонка "Город"
    city = row.get("Город")

    if pd.isna(city):
        return "UNKNOWN"

    return str(city).strip()


# =========================
# STATUS (student / professor)
# =========================
def detect_status(row):

    # если есть явная колонка
    status = row.get("Статус")

    if pd.isna(status):
        return "student"

    status = str(status).strip().lower()

    if "проф" in status or "prof" in status:
        return "professor"

    return "student"


# =========================
# FAMILY ID (по фамилии)
# =========================
def detect_family(row):

    last = str(row.get("Фамилия", "")).strip().lower()
    first = str(row.get("Имя", "")).strip().lower()

    if not last:
        return None

    return last  # можно усложнить позже


# =========================
# MAIN
# =========================
def preprocess_guests(df):

    # убираем тех, у кого нет заезда
    df = df[df["Заезд"].notna()].copy()

    processed = pd.DataFrame()

    # =====================
    # FIO
    # =====================
    processed["fio"] = (
        df["Фамилия"].fillna("")
        + " "
        + df["Имя"].fillna("")
        + " "
        + df["Отчество"].fillna("")
    ).str.strip()

    # =====================
    # GENDER
    # =====================
    processed["gender"] = df["Имя"].apply(detect_gender)

    # =====================
    # BIRTHDATE + AGE
    # =====================
    processed["birthdate"] = pd.to_datetime(
        df["Дата рождения"],
        errors="coerce"
    )

    processed["age"] = processed["birthdate"].apply(calculate_age)

    # =====================
    # DATES
    # =====================
    processed["checkin"] = pd.to_datetime(df["Заезд"], errors="coerce")
    processed["checkout"] = pd.to_datetime(df["Отъезд"], errors="coerce")
    processed["nights"] = pd.to_numeric(df["Ночей"], errors="coerce").fillna(0).astype(int)

    # =====================
    # NEW FIELDS FOR YOUR ALGORITHM
    # =====================
    processed["city"] = df.apply(detect_city, axis=1)
    processed["status"] = df.apply(detect_status, axis=1)
    processed["family_id"] = df.apply(detect_family, axis=1)

    return processed
