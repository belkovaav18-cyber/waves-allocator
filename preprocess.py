import pandas as pd
import re
from comment_engine import parse_comment


def norm_cols(df):
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip()
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


# ---------------- MAIN ----------------
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

    # ---------------- COMMENTS ENGINE ----------------
    comments = col("Комментарий", "").fillna("")

    fio_list = processed["fio"].tolist()

    parsed = comments.apply(lambda c: parse_comment(c, fio_list))

    processed["group_hard"] = parsed.apply(lambda x: x["hard_group"])
    processed["group_soft"] = parsed.apply(lambda x: x["soft_group"])
    processed["group_avoid"] = parsed.apply(lambda x: x["avoid_group"])
    processed["room_type"] = parsed.apply(lambda x: x["room_type"])

    # non-residents
    processed.loc[~processed["resident"], "nights"] = processed.loc[
        ~processed["resident"], "nights"
    ].apply(lambda _: [])

    return processed
