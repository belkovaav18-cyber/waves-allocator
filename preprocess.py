import pandas as pd
import re

# =========================================================
# utils
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
# GENDER
# =========================================================
def detect_gender(fio):
    parts = str(fio).split()
    if not parts:
        return "M"
    return "F" if parts[0].lower().endswith(("а", "я")) else "M"


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

        if "ноч" not in col_str and "комнат" not in col_str:
            continue

        if val in ["", "нет", "0", "-", "false"]:
            continue

        match = re.search(r"(\d+)", col_str)
        if match:
            nights.append(int(match.group(1)))

    return sorted(set(nights))


# =========================================================
# RESIDENT
# =========================================================
def parse_resident(v):
    if pd.isna(v):
        return True

    v = str(v).lower()
    if "не" in v and "прож" in v:
        return False

    return True


# =========================================================
# ROOM TYPE
# =========================================================
def parse_room_type(comment):
    if not comment:
        return None

    c = str(comment).lower()

    if "одномест" in c:
        return 1
    if "двухмест" in c or "двух-мест" in c:
        return 2
    if "трехмест" in c or "трёхмест" in c:
        return 3

    return None


# =========================================================
# COMMENT ENGINE (очень простой, но рабочий)
# =========================================================
def parse_comment(comment, fio_list):

    text = str(comment).lower()

    hard = []
    soft = []
    avoid = []

    for fio in fio_list:
        fio_l = fio.lower()

        if fio_l in text:
            hard.append(fio)

    # эвристики
    if "без подсел" in text or "одномест" in text:
        return {
            "hard_group": [],
            "soft_group": [],
            "avoid_group": [],
            "room_type": 1
        }

    if "двухмест" in text:
        room_type = 2
    elif "трехмест" in text:
        room_type = 3
    else:
        room_type = None

    return {
        "hard_group": hard,
        "soft_group": soft,
        "avoid_group": avoid,
        "room_type": room_type
    }


# =========================================================
# MAIN
# =========================================================
def preprocess_guests(df):

    df = normalize_columns(df)

    processed = pd.DataFrame()

    # basic
    processed["fio"] = df["ФИО"]

    # resident
    processed["resident"] = df.get("Выбор тарифа за проживание", "").apply(parse_resident)

    # meta
    processed["gender"] = processed["fio"].apply(detect_gender)
    processed["city"] = df.get("Город", "UNKNOWN")
    processed["status"] = df.get("Статус", "student")

    # nights
    processed["nights"] = df.apply(extract_nights, axis=1)

    # IMPORTANT: non-residents
    mask = ~processed["resident"]
    processed.loc[mask, "nights"] = [[] for _ in range(mask.sum())]

    # comments SAFE
    comment_col = df["Комментарий"] if "Комментарий" in df.columns else [""] * len(df)

    fio_list = processed["fio"].tolist()

    parsed = comment_col.apply(lambda c: parse_comment(c, fio_list))

    processed["group_hard"] = [p["hard_group"] for p in parsed]
    processed["group_soft"] = [p["soft_group"] for p in parsed]
    processed["group_avoid"] = [p["avoid_group"] for p in parsed]
    processed["room_type"] = [p["room_type"] for p in parsed]

    return processed
