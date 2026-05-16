import pandas as pd
import re


# =========================================================
# CLEAN COLUMNS
# =========================================================
def normalize_columns(df):

    df = df.copy()

    df.columns = (
        df.columns
        .astype(str)
        .str.replace("\n", " ", regex=False)
        .str.strip()
    )

    return df


# =========================================================
# EXTRACT NIGHTS FROM WIDE TABLE
# =========================================================
def extract_nights(row):

    nights = []

    for col, val in row.items():

        if pd.isna(val):
            continue

        val = str(val).strip().lower()

        # интересуют только отметки проживания
        if "комната" in col.lower():

            # если человек выбрал проживание
            if val != "" and val.lower() not in ["нет", "0", "-"]:

                # вытаскиваем ночь из названия колонки
                match = re.search(r"ночь на (\d+)", col)

                if match:
                    nights.append(int(match.group(1)))

    return sorted(list(set(nights)))


# =========================================================
# GROUP PARSER
# =========================================================
def extract_hard_group(comment):

    if not comment:
        return []

    text = str(comment).lower()

    names = re.findall(r"[а-яё]{4,}", text)

    stop = {
        "прошу", "поселить", "вместе",
        "пожалуйста", "спасибо", "соавтором"
    }

    return [
        n for n in names
        if n not in stop and len(n) > 3
    ]


# =========================================================
# MAIN
# =========================================================
def preprocess_guests(df):

    df = normalize_columns(df)

    processed = pd.DataFrame()

    # -----------------------------
    # FIO
    # -----------------------------
    processed["fio"] = df["ФИО"]

    # -----------------------------
    # gender
    # -----------------------------
    processed["gender"] = df["ФИО"].apply(
        lambda x: "F" if str(x).strip().split()[0].endswith(("а", "я")) else "M"
    )

    # -----------------------------
    # status / city
    # -----------------------------
    processed["city"] = df.get("Город", "UNKNOWN")
    processed["status"] = df.get("Статус", "student")

    # -----------------------------
    # comments
    # -----------------------------
    processed["comment"] = df.get("Комментарий", "")

    # -----------------------------
    # NIGHTS (ВАЖНО)
    # -----------------------------
    processed["nights"] = df.apply(extract_nights, axis=1)

    # -----------------------------
    # groups
    # -----------------------------
    processed["group_hard"] = processed["comment"].apply(extract_hard_group)

    return processed
