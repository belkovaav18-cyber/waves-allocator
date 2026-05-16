import pandas as pd
import re


# =========================================================
# NORMALIZE COLUMNS
# =========================================================
def normalize_columns(df):
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.replace("\n", " ", regex=False)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
        .str.lower()
    )
    return df


# =========================================================
# CLEAN TEXT
# =========================================================
def clean(text):
    text = str(text).lower()
    text = re.sub(r"[^\w\sа-яё]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# =========================================================
# GENDER
# =========================================================
def detect_gender(fio):
    parts = str(fio).split()
    if not parts:
        return "M"
    return "F" if parts[0].lower().endswith(("а", "я")) else "M"


# =========================================================
# RESIDENT
# =========================================================
def parse_resident(v):
    v = str(v).lower()

    if any(x in v for x in ["не буду", "не прожив", "не проживает", "отказ"]):
        return False

    return True


# =========================================================
# ROOM TYPE
# =========================================================
def detect_room_type(text):
    t = clean(text)

    if "одномест" in t:
        return 1
    if "двухмест" in t or "2 мест" in t:
        return 2
    if "трехмест" in t or "3 мест" in t:
        return 3

    return None


# =========================================================
# FIO MATCH (СТАБИЛЬНЫЙ)
# =========================================================
def fio_match(text, fio):
    text = clean(text)
    fio = clean(fio)

    parts = fio.split()
    if not parts:
        return False

    surname = parts[0]

    if surname not in text:
        return False

    initials = "".join([p[0] for p in parts[1:] if p])

    if initials:
        return initials in text.replace(" ", "")

    return True


# =========================================================
# COMMENT PARSER
# =========================================================
def parse_comment(comment, fio_list):

    text = clean(comment)

    hard = []
    soft = []
    avoid = []

    for fio in fio_list:
        if fio_match(text, fio):
            hard.append(fio)

    room_type = detect_room_type(text)

    if "без подсел" in text:
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
    # BASIC
    # -------------------------
    processed["fio"] = df["фио"].astype(str)

    # -------------------------
    # RESIDENT
    # -------------------------
    processed["resident"] = df.get(
        "выбор тарифа за проживание",
        ""
    ).apply(parse_resident)

    # -------------------------
    # META
    # -------------------------
    processed["gender"] = processed["fio"].apply(detect_gender)

    processed["city"] = df.get("город", "unknown")
    processed["status"] = df.get("статус", "student")

    # -------------------------
    # NIGHTS
    # -------------------------
    processed["nights"] = [[] for _ in range(len(processed))]

    # -------------------------
    # COMMENTS SAFE
    # -------------------------
    fio_list = df["фио"].astype(str).tolist()

    if "комментарий" in df.columns:
        comment_col = df["комментарий"].fillna("").astype(str)
    else:
        comment_col = pd.Series([""] * len(df))

    parsed = comment_col.apply(lambda c: parse_comment(c, fio_list))

    processed["group_hard"] = [p["hard_group"] for p in parsed]
    processed["group_soft"] = [p["soft_group"] for p in parsed]
    processed["group_avoid"] = [p["avoid_group"] for p in parsed]
    processed["room_type"] = [p["room_type"] for p in parsed]

    return processed
