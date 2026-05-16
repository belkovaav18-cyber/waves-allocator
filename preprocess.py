import pandas as pd
import re
from datetime import datetime


# =========================================================
# helpers
# =========================================================
def normalize_name(name: str):
    return re.sub(r"\s+", " ", str(name).strip().lower())


def extract_hard_group(comment):
    """
    Явные требования: "Белоножко ДФ и Черновым АС"
    """
    if not comment:
        return []

    text = str(comment).lower()

    # ищем куски похожие на ФИО
    matches = re.findall(r"[а-яё]{4,}", text, re.IGNORECASE)

    stop = {
        "прошу", "поселить", "вместе", "пожалуйста",
        "спасибо", "меня", "моим", "соавтором"
    }

    names = []

    for m in matches:
        m = m.strip()
        if m in stop:
            continue
        if len(m) < 4:
            continue
        names.append(normalize_name(m))

    return list(set(names))


def extract_soft_group(comment):
    """
    "соавтор", "вместе с коллегой"
    """
    if not comment:
        return []

    text = str(comment).lower()

    soft_keywords = ["соавтор", "коллег", "вместе"]

    if any(k in text for k in soft_keywords):
        # мягкая связь, пока просто флаг
        return ["soft_link"]

    return []


# =========================================================
# core preprocess
# =========================================================
def preprocess_guests(df):

    df = df.copy()

    processed = pd.DataFrame()

    processed["fio"] = (
        df["Фамилия"].fillna("") + " " +
        df["Имя"].fillna("") + " " +
        df["Отчество"].fillna("")
    ).str.strip()

    processed["gender"] = df["Имя"].apply(
        lambda x: "F" if str(x).lower().strip().endswith(("а", "я")) else "M"
    )

    processed["birthdate"] = pd.to_datetime(df.get("Дата рождения"), errors="coerce")

    processed["checkin"] = pd.to_datetime(df.get("Заезд"), errors="coerce")
    processed["checkout"] = pd.to_datetime(df.get("Отъезд"), errors="coerce")

    processed["nights"] = df.get("Ночей", 0).fillna(0).astype(int)

    processed["city"] = df.get("Город", "UNKNOWN").fillna("UNKNOWN")

    processed["status"] = df.get("Статус", "student").fillna("student")

    processed["comment"] = df.get("Комментарий", "").fillna("")

    # =====================================================
    # GROUPS
    # =====================================================
    processed["group_hard"] = processed["comment"].apply(extract_hard_group)
    processed["group_soft"] = processed["comment"].apply(extract_soft_group)

    return processed
