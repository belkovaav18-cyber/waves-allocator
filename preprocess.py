import pandas as pd
import re


ROOM_WORD = "Комната"


def detect_gender(fio):
    if not fio:
        return "M"
    return "F" if fio.strip().split()[0].endswith(("а", "я")) else "M"


def extract_nights(row):
    nights = []

    for col, val in row.items():
        if ROOM_WORD not in col:
            continue
        if pd.isna(val) or str(val).strip() == "":
            continue

        m = re.search(r"(\d{1,2})", col)
        if m:
            nights.append(int(m.group(1)))

    return sorted(set(nights))


def extract_group(comment):
    if not comment:
        return []

    comment = str(comment)

    # ищем фамилии/инициалы
    names = re.findall(r"[А-ЯЁA-Z][а-яёa-z]{2,}", comment)

    stop = {"прошу", "поселить", "вместе", "если", "можно"}

    return [n for n in names if n.lower() not in stop]


def preprocess(df):

    res = []

    for _, row in df.iterrows():

        fio = row.get("ФИО")
        if pd.isna(fio):
            continue

        nights = extract_nights(row)

        if not nights:
            continue

        res.append({
            "id": row.get("ID"),
            "fio": fio,
            "gender": detect_gender(fio),
            "status": str(row.get("Выбор тарифа за проживание", "student")),
            "nights": nights,
            "group": extract_group(row.get("Комментарий")),
            "city": row.get("Город"),
        })

    return pd.DataFrame(res)
