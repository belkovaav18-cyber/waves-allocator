import pandas as pd
import re


# =========================================================
# COLUMN NORMALIZATION
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


# =========================================================
# HELPERS
# =========================================================
def norm(x):
    return re.sub(r"\s+", " ", str(x).strip().lower())


# =========================================================
# GENDER
# =========================================================
def detect_gender(fio):
    parts = str(fio).split()
    if not parts:
        return "M"
    return "F" if parts[0].lower().endswith(("а", "я")) else "M"


# =========================================================
# RESIDENT PARSER
# =========================================================
def parse_resident(v):
    if pd.isna(v):
        return True

    v = str(v).lower()

    if "не" in v and "прож" in v:
        return False

    return True


# =========================================================
# NIGHTS EXTRACTION
# =========================================================
def extract_nights(row):
    nights = []

    for col in row.index:
        col_str = str(col).lower()
        val = row[col]

        if pd.isna(val):
            continue

        val = str(val).strip().lower()

        if "ноч" not in col_str and "комнат" not in col_str:
            continue

        if val in ["", "нет", "0", "-", "false"]:
            continue

        match = re.search(r"(\d+)", col_str)
        if match:
            nights.append(int(match.group(1)))

    return sorted(set(nights))


# =========================================================
# COMMENT PARSER (RULE-BASED)
# =========================================================
def parse_comment(comment, fio_list):

    text = str(comment).lower()

    hard = []
    soft = []
    avoid = []

    # --- simple FIO matching ---
    for fio in fio_list:
        fio_l = fio.lower()
        if fio_l and fio_l in text:
            hard.append(fio)

    # --- room type detection ---
    room_type = None

    if "одномест" in text:
        room_type = 1
    elif "двухмест" in text or "двух-мест" in text:
        room_type = 2
    elif "трехмест" in text or "трёхмест" in text:
        room_type = 3

    # --- special logic ---
    if "без подсел" in text or "одномест" in text:
        room_type = 1

    return {
        "hard_group": list(set(hard)),
        "soft_group": soft,
        "avoid_group": avoid,
        "room_type": room_type
    }


# =========================================================
# MAIN PIPELINE
# =========================================================
def preprocess_guests(df):

    df = normalize_columns(df)

    processed = pd.DataFrame()

    # -------------------------
    # BASIC FIELDS
    # -------------------------
    processed["fio"] = df["ФИО"]

    # -------------------------
    # RESIDENT FLAG
    # -------------------------
    processed["resident"] = df.get(
        "Выбор тарифа за проживание",
        ""
    ).apply(parse_resident)

    # -------------------------
    # META
    # -------------------------
    processed["gender"] = processed["fio"].apply(detect_gender)

    processed["city"] = df.get("Город", "UNKNOWN")
    processed["status"] = df.get("Статус", "student")

    # -------------------------
    # NIGHTS
    # -------------------------
    processed["nights"] = df.apply(extract_nights, axis=1)

    # нерезиденты не живут
    processed["nights"] = processed.apply(
        lambda r: [] if not r["resident"] else r["nights"],
        axis=1
    )

    # -------------------------
    # COMMENT ENGINE (SAFE)
    # -------------------------
    fio_list = processed["fio"].tolist()

    if "Комментарий" in df.columns:
        comment_series = df["Комментарий"].fillna("")
    else:
        comment_series = pd.Series([""] * len(processed))

    parsed = comment_series.apply(
        lambda c: parse_comment(c, fio_list)
    )

    processed["group_hard"] = [p["hard_group"] for p in parsed]
    processed["group_soft"] = [p["soft_group"] for p in parsed]
    processed["group_avoid"] = [p["avoid_group"] for p in parsed]
    processed["room_type"] = [p["room_type"] for p in parsed]

    return processed
