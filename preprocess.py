import pandas as pd
import re


ROOM_KEYWORD = "Комната"
MEAL_KEYWORDS = ["Завтрак", "Обед", "Ужин"]
BUS_KEYWORDS = ["Автобус"]


# -------------------------
# имя → пол (очень грубо)
# -------------------------
def detect_gender(fio):
    if not fio:
        return "M"
    fio = fio.strip().lower()
    return "F" if fio.split()[0].endswith(("а", "я")) else "M"


# -------------------------
# извлечение "комнатных ночей"
# -------------------------
def extract_nights(row):

    nights = []

    for col, val in row.items():

        if ROOM_KEYWORD not in col:
            continue

        if pd.isna(val) or str(val).strip() == "":
            continue

        # ищем дату внутри названия столбца
        match = re.search(r"(\d{1,2})", col)
        if match:
            nights.append(int(match.group(1)))

    return sorted(set(nights))


# -------------------------
# комментарии → группы
# -------------------------
def extract_group(row):

    comment = str(row.get("Комментарий", "")).lower()

    # ищем фамилии/инициалы (очень упрощённо)
    names = re.findall(r"[а-яёa-z]{4,}", comment, re.IGNORECASE)

    # убираем мусорные слова
    stop = {"прошу", "поселить", "вместе", "если", "можно"}

    group = [n for n in names if n not in stop]

    return group if group else []


# -------------------------
# статус
# -------------------------
def detect_status(row):
    s = str(row.get("Выбор тарифа за проживание", "")).lower()

    if "проф" in s:
        return "professor"
    return "student"


# -------------------------
# main preprocess
# -------------------------
def preprocess_guests(df):

    df = df.copy()

    result = []

    for _, row in df.iterrows():

        fio = row.get("ФИО")
        if pd.isna(fio):
            continue

        nights = extract_nights(row)

        if not nights:
            continue

        meals = {
            "breakfast": [],
            "lunch": [],
            "dinner": []
        }

        for col, val in row.items():

            if pd.isna(val):
                continue

            for k in MEAL_KEYWORDS:
                if k in col and str(val).strip() != "":
                    meals[k.lower()] = True

        result.append({
            "id": row.get("ID"),
            "fio": fio,
            "gender": detect_gender(fio),
            "status": detect_status(row),
            "nights": nights,
            "group": extract_group(row),
            "car": row.get("Номер автомобиля"),
            "comment": row.get("Комментарий"),
            "raw": row.to_dict()
        })

    return pd.DataFrame(result)
