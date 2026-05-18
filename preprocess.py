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
# SHORT NAME BUILDER (УЛУЧШЕННАЯ ВЕРСИЯ)
# =========================================================
def short_versions(fio):
    """Генерирует разные варианты написания ФИО для поиска"""
    fio = norm(fio)
    parts = fio.split()
    
    if len(parts) < 2:
        return []
    
    surname = parts[0]
    name = parts[1] if len(parts) > 1 else ""
    patronymic = parts[2] if len(parts) > 2 else ""
    
    variants = [
        fio,  # полное: "попкова анна андреевна"
        surname,  # только фамилия: "попкова"
        f"{surname} {name}",  # фамилия + имя: "попкова анна"
        f"{surname} {name[0]}.{patronymic[0]}." if patronymic else f"{surname} {name[0]}.",  # "попкова а.а."
        f"{surname} {name[0]}.{patronymic[0]}" if patronymic else f"{surname} {name[0]}",  # "попкова а.а"
        f"{surname} {name[0]}",  # "попкова а"
    ]
    
    # Варианты с падежными окончаниями (для русского языка)
    name_variants = []
    if name.endswith("а"):
        name_variants.append(name[:-1] + "ы")  # анна -> анны
        name_variants.append(name[:-1] + "е")  # анна -> анне
        name_variants.append(name[:-1] + "у")  # анна -> анну
        name_variants.append(name[:-1] + "ой")  # анна -> анной
    
    if patronymic and patronymic.endswith("а"):
        name_variants.append(patronymic[:-1] + "ы")
        name_variants.append(patronymic[:-1] + "е")
        name_variants.append(patronymic[:-1] + "у")
        name_variants.append(patronymic[:-1] + "ой")
    
    for nv in name_variants:
        variants.append(f"{surname} {nv}")
        variants.append(f"{surname} {name} {nv}")
    
    return list(set(variants))


def extract_people_improved(comment, fio_list):
    """
    Улучшенная версия поиска людей в комментарии.
    Учитывает падежи и частичные совпадения.
    """
    text = norm(comment)
    found = []
    
    for fio in fio_list:
        variants = short_versions(fio)
        
        for v in variants:
            if len(v) < 3:
                continue
            
            # Прямое вхождение
            if v in text:
                found.append(fio)
                break
            
            # Нечеткое сравнение
            score = fuzz.partial_ratio(v, text)
            if score >= 85:
                found.append(fio)
                break
            
            # Специальная проверка для "с [фамилией]" конструкции
            pattern = rf"с\s+{re.escape(v)}"
            if re.search(pattern, text):
                found.append(fio)
                break
    
    return list(set(found))


# =========================================================
# SINGLE ROOM LIST
# =========================================================
SINGLE_ROOM_PEOPLE = [
    "Макаров В.А. – МГУ", "Пирогов Ю.А. – МГУ", "Пятаков А.П. – МГУ",
    "Руденко О.В. – академик, МГУ", "Сазонов С.В. – НИЦ «Курчатовский институт»",
    "Сапожников О.А. – МГУ", "Тимофеев И.В. – ИФ СО РАН",
    "Храмов А.Е. – РЭУ им. Г.В. Плеханова", "Цысарь С.А. – МГУ",
    "Чашечкин Ю.Д. – ИПМех РАН", "Черепенин В.А. – академик, ИРЭ РАН",
    "Шандаров С.М. – ТУСУР", "Козарь А.В. – МГУ (председатель)",
    "Калиш А.Н. – МГУ (секретарь)", "Архипов Р.М. – ФТИ им. А.Ф. Иоффе",
    "Балакший В.И. – МГУ", "Белотелов В.И. – МГУ", "Боголюбов А.Н. – МГУ",
    "Бородачев Л.В. – МГУ", "Бугай А.Н. – ОИЯИ", "Денисов В.И. – МГУ",
    "Звездин А.К. – ИОФ РАН", "Игнатьева Д.О. – МГУ", "Короновский А.А. – СГУ",
    "Котова С.П. – Самарский филиал ФИАН",
]

def extract_name_only(full_str):
    if " – " in full_str:
        return full_str.split(" – ")[0]
    return full_str

SINGLE_ROOM_NAMES = [extract_name_only(p) for p in SINGLE_ROOM_PEOPLE]


