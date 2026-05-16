import pandas as pd
import re


def norm_cols(df):
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )
    return df


def detect_gender(fio):
    fio = str(fio)
    if not fio:
        return "M"
    return "F" if fio.split()[0].lower().endswith(("а", "я")) else "M"


def parse_resident(x):
    if pd.isna(x):
        return True
    x = str(x).lower()
    return not ("не буду" in x or "не прожива" in x)


def extract_nights(row):
    nights = []
    for col in row.index:
        if "ночь" not in str(col).lower():
            continue

        val = row[col]
        if pd.isna(val):
            continue

        if str(val).strip().lower() in ["нет", "0", "-", "false", ""]:
            continue

        m = re.search(r"(\d+)", str(col))
        if m:
            nights.append(int(m.group(1)))

    return list(set(nights))


# ---------------- SAFE COMMENT PARSER ----------------
def parse_comment(comment):
    # пока заглушка (потом подключишь LLM/regex engine)
    return {
        "hard_group": [],
        "soft_group": [],
        "avoid_group": [],
        "room_type": None
    }


def preprocess_guests(df):

    df = norm_cols(df)

    def col(name, default=None):
        return df[name] if name in df.columns else pd.Series([default] * len(df))

    processed = pd.DataFrame()

    processed["fio"] = col("ФИО", "")
    processed["gender"] = processed["fio"].apply(detect_gender)

    processed["city"] = col("Город", "UNKNOWN")
    processed["status"] = col("Статус", "student")

    processed["resident"] = col("Выбор тарифа за проживание", "").apply(parse_resident)

    processed["nights"] = df.apply(extract_nights, axis=1)

    # comments safe
    comments = col("Комментарий", "").fillna("")

    parsed = comments.apply(parse_comment)

    processed["group_hard"] = parsed.apply(lambda x: x["hard_group"])
    processed["group_soft"] = parsed.apply(lambda x: x["soft_group"])
    processed["group_avoid"] = parsed.apply(lambda x: x["avoid_group"])
    processed["room_type"] = parsed.apply(lambda x: x["room_type"])

    # 🔥 FIX: без pandas assign list error
    processed.loc[processed["resident"] == False, "nights"] = processed.loc[
        processed["resident"] == False, "nights"
    ].apply(lambda _: [])

    return processed
