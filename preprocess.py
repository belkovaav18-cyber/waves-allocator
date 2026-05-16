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
# NIGHTS
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
# GENDER
# =========================================================
def detect_gender(fio):

    parts = str(fio).split()
    if not parts:
        return "M"

    return "F" if parts[0].lower().endswith(("а", "я")) else "M"


# =========================================================
# HARD GROUPS (упрощённо пока)
# =========================================================
def extract_hard_groups(comment):
    return []


# =========================================================
# RESIDENT PARSING (ВАЖНО)
# =========================================================
def parse_resident(value):

    if pd.isna(value):
        return True

    v = str(value).strip().lower()

    if "не буду" in v or "не прожива" in v:
        return False

    return True


# =========================================================
# MAIN
# =========================================================
def preprocess_guests(df):

    df = normalize_columns(df)

    processed = pd.DataFrame()

    # -------------------------
    # FIO
    # -------------------------
    processed["fio"] = df["ФИО"]

    # -------------------------
    # RESIDENT FLAG (КЛЮЧЕВОЕ)
    # -------------------------
    processed["resident"] = df.get(
        "Выбор тарифа за проживание",
        True
    ).apply(parse_resident)

    # -------------------------
    # gender / meta
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
    # HARD GROUPS (пока пусто)
    # -------------------------
    processed["group_hard"] = [[] for _ in range(len(processed))]

    # -------------------------
    # NON-RESIDENT CLEANUP
    # -------------------------
    # важно: у них не должно быть ночей
    mask = processed["resident"] == False
    processed.loc[mask, "nights"] = processed.loc[mask, "nights"].apply(lambda x: [])

    return processed