# =========================================================
# PREFERRED BUILDING
# =========================================================
def detect_preferred_building(comment):
    text = norm(comment)
    if "красный" in text or "1 корпус" in text:
        return "red"
    elif "желтый" in text or "2 корпус" in text:
        return "yellow"
    return None


# =========================================================
# PREFERRED FLOOR (НОВАЯ ФУНКЦИЯ)
# =========================================================
def detect_preferred_floor(comment):
    """
    Определяет желаемый этаж из комментария.
    Возвращает номер этажа (int) или None.
    Поддерживает фразы: "на 1 этаже", "первый этаж", "1 этаж" и т.д.
    """
    text = norm(comment)
    
    # Паттерны для поиска этажа
    patterns = [
        r"на\s+(\d+)\s+этаж",  # "на 1 этаже", "на 2 этаже"
        r"(\d+)\s+этаж",        # "1 этаж", "2 этаж"
        r"первый\s+этаж",       # "первый этаж" -> 1
        r"второй\s+этаж",       # "второй этаж" -> 2
        r"третий\s+этаж",       # "третий этаж" -> 3
        r"четвертый\s+этаж",    # "четвертый этаж" -> 4
        r"пятый\s+этаж",        # "пятый этаж" -> 5
    ]
    
    floor_map = {
        "первый": 1, "второй": 2, "третий": 3,
        "четвертый": 4, "пятый": 5
    }
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            # Если нашли цифру
            if match.group(1).isdigit():
                return int(match.group(1))
            # Если нашли слово "первый" и т.д.
            for word, num in floor_map.items():
                if word in text:
                    return num
    
    # Проверка на "не первый этаж" (игнорируем)
    if "не первый" in text or "не 1" in text:
        return None
    
    return None


def get_floor_from_room_id(room_id):
    """
    Извлекает номер этажа из ID комнаты.
    Примеры:
    - "1-101" -> 1 (первая цифра после дефиса)
    - "101" -> 1 (первая цифра номера)
    - "2-215" -> 2
    - "215" -> 2
    - "301" -> 3
    """
    room_str = str(room_id)
    
    # Если формат "корпус-номер" (например "1-101")
    if '-' in room_str:
        after_hyphen = room_str.split('-')[1]
        if after_hyphen and after_hyphen[0].isdigit():
            return int(after_hyphen[0])
    
    # Если просто номер комнаты (например "101" или "215")
    # Берем первую цифру номера
    digits = re.sub(r'\D', '', room_str)  # оставляем только цифры
    if digits and digits[0].isdigit():
        return int(digits[0])
    
    return None


# =========================================================
# SINGLE TARIFF
# =========================================================
def parse_single_tariff(row, df_original, idx):
    for col in df_original.columns:
        col_norm = norm(col)
        if "тариф" in col_norm or "проживание" in col_norm:
            val = df_original.loc[idx, col]
            if pd.notna(val):
                val_str = str(val).lower()
                if "одномест" in val_str or "single" in val_str:
                    return True
    return False


# =========================================================
# COMMENT PARSER (с добавлением этажа)
# =========================================================
def parse_comment(comment, fio_list, single_tariff_flag=False, person_fio=None):
    text = norm(comment)

    hard = []
    soft = []
    avoid = []
    allocation_variants = []
    room_type = None

    # ROOM TYPE
    if "одномест" in text or "без подсел" in text:
        room_type = 1
    elif "двухмест" in text or "двух-мест" in text or "двуспаль" in text:
        room_type = 2
    elif "трехмест" in text or "трёхмест" in text:
        room_type = 3

    # Одноместный тариф
    if single_tariff_flag:
        room_type = 2
        hard.append("NO_SUBLEASE")

    # Спецсписок
    if person_fio and person_fio in SINGLE_ROOM_NAMES:
        room_type = 1
        hard.append("MUST_BE_SINGLE")

    # Ищем людей
    found_people = extract_people_improved(comment, fio_list)

    # TOGETHER WORDS
    together_words = [
        "вместе", "совместно", "поселить с", "проживание с",
        "заселить с", "с подселением", "с женой", "с мужем", "с супруг",
        "размещение с"
    ]
    if any(w in text for w in together_words):
        hard.extend(found_people)

    # SOFT WORDS
    soft_words = ["желательно", "если возможно", "по возможности", "хотелось бы"]
    if any(w in text for w in soft_words):
        soft.extend(found_people)

    # AVOID
    avoid_words = ["не селить", "не вместе", "не хочу"]
    if any(w in text for w in avoid_words):
        avoid.extend(found_people)

    # PRIORITY VARIANTS
    if "если" in text and "3" in text and len(found_people) >= 2:
        allocation_variants.append({
            "room_type": 3,
            "group": found_people,
            "priority": 1
        })
    if "если" in text and "2" in text and len(found_people) >= 1:
        allocation_variants.append({
            "room_type": 2,
            "group": [found_people[0]],
            "priority": 2
        })

    preferred_building = detect_preferred_building(comment)
    
    # НОВОЕ: определяем желаемый этаж
    preferred_floor = detect_preferred_floor(comment)

    return {
        "hard_group": list(set(hard)),
        "soft_group": list(set(soft)),
        "avoid_group": list(set(avoid)),
        "room_type": room_type,
        "allocation_variants": allocation_variants,
        "preferred_building": preferred_building,
        "preferred_floor": preferred_floor,  # новый ключ
    }


