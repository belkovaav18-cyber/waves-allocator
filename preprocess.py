import pandas as pd
import re


# =========================================================
# CLEAN
# =========================================================
def normalize_columns(df):
    df = df.copy()
    df.columns = (
        df.columns
        .astype(str)
        .str.replace("\n", " ", regex=False)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )
    return df


def norm(x):
    return re.sub(r"\s+", " ", str(x).strip().lower())


# =========================================================
# NIGHTS (из чекбоксов)
# =========================================================
def extract_nights(row):

    nights = []

    for col in row.index:

        col_str = str(col).lower()
        val = row[col]

        if pd.isna(val):
            continue

        val = str(val).strip().lower()

        if "комната" not in col_str:
            continue

        if val in ["", "нет", "0", "-", "false"]:
            continue

        match = re.search(r"ночь на (\d+)", col_str)

        if match:
            nights.append(int(match.group(1)))

    return sorted(set(nights))


# =========================================================
# HARD GROUPS (через реальные ФИО)
# =========================================================
def build_fio_index(df):
    return {
        norm(fio): fio
        for fio in df["fio"].fillna("")
    }


def extract_hard_groups(comment, fio_index):

    if not comment:
        return []

    text = norm(comment)

    result = []

    for fio_norm, fio_original in fio_index.items():

        # матч по фамилии + имени
        parts = fio_norm.split()

        if len(parts) < 2:
            continue

        key = " ".join(parts[:2])

        if key in text:
            result.append(fio_original)

    return result


# =========================================================
# GENDER
# =========================================================
def detect_gender(fio):

    parts = str(fio).split()
    if not parts:
        return "M"

    return "F" if parts[0].lower().endswith(("а", "я")) else "M"


# =========================================================
# MAIN
# =========================================================
def preprocess_guests(df):

    df = normalize_columns(df)

    processed = pd.DataFrame()

    # -------------------------
    # FIO (ВАЖНО: сразу норм)
    # -------------------------
    processed["fio"] = df["ФИО"]

    # -------------------------
    # meta
    # -------------------------
    processed["gender"] = processed["fio"].apply(detect_gender)

    processed["city"] = df.get("Город", "UNKNOWN")
    processed["status"] = df.get("Статус", "student")

    processed["comment"] = df.get("Комментарий", "")

    # -------------------------
    # nights
    # -------------------------
    processed["nights"] = df.apply(extract_nights, axis=1)

    # -------------------------
    # HARD GROUPS
    # -------------------------
    fio_index = build_fio_index(processed)

    processed["group_hard"] = processed["comment"].apply(
        lambda c: extract_hard_groups(c, fio_index)
    )

    # soft groups пока выключаем (можно расширить позже)
    processed["group_soft"] = [[] for _ in range(len(processed))]

    return processed
