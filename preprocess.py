import pandas as pd
import re


# =========================================================
# CLEAN COLUMNS
# =========================================================
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    df.columns = (
        df.columns
        .astype(str)
        .str.replace("\n", " ", regex=False)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )

    return df


# =========================================================
# NORMALIZATION HELPERS
# =========================================================
def norm(x):
    return re.sub(r"\s+", " ", str(x).strip().lower())


# =========================================================
# FIND NIGHT SELECTIONS
# =========================================================
def extract_nights(row):

    nights = []

    for col in row.index:

        col_str = str(col).lower()
        val = row[col]

        if pd.isna(val):
            continue

        val = str(val).strip().lower()

        # нас интересуют только колонки проживания
        if "комната" not in col_str:
            continue

        # если отмечено проживание
        if val in ["", "нет", "0", "-", "false"]:
            continue

        # вытаскиваем номер ночи
        match = re.search(r"ночь на (\d+)", col_str)

        if match:
            nights.append(int(match.group(1)))

    return sorted(set(nights))


# =========================================================
# HARD GROUPS (REAL FIO MATCHING)
# =========================================================
def build_fio_index(df):

    return {
        norm(fio): fio
        for fio in df["ФИО"].fillna("")
    }


def extract_hard_groups(comment, fio_index):

    if not comment:
        return []

    text = norm(comment)

    result = []

    for fio_norm, fio_original in fio_index.items():

        # пробуем матч по фамилии + имени (основной кейс)
        parts = fio_norm.split()

        if len(parts) == 0:
            continue

        # минимум фамилия + имя
        key = " ".join(parts[:2])

        if key and key in text:
            result.append(fio_original)

    return result


# =========================================================
# GENDER (простая эвристика)
# =========================================================
def detect_gender(fio):

    parts = str(fio).strip().split()

    if not parts:
        return "M"

    name = parts[0].lower()

    return "F" if name.endswith(("а", "я")) else "M"


# =========================================================
# MAIN PREPROCESS
# =========================================================
def preprocess_guests(df: pd.DataFrame) -> pd.DataFrame:

    df = normalize_columns(df)

    processed = pd.DataFrame()

    # -----------------------------
    # FIO
    # -----------------------------
    processed["fio"] = df["ФИО"]

    # -----------------------------
    # gender
    # -----------------------------
    processed["gender"] = processed["fio"].apply(detect_gender)

    # -----------------------------
    # optional fields
    # -----------------------------
    processed["city"] = df.get("Город", "UNKNOWN")
    processed["status"] = df.get("Статус", "student")

    # -----------------------------
    # comments
    # -----------------------------
    processed["comment"] = df.get("Комментарий", "")

    # -----------------------------
    # nights (ВАЖНОЕ ИЗМЕНЕНИЕ)
    # -----------------------------
    processed["nights"] = df.apply(extract_nights, axis=1)

    # -----------------------------
    # HARD GROUPS (FIXED)
    # -----------------------------
    fio_index = build_fio_index(processed)

    processed["group_hard"] = processed["comment"].apply(
        lambda c: extract_hard_groups(c, fio_index)
    )

    return processed
