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
    )

    return df


# =========================================================
# HELPERS
# =========================================================
def norm(x):

    return re.sub(
        r"\s+",
        " ",
        str(x).strip().lower()
    )


# =========================================================
# GENDER
# =========================================================
def detect_gender(fio):

    parts = str(fio).split()

    if not parts:
        return "M"

    return (
        "F"
        if parts[0].lower().endswith(("а", "я"))
        else "M"
    )


# =========================================================
# RESIDENT PARSER
# =========================================================
def parse_resident(v):

    if pd.isna(v):
        return True

    v = str(v).lower()

    if (
        "не буду" in v
        or "не прожива" in v
    ):
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

        if (
            "ноч" not in col_str
            and "комнат" not in col_str
        ):
            continue

        if val in ["", "нет", "0", "-", "false"]:
            continue

        match = re.search(r"(\d+)", col_str)

        if match:
            nights.append(int(match.group(1)))

    return sorted(list(set(nights)))


# =========================================================
# SHORT NAME BUILDER
# =========================================================
def short_versions(fio):

    fio = norm(fio)

    parts = fio.split()

    if len(parts) < 2:
        return []

    surname = parts[0]

    initials = ""

    for p in parts[1:]:
        initials += p[0]

    variants = [
        fio,
        surname,
        f"{surname} {initials}",
    ]

    if len(initials) >= 2:
        variants.append(
            f"{surname} {initials[0]}.{initials[1]}."
        )

        variants.append(
            f"{surname} {initials[0]}.{initials[1]}"
        )

    return variants


# =========================================================
# FIND PEOPLE IN COMMENT
# =========================================================
def extract_people(comment, fio_list):

    text = norm(comment)

    found = []

    for fio in fio_list:

        variants = short_versions(fio)

        for v in variants:

            if len(v) < 4:
                continue

            if v in text:
                found.append(fio)
                break

            score = fuzz.partial_ratio(v, text)

            if score >= 90:
                found.append(fio)
                break

    return list(set(found))


# =========================================================
# COMMENT PARSER
# =========================================================
def parse_comment(comment, fio_list):

    text = norm(comment)

    hard = []
    soft = []
    avoid = []

    allocation_variants = []

    room_type = None

    # =====================================================
    # ROOM TYPE
    # =====================================================

    if (
        "одномест" in text
        or "без подсел" in text
    ):
        room_type = 1

    elif (
        "двухмест" in text
        or "двух-мест" in text
        or "двуспаль" in text
    ):
        room_type = 2

    elif (
        "трехмест" in text
        or "трёхмест" in text
    ):
        room_type = 3

    # =====================================================
    # PEOPLE
    # =====================================================

    found_people = extract_people(
        text,
        fio_list
    )

    # =====================================================
    # TOGETHER WORDS
    # =====================================================

    together_words = [
        "вместе",
        "совместно",
        "поселить с",
        "проживание с",
        "заселить с",
        "с подселением",
        "с женой",
        "с мужем",
        "с супруг",
    ]

    if any(w in text for w in together_words):
        hard.extend(found_people)

    # =====================================================
    # SOFT WORDS
    # =====================================================

    soft_words = [
        "желательно",
        "если возможно",
        "по возможности",
        "хотелось бы"
    ]

    if any(w in text for w in soft_words):
        soft.extend(found_people)

    # =====================================================
    # AVOID
    # =====================================================

    avoid_words = [
        "не селить",
        "не вместе",
        "не хочу"
    ]

    if any(w in text for w in avoid_words):
        avoid.extend(found_people)

    # =====================================================
    # PRIORITY VARIANTS
    # =====================================================

    if (
        "если" in text
        and "3" in text
        and len(found_people) >= 2
    ):

        allocation_variants.append({
            "room_type": 3,
            "group": found_people,
            "priority": 1
        })

    if (
        "если" in text
        and "2" in text
        and len(found_people) >= 1
    ):

        allocation_variants.append({
            "room_type": 2,
            "group": [found_people[0]],
            "priority": 2
        })

    return {
        "hard_group": list(set(hard)),
        "soft_group": list(set(soft)),
        "avoid_group": list(set(avoid)),
        "room_type": room_type,
        "allocation_variants": allocation_variants
    }


# =========================================================
# MAIN PIPELINE
# =========================================================
def preprocess_guests(df):

    df = normalize_columns(df)

    processed = pd.DataFrame()

    # =====================================================
    # BASIC
    # =====================================================

    processed["fio"] = df["ФИО"]

    processed["resident"] = df.get(
        "Выбор тарифа за проживание",
        ""
    ).apply(parse_resident)

    processed["gender"] = (
        processed["fio"]
        .apply(detect_gender)
    )

    processed["city"] = df.get(
        "Город",
        "UNKNOWN"
    )

    processed["status"] = df.get(
        "Статус",
        "student"
    )

    # =====================================================
    # NIGHTS
    # =====================================================

    processed["nights"] = df.apply(
        extract_nights,
        axis=1
    )

    # нерезиденты не живут
    processed["nights"] = processed.apply(
        lambda row:
            []
            if not row["resident"]
            else row["nights"],
        axis=1
    )

    # =====================================================
    # COMMENTS
    # =====================================================

    fio_list = processed["fio"].tolist()

    comment_col = None

    for c in df.columns:

        c_norm = norm(c)

        if "коммент" in c_norm:
            comment_col = c
            break

    if comment_col is None:
        comments = pd.Series(
            [""] * len(processed)
        )
    else:
        comments = df[comment_col].fillna("")

    parsed = comments.apply(
        lambda c: parse_comment(c, fio_list)
    )

    processed["group_hard"] = [
        x["hard_group"]
        for x in parsed
    ]

    processed["group_soft"] = [
        x["soft_group"]
        for x in parsed
    ]

    processed["group_avoid"] = [
        x["avoid_group"]
        for x in parsed
    ]

    processed["room_type"] = [
        x["room_type"]
        for x in parsed
    ]

    processed["allocation_variants"] = [
        x["allocation_variants"]
        for x in parsed
    ]

    return processed
