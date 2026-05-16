import pandas as pd
import re


def normalize_columns(df):
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.replace("\n", " ", regex=False)
        .str.strip()
    )
    return df


def detect_gender(fio):
    parts = str(fio).split()
    if not parts:
        return "M"
    return "F" if parts[0].lower().endswith(("а", "я")) else "M"


def parse_resident(x):
    if pd.isna(x):
        return True
    x = str(x).lower()
    return not ("не буду" in x or "не прожива" in x)


def extract_nights(row):
    nights = []
    for col in row.index:
        if "ночь" not in str(col).lower():
            continue
        val = row[col]
        if pd.isna(val):
            continue
        if str(val).strip().lower() in ["нет", "0", "-", "false", ""]:
            continue

        m = re.search(r"(\d+)", str(col))
        if m:
            nights.append(int(m.group(1)))

    return sorted(set(nights))


# ---------------- SAFE COMMENT PARSER (TEMP STUB) ----------------
def parse_comment_safe(comment):
    return {
        "hard_group": [],
        "soft_group": [],
        "avoid_group": [],
        "room_type": None
    }


def preprocess_guests(df):

    df = normalize_columns(df)

    # ---------------- SAFE COLUMN ACCESS ----------------
    def col(name, default=None):
        return df[name] if name in df.columns else pd.Series([default] * len(df))

    fio = col("ФИО", "")

    processed = pd.DataFrame()
    processed["fio"] = fio
    processed["gender"] = fio.apply(detect_gender)

    processed["city"] = col("Город", "UNKNOWN")
    processed["status"] = col("Статус", "student")

    processed["resident"] = col("Выбор тарифа за проживание", "").apply(parse_resident)

    processed["nights"] = df.apply(extract_nights, axis=1)

    # IMPORTANT: no crashes
    comments = col("Комментарий", "").fillna("")

    parsed = comments.apply(parse_comment_safe)

    processed["group_hard"] = parsed.apply(lambda x: x["hard_group"])
    processed["group_soft"] = parsed.apply(lambda x: x["soft_group"])
    processed["group_avoid"] = parsed.apply(lambda x: x["avoid_group"])
    processed["room_type"] = parsed.apply(lambda x: x["room_type"])

    # non-residents
    processed.loc[~processed["resident"], "nights"] = [[] for _ in range(len(processed))]

    return processed
