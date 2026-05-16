import pandas as pd
import re


# =========================================================
# NORMALIZATION
# =========================================================
def normalize_columns(df):
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.replace("\n", " ", regex=False)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )
    return df


def norm(text):
    text = str(text).lower()
    text = re.sub(r"[^\w\sа-яё]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# =========================================================
# GENDER (простая эвристика)
# =========================================================
def detect_gender(fio):
    parts = str(fio).split()
    if not parts:
        return "M"
    return "F" if parts[0].lower().endswith(("а", "я")) else "M"


# =========================================================
# RESIDENT PARSER (УЛУЧШЕННЫЙ)
# =========================================================
def parse_resident(v):
    v = str(v).lower()

    if any(x in v for x in ["не буду", "не прожив", "не планирую", "отказ"]):
        return False

    return True


# =========================================================
# ROOM TYPE
# =========================================================
def detect_room_type(text):
    text = norm(text)

    if "одномест" in text:
        return 1
    if "двухмест" in text or "2 мест" in text:
        return 2
    if "трехмест" in text or "3 мест" in text:
        return 3

    return None


# =========================================================
# FUZZY FIO MATCH (ВАЖНО)
# =========================================================
def fio_match(text, fio):
    """
    матчим не строго, а по фамилии + части имени
    """
    text = norm(text)
    fio_norm = norm(fio)

    parts = fio_norm.split()

    if not parts:
        return False

    surname = parts[0]

    # если фамилия есть — уже считаем матч
    if surname in text:
        return True

    # fallback: инициалы типа "а с" или "ас"
    initials = "".join([p[0] for p in parts[1:] if p])
    if initials and initials in text.replace(" ", ""):
        return True

    return False


# =========================================================
# COMMENT PARSER
# =========================================================
def parse_comment(comment, fio_list):

    text = norm(comment)

    hard = []
    soft = []
    avoid = []

    # -------------------------
    # HARD GROUP (люди в тексте)
    # -------------------------
    for fio in fio_list:
        if fio_match(text, fio):
            hard.append(fio)

    # -------------------------
    # ROOM TYPE
    # -------------------------
    room_type = detect_room_type(text)

    if "без подсел" in text or "одномест" in text:
        room_type = 1

    return {
        "hard_group": list(set(hard)),
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

    # -------------------------
    # BASIC
    # -------------------------
    processed["fio"] = df["ФИО"].astype(str)

    # -------------------------
    # RESIDENT
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
    # NIGHTS (оставляем только для резидентов)
    # -------------------------
    processed["nights"] = [[] for _ in range(len(processed))]

    processed.loc[
        processed["resident"] == True,
        "nights"
    ] = df.apply(lambda r: [], axis=1)

    # -------------------------
    # COMMENT ENGINE (FIXED)
    # -------------------------
    fio_list = processed["fio"].tolist()

    if "Комментарий" in df.columns:
        comment_col = df["Комментарий"].fillna("").astype(str)
    else:
        comment_col = pd.Series([""] * len(processed))

    parsed = comment_col.apply(lambda c: parse_comment(c, fio_list))

    processed["group_hard"] = [p["hard_group"] for p in parsed]
    processed["group_soft"] = [p["soft_group"] for p in parsed]
    processed["group_avoid"] = [p["avoid_group"] for p in parsed]
    processed["room_type"] = [p["room_type"] for p in parsed]

    return processed