# =========================================================
# MAIN PIPELINE
# =========================================================
def preprocess_guests(df):
    df = normalize_columns(df)

    processed = pd.DataFrame()

    # BASIC
    processed["fio"] = df["ФИО"]
    processed["resident"] = df.get("Выбор тарифа за проживание", "").apply(parse_resident)
    processed["gender"] = processed["fio"].apply(detect_gender)
    processed["city"] = df.get("Город", "UNKNOWN")
    processed["status"] = df.get("Статус", "student")

    # NIGHTS
    processed["nights"] = df.apply(extract_nights, axis=1)
    processed["nights"] = processed.apply(
        lambda row: [] if not row["resident"] else row["nights"],
        axis=1
    )

    # COMMENTS
    fio_list = processed["fio"].tolist()

    comment_col = None
    for c in df.columns:
        c_norm = norm(c)
        if "коммент" in c_norm:
            comment_col = c
            break

    if comment_col is None:
        comments = pd.Series([""] * len(processed))
    else:
        comments = df[comment_col].fillna("")

    # Определяем одноместный тариф
    single_tariff_flags = []
    for idx in df.index:
        flag = parse_single_tariff(df.loc[idx], df, idx)
        single_tariff_flags.append(flag)

    # Парсим комментарии
    parsed = []
    for i, (comment, fio) in enumerate(zip(comments, processed["fio"])):
        parsed.append(
            parse_comment(
                comment,
                fio_list,
                single_tariff_flag=single_tariff_flags[i],
                person_fio=fio
            )
        )

    processed["group_hard"] = [x["hard_group"] for x in parsed]
    processed["group_soft"] = [x["soft_group"] for x in parsed]
    processed["group_avoid"] = [x["avoid_group"] for x in parsed]
    processed["room_type"] = [x["room_type"] for x in parsed]
    processed["allocation_variants"] = [x["allocation_variants"] for x in parsed]
    processed["preferred_building"] = [x["preferred_building"] for x in parsed]
    
    # НОВОЕ ПОЛЕ: желаемый этаж
    processed["preferred_floor"] = [x["preferred_floor"] for x in parsed]

    # Дополнительные флаги
    processed["require_no_subleaser"] = processed["group_hard"].apply(
        lambda x: "NO_SUBLEASE" in x
    )
    processed["must_be_single_room"] = processed["fio"].apply(
        lambda x: x in SINGLE_ROOM_NAMES
    )

    return processed


# =========================================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ФИЛЬТРАЦИИ КОМНАТ ПО ЭТАЖУ
# =========================================================
def filter_rooms_by_floor(rooms, preferred_floor):
    """
    Фильтрует комнаты по желаемому этажу.
    rooms: список словарей с ключом 'id' (например '1-101' или '101')
    preferred_floor: номер этажа (int)
    возвращает отфильтрованный список комнат
    """
    if preferred_floor is None:
        return rooms
    
    filtered = []
    for room in rooms:
        room_id = room.get('id', '')
        floor = get_floor_from_room_id(room_id)
        if floor == preferred_floor:
            filtered.append(room)
    
    return filtered
