import pandas as pd
from datetime import datetime


def detect_gender(name):
    if pd.isna(name):
        return "M"

    name = str(name).strip().lower()
    return "F" if name.endswith(("а", "я")) else "M"


def calculate_age(birthdate):
    if pd.isna(birthdate):
        return None

    today = datetime.today()

    return (
        today.year
        - birthdate.year
        - ((today.month, today.day) < (birthdate.month, birthdate.day))
    )


def detect_city(row):
    city = row.get("Город")
    if pd.isna(city):
        return "UNKNOWN"
    return str(city).strip()


def detect_status(row):
    status = row.get("Должность") or row.get("Статус")

    if pd.isna(status):
        return "student"

    status = str(status).lower()
    if "проф" in status or "prof" in status:
        return "professor"

    return "student"


def detect_family(row):
    last = str(row.get("Фамилия", "")).strip().lower()
    if not last:
        return None
    return last


def preprocess_guests(df):
    df = df.copy()

    df = df[df["Заезд"].notna()].copy()

    processed = pd.DataFrame()

    processed["fio"] = (
        df["Фамилия"].fillna("") + " " +
        df["Имя"].fillna("") + " " +
        df["Отчество"].fillna("")
    ).str.strip()

    processed["gender"] = df["Имя"].apply(detect_gender)

    processed["birthdate"] = pd.to_datetime(df["Дата рождения"], errors="coerce")
    processed["age"] = processed["birthdate"].apply(calculate_age)

    processed["checkin"] = pd.to_datetime(df["Заезд"], errors="coerce")
    processed["checkout"] = pd.to_datetime(df["Отъезд"], errors="coerce")

    processed["nights"] = pd.to_numeric(df["Ночей"], errors="coerce").fillna(0).astype(int)

    processed["city"] = df.apply(detect_city, axis=1)
    processed["status"] = df.apply(detect_status, axis=1)
    processed["family_id"] = df.apply(detect_family, axis=1)

    return processed
