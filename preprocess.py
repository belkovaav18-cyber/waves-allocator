import pandas as pd
import re
from rapidfuzz import fuzz


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
        .str.lower()
    )

    return df


# =========================================================
# TEXT NORMALIZATION
# =========================================================
def normalize(text):

    text = str(text).lower().strip()

    text = text.replace("ё", "е")

    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# =========================================================
# FIO NORMALIZATION
# =========================================================
def normalize_fio(fio):

    fio = normalize(fio)

    parts = fio.split()

    if len(parts) == 0:
        return ""

    return " ".join(parts)


# =========================================================
# GENDER
# =========================================================
def detect_gender(fio):

    fio = str(fio).strip()

    if not fio:
        return "M"

    parts = fio.split()

    if len(parts) < 2:
        return "M"

    name = parts[1].lower()

    if name.endswith(("а", "я")):
        return "F"

    return "M"


# =========================================================
# RESIDENT PARSER
# =========================================================
def parse_resident(v):

    if pd.isna(v):
        return True

    v = normalize(v)

    stop_words = [
        "не буду",
        "не прожива",
        "не планир",
        "без проживания",
        "отказ"
    ]

    for w in stop_words:
        if w in v:
            return False

    return True


# =========================================================
# NIGHTS EXTRACTION
# =========================================================
def extract_nights(row):

    nights = []

    for col in row.index:

        col_str = normalize(col)

        val = row[col]

        if pd.isna(val):
            continue

        val = normalize(val)

        # только колонки ночей
        if "ноч" not in col_str and "комнат" not in col_str:
            continue

        # пустые значения
        if val in ["", "нет", "0", "-", "false"]:
            continue

        # ищем номер ночи
        match = re.search(r"(\d+)", col_str)

        if match:
            nights.append(int(match.group(1)))

    return sorted(list(set(nights)))


# =========================================================
# ROOM TYPE DETECTION
# =========================================================
def detect_room_type(text):

    text = normalize(text)

    if any(x in text for x in [
        "одномест",
        "1 мест",
        "без подсел"
    ]):
        return 1

    if any(x in text for x in [
        "двухмест",
        "двух мест",
        "2 мест",
        "двух-мест"
    ]):
        return 2

    if any(x in text for x in [
        "трехмест",
        "трех мест",
        "3 мест",
        "трёхмест"
    ]):
        return 3

    return None


# =========================================================
# COMMENT PARSER
# =========================================================
def parse_comment(comment, fio_list, current_fio=None):

    text = normalize(comment)

    hard = []
    soft = []
    avoid = []

    # -----------------------------------------
    # fuzzy fio matching
    # -----------------------------------------
    for fio in fio_list:

        fio_norm = normalize_fio(fio)

        if not fio_norm:
            continue

        score = fuzz.partial_ratio(fio_norm, text)

        # DEBUG threshold
        if score >= 80:

            if current_fio is not None:

                # не добавляем самого себя
                if normalize_fio(current_fio) == fio_norm:
                    continue

            hard.append(fio)

    hard = list(set(hard))

    # -----------------------------------------
    # room type
    # -----------------------------------------
    room_type = detect_room_type(text)

    # -----------------------------------------
    # avoid logic
    # -----------------------------------------
    if any(x in text for x in [
        "не вместе",
        "не селить",
        "не подсел"
    ]):
        avoid = hard.copy()
        hard = []

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

    # -----------------------------------------
    # normalize columns
    # -----------------------------------------
    df = normalize_columns(df)

    processed = pd.DataFrame()

    # -----------------------------------------
    # FIO
    # -----------------------------------------
    if "фио" not in df.columns:
        raise Exception("Колонка ФИО не найдена")

    processed["fio"] = df["фио"].astype(str)

    # -----------------------------------------
    # RESIDENT
    # -----------------------------------------
    tariff_col = None

    for c in df.columns:
        if "тариф" in c and "прож" in c:
            tariff_col = c
            break

    if tariff_col:
        processed["resident"] = df[tariff_col].apply(parse_resident)
    else:
        processed["resident"] = True

    # -----------------------------------------
    # META
    # -----------------------------------------
    city_col = next(
        (c for c in df.columns if "город" in c),
        None
    )

    status_col = next(
        (c for c in df.columns if "статус" in c),
        None
    )

    processed["city"] = (
        df[city_col] if city_col else "unknown"
    )

    processed["status"] = (
        df[status_col] if status_col else "student"
    )

    # -----------------------------------------
    # GENDER
    # -----------------------------------------
    processed["gender"] = processed["fio"].apply(
        detect_gender
    )

    # -----------------------------------------
    # NIGHTS
    # -----------------------------------------
    processed["nights"] = df.apply(
        extract_nights,
        axis=1
    )

    # -----------------------------------------
    # нерезиденты не живут
    # -----------------------------------------
    processed["nights"] = processed.apply(
        lambda r: [] if not r["resident"] else r["nights"],
        axis=1
    )

    # -----------------------------------------
    # COMMENT COLUMN
    # -----------------------------------------
    comment_col = next(
        (
            c for c in df.columns
            if "коммент" in c
            or "пожел" in c
        ),
        None
    )

    if comment_col:
        comments = df[comment_col].fillna("").astype(str)
    else:
        comments = pd.Series(
            [""] * len(processed)
        )

    # -----------------------------------------
    # COMMENT PARSING
    # -----------------------------------------
    fio_list = processed["fio"].tolist()

    parsed = []

    for i in range(len(processed)):

        current_fio = processed.iloc[i]["fio"]

        p = parse_comment(
            comments.iloc[i],
            fio_list,
            current_fio=current_fio
        )

        parsed.append(p)

    processed["group_hard"] = [
        p["hard_group"] for p in parsed
    ]

    processed["group_soft"] = [
        p["soft_group"] for p in parsed
    ]

    processed["group_avoid"] = [
        p["avoid_group"] for p in parsed
    ]

    processed["room_type"] = [
        p["room_type"] for p in parsed
    ]

    return processed
