import pandas as pd
import re
from rapidfuzz import process, fuzz


# =========================================================
# CLEAN TEXT
# =========================================================
def clean(text):
    text = str(text).lower()
    text = re.sub(r"[^\w\sа-яё]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# =========================================================
# FIO NORMALIZATION (CRITICAL)
# =========================================================
def normalize_fio(fio):
    fio = clean(fio)
    fio = fio.replace("ё", "е")
    fio = fio.replace(".", "")
    return fio


def fio_variants(fio):
    """
    создаём варианты для лучшего матчинга
    """
    fio = normalize_fio(fio)
    parts = fio.split()

    if not parts:
        return []

    surname = parts[0]

    initials = "".join([p[0] for p in parts[1:] if p])

    variants = [
        surname,
        fio,
        surname + initials,
    ]

    return list(set(variants))


# =========================================================
# RESIDENT
# =========================================================
def parse_resident(v):
    v = str(v).lower()
    return not any(x in v for x in ["не буду", "не прожив", "отказ", "не планир"])


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
# FUZZY MATCH ENGINE
# =========================================================
def match_fios(text, fio_list, threshold=85):
    text = clean(text)

    matches = []

    for fio in fio_list:
        variants = fio_variants(fio)

        best = process.extractOne(
            text,
            variants,
            scorer=fuzz.partial_ratio
        )

        if best and best[1] >= threshold:
            matches.append(fio)

    return list(set(matches))


# =========================================================
# COMMENT PARSER
# =========================================================
def parse_comment(comment, fio_list):

    text = clean(comment)

    hard = match_fios(text, fio_list)

    soft = []
    avoid = []

    room_type = detect_room_type(text)

    # жесткие правила
    if "без подсел" in text:
        room_type = 1

    return {
        "hard_group": hard,
        "soft_group": soft,
        "avoid_group": avoid,
        "room_type": room_type
    }


# =========================================================
# MAIN PIPELINE
# =========================================================
def preprocess_guests(df):

    df = df.copy()

    # normalize columns
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
    )

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
    processed["city"] = df.get("город", "unknown")
    processed["status"] = df.get("статус", "student")

    # -------------------------
    # NIGHTS (упрощено)
    # -------------------------
    processed["nights"] = [[] for _ in range(len(processed))]

    # -------------------------
    # COMMENTS SAFE
    # -------------------------
    fio_list = processed["fio"].tolist()

    if "комментарий" in df.columns:
        comments = df["комментарий"].fillna("").astype(str)
    else:
        comments = pd.Series([""] * len(df))

    parsed = comments.apply(lambda c: parse_comment(c, fio_list))

    processed["group_hard"] = [p["hard_group"] for p in parsed]
    processed["group_soft"] = [p["soft_group"] for p in parsed]
    processed["group_avoid"] = [p["avoid_group"] for p in parsed]
    processed["room_type"] = [p["room_type"] for p in parsed]

    return processed
