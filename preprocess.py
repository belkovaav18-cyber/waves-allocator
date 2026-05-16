import pandas as pd
import re


def normalize_columns(df):
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.replace("\n", " ", regex=False)
        .str.strip()
    )
    return df


def norm(x):
    return re.sub(r"\s+", " ", str(x).strip().lower())


def detect_gender(fio):
    parts = str(fio).split()
    if not parts:
        return "M"
    return "F" if parts[0].lower().endswith(("а", "я")) else "M"


def extract_nights(row):
    nights = []

    for col in row.index:
        col_str = str(col).lower()
        val = row[col]

        if pd.isna(val):
            continue

        if "комната" not in col_str:
            continue

        val = str(val).lower().strip()
        if val in ["", "0", "нет", "false"]:
            continue

        m = re.search(r"ночь на (\d+)", col_str)
        if m:
            nights.append(int(m.group(1)))

    return sorted(set(nights))


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

    for fio_norm, fio in fio_index.items():
        parts = fio_norm.split()
        if len(parts) < 2:
            continue

        key = " ".join(parts[:2])
        if key in text:
            result.append(fio)

    return result


def preprocess_guests(df: pd.DataFrame):

    df = normalize_columns(df)

    processed = pd.DataFrame()

    processed["fio"] = df["ФИО"]
    processed["gender"] = processed["fio"].apply(detect_gender)
    processed["will_stay"] = (
    df["Выбор тарифа за проживание"]
    .astype(str)
    .str.strip()
    .str.lower()
    .ne("не буду проживать")
)
    processed["city"] = df.get("Город", "UNKNOWN")
    processed["status"] = df.get("Статус", "student")
    processed["comment"] = df.get("Комментарий", "")

    processed["nights"] = df.apply(extract_nights, axis=1)

    fio_index = build_fio_index(processed)

    processed["group_hard"] = processed["comment"].apply(
        lambda c: extract_hard_groups(c, fio_index)
    )

    processed["group_soft"] = [[] for _ in range(len(processed))]

    return processed
