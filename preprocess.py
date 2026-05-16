import pandas as pd
import re


# =========================================================
# NORMALIZE COLUMNS
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
    if pd.isna(v):
        return True

    v = str(v).lower()
    if ("не" in v and "прож" in v) or ("не буду" in v):
        return False

    return True


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

        m = re.search(r"(\d+)", col_str)
        if m:
            nights.append(int(m.group(1)))

    return sorted(set(nights))


# =========================================================
# NAME MATCHING HELPERS (КЛЮЧЕВАЯ ЧАСТЬ)
# =========================================================
def normalize_surname(fio):
    """
    Делает фамилию устойчивой к падежам:
    Черновым -> чернов
    Ивановой -> иванов
    """
    s = fio.lower().split()[0]
    s = re.sub(r"(ым|ом|ой|ая|ую|ю|е|а|я|у|и|ы)$", "", s)
    return s


def match_fio(text, fio):
    """
    fuzzy matching без библиотек
    """
    text = text.lower()

    surname = normalize_surname(fio)

    # прямое вхождение
    if surname in text:
        return True

    # частичное совпадение (на случай сокращений)
    if len(surname) >= 4 and surname[:4] in text:
        return True

    return False


# =========================================================
# COMMENT PARSER
# =========================================================
def parse_comment(comment, fio_list):

    text = str(comment).lower()

    hard = []
    soft = []
    avoid = []

    # -------------------------
    # HARD GROUP
    # -------------------------
    for fio in fio_list:
        if not fio:
            continue

        if match_fio(text, fio):
            hard.append(fio)

    # -------------------------
    # ROOM TYPE
    # -------------------------
    room_type = None

    if "одномест" in text or "без подсел" in text:
        room_type = 1
    elif "двухмест" in text or "2-мест" in text:
        room_type = 2
    elif "трехмест" in text or "3-мест" in text:
        room_type = 3

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
    processed["fio"] = df.get("ФИО", "")

    # -------------------------
    # RESIDENT
    # -------------------------
    processed["resident"] = df.get(
        "Выбор тарифа за проживание", ""
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
    mask = ~processed["resident"]
    processed.loc[mask, "nights"] = pd.Series(
        [[] for _ in range(mask.sum())],
        index=processed[mask].index
    )

    # -------------------------
    # COMMENTS ENGINE
    # -------------------------
    fio_list = processed["fio"].fillna("").tolist()

    if "Комментарий" in df.columns:
        comments = df["Комментарий"].fillna("")
    else:
        comments = pd.Series([""] * len(processed))

    parsed = comments.apply(lambda c: parse_comment(c, fio_list))

    processed["group_hard"] = parsed.apply(lambda x: x["hard_group"])
    processed["group_soft"] = parsed.apply(lambda x: x["soft_group"])
    processed["group_avoid"] = parsed.apply(lambda x: x["avoid_group"])
    processed["room_type"] = parsed.apply(lambda x: x["room_type"])

    return processed
