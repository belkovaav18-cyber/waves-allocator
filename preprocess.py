import pandas as pd
import re


NIGHT_MAP = {
    "31 мая": 31,
    "1 июня": 32,
    "2 июня": 33,
    "3 июня": 34,
    "4 июня": 35,
    "5 июня": 36,
}


def detect_gender(fio: str):
    if not fio:
        return "M"
    fio = fio.strip().lower()
    return "F" if fio.split()[0].endswith(("а", "я")) else "M"


def detect_status(text: str):
    if not text:
        return "student"
    t = str(text).lower()
    if "проф" in t:
        return "professor"
    return "student"


def extract_nights(row):
    """
    Берём все колонки вида:
    '31 мая / Комната (ночь ...)'
    """
    nights = []

    for col, val in row.items():
        if not isinstance(col, str):
            continue

        if "Комната" not in col:
            continue

        if pd.isna(val):
            continue

        for key, day in NIGHT_MAP.items():
            if key in col:
                nights.append(day)

    return sorted(set(nights))


def preprocess_guests(df: pd.DataFrame):

    df = df.copy()

    processed = []

    for _, row in df.iterrows():

        fio = row.get("ФИО")
        if pd.isna(fio):
            continue

        nights = extract_nights(row)

        if not nights:
            continue

        processed.append({
            "id": row.get("ID"),
            "fio": fio,
            "gender": detect_gender(fio),
            "status": detect_status(row.get("Статус") or row.get("Должность")),
            "city": str(row.get("Город", "UNKNOWN")),
            "nights": nights,
            "age": None,  # если появится дата рождения — легко добавить
            "raw": row.to_dict()
        })

    return pd.DataFrame(processed)
