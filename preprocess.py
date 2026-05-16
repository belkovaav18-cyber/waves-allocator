import pandas as pd
import re
from datetime import datetime


# =========================================================
# SAFE COLUMNS NORMALIZATION
# =========================================================
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    df.columns = (
        df.columns
        .astype(str)
        .str.replace("\n", " ", regex=False)   # убираем переносы строк
        .str.replace("\ufeff", "", regex=False) # BOM
        .str.strip()                           # пробелы
    )

    return df


# =========================================================
# SMART COLUMN FINDER
# =========================================================
def find_col(df, keywords):

    """
    ищет колонку по ключевым словам
    """
    for col in df.columns:
        col_low = col.lower()
        if all(k.lower() in col_low for k in keywords):
            return col
    return None


# =========================================================
# GENDER DETECT
# =========================================================
def detect_gender(name):

    if pd.isna(name):
        return "M"

    name = str(name).strip().lower()

    return "F" if name.endswith(("а", "я")) else "M"


# =========================================================
# GROUP PARSER (hard groups from comments)
# =========================================================
def extract_hard_group(comment):

    if not comment:
        return []

    text = str(comment).lower()

    # ищем все слова похожие на ФИО / фамилии
    names = re.findall(r"[а-яё]{4,}", text, re.IGNORECASE)

    stop = {
        "прошу", "поселить", "вместе", "пожалуйста",
        "спасибо", "меня", "моим", "соавтором", "пожалуйста"
    }

    cleaned = []

    for n in names:
        n = n.strip()

        if n in stop:
            continue

        if len(n) < 4:
            continue

        cleaned.append(n.lower())

    return list(set(cleaned))


# =========================================================
# MAIN PREPROCESS
# =========================================================
def preprocess_guests(df):

    df = df.copy()

    # -----------------------------
    # 1. clean columns
    # -----------------------------
    df = normalize_columns(df)

    # -----------------------------
    # 2. find columns safely
    # -----------------------------
    col_fio = find_col(df, ["фио"])
    col_last = find_col(df, ["фам"])
    col_first = find_col(df, ["имя"])
    col_mid = find_col(df, ["отч"])
    col_city = find_col(df, ["город"])
    col_status = find_col(df, ["стат"])
    col_comment = find_col(df, ["коммент"])
    col_birth = find_col(df, ["рожд"])
    col_checkin = find_col(df, ["заезд"])
    col_checkout = find_col(df, ["отъезд"])
    col_nights = find_col(df, ["ноч"])

    # -----------------------------
    # 3. build FIO safely
    # -----------------------------
    if col_fio:
        fio = df[col_fio]
    else:
        last = df[col_last] if col_last else ""
        first = df[col_first] if col_first else ""
        mid = df[col_mid] if col_mid else ""

        fio = (
            last.fillna("") + " " +
            first.fillna("") + " " +
            mid.fillna("")
        ).str.strip()

    processed = pd.DataFrame()
    processed["fio"] = fio

    # -----------------------------
    # 4. gender
    # -----------------------------
    if col_first:
        processed["gender"] = df[col_first].apply(detect_gender)
    else:
        processed["gender"] = "M"

    # -----------------------------
    # 5. city / status
    # -----------------------------
    processed["city"] = df[col_city] if col_city else "UNKNOWN"
    processed["status"] = df[col_status] if col_status else "student"

    # -----------------------------
    # 6. dates
    # -----------------------------
    processed["checkin"] = pd.to_datetime(
        df[col_checkin], errors="coerce"
    ) if col_checkin else None

    processed["checkout"] = pd.to_datetime(
        df[col_checkout], errors="coerce"
    ) if col_checkout else None

    # -----------------------------
    # 7. nights
    # -----------------------------
    if col_nights:
        processed["nights"] = pd.to_numeric(
            df[col_nights],
            errors="coerce"
        ).fillna(0).astype(int)
    else:
        processed["nights"] = 0

    # -----------------------------
    # 8. comments
    # -----------------------------
    processed["comment"] = df[col_comment] if col_comment else ""

    # -----------------------------
    # 9. groups
    # -----------------------------
    processed["group_hard"] = processed["comment"].apply(extract_hard_group)

    return processed
