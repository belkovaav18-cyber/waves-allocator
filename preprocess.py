import pandas as pd
import re

# если у тебя есть comment_engine — оставляем
try:
    from comment_engine import parse_comment
except:
    parse_comment = None


# =========================================================
# CLEAN COLUMNS
# =========================================================
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
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
# SAFE STRING NORMALIZE
# =========================================================
def norm(x):
    return re.sub(r"\s+", " ", str(x).strip().lower())


# =========================================================
# GENDER
# =========================================================
def detect_gender(fio: str) -> str:
    parts = str(fio).split()
    if not parts:
        return "M"

    return "F" if parts[0].lower().endswith(("а", "я")) else "M"


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

        if "комната" not in col_str:
            continue

        if val in ["", "нет", "0", "-", "false"]:
            continue

        match = re.search(r"ночь на (\d+)", col_str)
        if match:
            nights.append(int(match.group(1)))

    return sorted(set(nights))


# =========================================================
# RESIDENT PARSING
# =========================================================
def parse_resident(value):
    if pd.isna(value):
        return True

    v = str(value).strip().lower()

    # ВСЕ возможные варианты "не проживает"
    if any(x in v for x in [
        "не буду проживать",
        "не прожива",
        "не проживает",
        "no stay"
    ]):
        return False

    return True


# =========================================================
# COMMENT ENGINE SAFE WRAPPER
# =========================================================
def safe_parse_comments(df, fio_list):
    """
    возвращает структуру:
    [
      {
        hard_group: [],
        soft_group: [],
        avoid_group: [],
        room_type: ...
      }
    ]
    """

    results = []

    for c in df["Комментарий"].fillna(""):
        if parse_comment is None:
            results.append({
                "hard_group": [],
                "soft_group": [],
                "avoid_group": [],
                "room_type": None
            })
        else:
            try:
                results.append(parse_comment(c, fio_list))
            except:
                results.append({
                    "hard_group": [],
                    "soft_group": [],
                    "avoid_group": [],
                    "room_type": None
                })

    return results


# =========================================================
# MAIN
# =========================================================
def preprocess_guests(df: pd.DataFrame) -> pd.DataFrame:

    df = normalize_columns(df)
    df = df.copy()

    processed = pd.DataFrame()

    # -------------------------
    # FIO (гарантия)
    # -------------------------
    processed["fio"] = df.get("ФИО", "").fillna("").astype(str)

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

    processed["comment"] = df.get("Комментарий", "")

    # -------------------------
    # NIGHTS
    # -------------------------
    processed["nights"] = df.apply(extract_nights, axis=1)

    # ❗ нерезиденты не живут
    processed.loc[processed["resident"] == False, "nights"] = [[] for _ in range(len(processed))]

    # -------------------------
    # COMMENT ENGINE
    # -------------------------
    fio_list = processed["fio"].tolist()
    parsed = safe_parse_comments(df, fio_list)

    processed["group_hard"] = [p["hard_group"] for p in parsed]
    processed["group_soft"] = [p["soft_group"] for p in parsed]
    processed["group_avoid"] = [p["avoid_group"] for p in parsed]
    processed["room_type"] = [p["room_type"] for p in parsed]

    return processed
