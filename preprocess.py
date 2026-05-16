import pandas as pd
import re


# =========================================================
# NORMALIZE COLUMNS
# =========================================================
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.replace("\n", " ", regex=False)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )
    return df


# =========================================================
# SAFE COLUMN FINDER (КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ)
# =========================================================
def get_col(df: pd.DataFrame, name: str):
    """
    Ищет колонку независимо от:
    - регистра
    - пробелов
    - скрытых символов
    """
    name = name.strip().lower()

    for c in df.columns:
        if str(c).strip().lower() == name:
            return df[c]

    return None


# =========================================================
# NORMALIZATION
# =========================================================
def norm(x):
    return re.sub(r"\s+", " ", str(x).strip().lower())


# =========================================================
# GENDER (простая эвристика)
# =========================================================
def detect_gender(fio: str):
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

        if "комната" not in col_str:
            continue

        val = str(val).strip().lower()
        if val in ["", "0", "нет", "false"]:
            continue

        m = re.search(r"ночь на (\d+)", col_str)
        if m:
            nights.append(int(m.group(1)))

    return sorted(set(nights))


# =========================================================
# FIO INDEX FOR GROUPS
# =========================================================
def build_fio_index(df):
    return {
        norm(fio): fio
        for fio in df["fio"].fillna("")
    }


# =========================================================
# HARD GROUPS PARSER (regex-based)
# =========================================================
def extract_hard_groups(comment, fio_index):
    if not comment:
        return []

    text = norm(comment)
    result = []

    for fio_norm, fio in fio_index.items():
        parts = fio_norm.split()
        if len(parts) < 2:
            continue

        key = " ".join(parts[:2])

        if key in text:
            result.append(fio)

    return result


# =========================================================
# MAIN PREPROCESS
# =========================================================
def preprocess_guests(df: pd.DataFrame):

    df = normalize_columns(df)

    processed = pd.DataFrame()

    # =====================================================
    # FIO (обязательно)
    # =====================================================
    fio_col = get_col(df, "ФИО")
    processed["fio"] = fio_col if fio_col is not None else ""

    # =====================================================
    # gender
    # =====================================================
    processed["gender"] = processed["fio"].apply(detect_gender)

    # =====================================================
    # optional fields
    # =====================================================
    city_col = get_col(df, "Город")
    status_col = get_col(df, "Статус")
    comment_col = get_col(df, "Комментарий")

    processed["city"] = city_col if city_col is not None else "UNKNOWN"
    processed["status"] = status_col if status_col is not None else "student"
    processed["comment"] = comment_col if comment_col is not None else ""

    # =====================================================
    # NIGHTS
    # =====================================================
    processed["nights"] = df.apply(extract_nights, axis=1)

    # =====================================================
    # WILL STAY (КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ)
    # =====================================================
    tariff_col = get_col(df, "Выбор тарифа за проживание")

    if tariff_col is None:
        processed["will_stay"] = True
    else:
        processed["will_stay"] = (
            tariff_col.astype(str)
            .str.strip()
            .str.lower()
            .ne("не буду проживать")
        )

    # =====================================================
    # HARD GROUPS
    # =====================================================
    fio_index = build_fio_index(processed)

    processed["group_hard"] = processed["comment"].apply(
        lambda c: extract_hard_groups(c, fio_index)
    )

    # =====================================================
    # SOFT GROUPS (пока пусто)
    # =====================================================
    processed["group_soft"] = [[] for _ in range(len(processed))]

    return processed
