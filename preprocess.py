import pandas as pd

from datetime import datetime


def detect_gender(name):

    if pd.isna(name):
        return "M"

    name = str(name).strip().lower()

    female_endings = ["а", "я"]

    if name.endswith(tuple(female_endings)):
        return "F"

    return "M"


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


def preprocess_guests(df):

    df = df[df["Заезд"].notna()]

    processed = pd.DataFrame()

    processed["fio"] = (
        df["Фамилия"].fillna("")
        + " "
        + df["Имя"].fillna("")
        + " "
        + df["Отчество"].fillna("")
    )

    processed["gender"] = df["Имя"].apply(
        detect_gender
    )

    processed["birthdate"] = pd.to_datetime(
        df["Дата рождения"],
        errors="coerce"
    )

    processed["age"] = processed[
        "birthdate"
    ].apply(calculate_age)

    processed["checkin"] = df["Заезд"]

    processed["checkout"] = df["Отъезд"]

    processed["nights"] = df["Ночей"]

    return processed
