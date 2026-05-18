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
# TARIFF TYPE PARSER (НОВАЯ ФУНКЦИЯ)
# =========================================================
def parse_tariff_type(v):
    """
    Определяет тип тарифа:
    - "without_subleaser" - размещение без подселения
    - "with_subleaser" - размещение с подселением
    - None - не определен
    """
    if pd.isna(v):
        return None
    
    v_str = str(v).lower()
    
    if "без подсел" in v_str:
        return "without_subleaser"
    elif "с подсел" in v_str:
        return "with_subleaser"
    
    return None


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
    """Генерирует разные варианты написания ФИО для поиска"""
    fio = norm(fio)
    parts = fio.split()
    
    if len(parts) < 2:
        return []
    
    surname = parts[0]
    name = parts[1] if len(parts) > 1 else ""
    patronymic = parts[2] if len(parts) > 2 else ""
    
    variants = [
        fio,
        surname,
        f"{surname} {name}",
        f"{surname} {name[0]}.{patronymic[0]}." if patronymic else f"{surname} {name[0]}.",
        f"{surname} {name[0]}.{patronymic[0]}" if patronymic else f"{surname} {name[0]}",
        f"{surname} {name[0]}",
    ]
    
    # Варианты с падежными окончаниями
    name_variants = []
    if name.endswith("а"):
        name_variants.append(name[:-1] + "ы")
        name_variants.append(name[:-1] + "е")
        name_variants.append(name[:-1] + "у")
        name_variants.append(name[:-1] + "ой")
    
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
    """Улучшенная версия поиска людей в комментарии"""
    text = norm(comment)
    found = []
    
    for fio in fio_list:
        variants = short_versions(fio)
        
        for v in variants:
            if len(v) < 3:
                continue
            
            if v in text:
                found.append(fio)
                break
            
            score = fuzz.partial_ratio(v, text)
            if score >= 85:
                found.append(fio)
                break
            
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
# PREFERRED BUILDING FOR SPECIFIC PEOPLE
# =========================================================
YELLOW_BUILDING_PEOPLE = [
    "Калиш А.Н.", "Калиш", "Цысарь С.А.", "Цысарь",
    "Князев", "Безменова", "Отинова", "Зорина", "Дьяконов",
    "Каминский", "Крохмаль", "Лапина", "Снигирёв", "Груняшина",
    "Кабак", "Коньков", "Кукушкин", "Левкин", "Трунцов",
    "Юшков", "Останин", "Львов"
]

YELLOW_BUILDING_NAMES_NORM = [norm(name) for name in YELLOW_BUILDING_PEOPLE]


def detect_forced_building(fio):
    """Определяет принудительный корпус для определенных людей"""
    fio_norm = norm(fio)
    
    for name in YELLOW_BUILDING_NAMES_NORM:
        if name in fio_norm or fio_norm.startswith(name):
            return "yellow"
    
    return None


# =========================================================
# PREFERRED BUILDING
# =========================================================
def detect_preferred_building(comment, fio=None):
    """Определяет желаемый корпус из комментария или из принудительного списка"""
    if fio:
        forced = detect_forced_building(fio)
        if forced:
            return forced
    
    text = norm(comment)
    if "красный" in text or "1 корпус" in text:
        return "red"
    elif "желтый" in text or "2 корпус" in text:
        return "yellow"
    
    return None


# =========================================================
# PREFERRED FLOOR
# =========================================================
def detect_preferred_floor(comment):
    """Определяет желаемый этаж из комментария"""
    text = norm(comment)
    
    patterns = [
        r"на\s+(\d+)\s+этаж",
        r"(\d+)\s+этаж",
        r"первый\s+этаж",
        r"второй\s+этаж",
        r"третий\s+этаж",
        r"четвертый\s+этаж",
        r"пятый\s+этаж",
    ]
    
    floor_map = {
        "первый": 1, "второй": 2, "третий": 3,
        "четвертый": 4, "пятый": 5
    }
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            if match.group(1).isdigit():
                return int(match.group(1))
            for word, num in floor_map.items():
                if word in text:
                    return num
    
    return None


def get_floor_from_room_id(room_id):
    """Извлекает номер этажа из ID комнаты"""
    room_str = str(room_id)
    
    if '-' in room_str:
        after_hyphen = room_str.split('-')[1]
        if after_hyphen and after_hyphen[0].isdigit():
            return int(after_hyphen[0])
    
    digits = re.sub(r'\D', '', room_str)
    if digits and digits[0].isdigit():
        return int(digits[0])
    
    return None


# =========================================================
# SINGLE TARIFF (старая функция для одноместного тарифа)
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
# COMMENT PARSER
# =========================================================
def parse_comment(comment, fio_list, single_tariff_flag=False, person_fio=None, tariff_type=None):
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

    # Одноместный тариф (старая логика)
    if single_tariff_flag:
        room_type = 2
        hard.append("NO_SUBLEASE")

    # НОВАЯ ЛОГИКА: тариф "без подселения"
    if tariff_type == "without_subleaser":
        # Селятся в двуместные номера, но без подселения других
        room_type = 2
        hard.append("NO_SUBLEASE")
    
    # НОВАЯ ЛОГИКА: тариф "с подселением"
    if tariff_type == "with_subleaser":
        # Селятся в двуместные номера, можно подселять других
        room_type = 2
        # Не добавляем ограничение NO_SUBLEASE

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

    preferred_building = detect_preferred_building(comment, person_fio)
    preferred_floor = detect_preferred_floor(comment)

    return {
        "hard_group": list(set(hard)),
        "soft_group": list(set(soft)),
        "avoid_group": list(set(avoid)),
        "room_type": room_type,
        "allocation_variants": allocation_variants,
        "preferred_building": preferred_building,
        "preferred_floor": preferred_floor,
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

    # НОВОЕ: определяем тип тарифа
    processed["tariff_type"] = df.get("Выбор тарифа за проживание", "").apply(parse_tariff_type)

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

    # Определяем одноместный тариф (старая логика)
    single_tariff_flags = []
    for idx in df.index:
        flag = parse_single_tariff(df.loc[idx], df, idx)
        single_tariff_flags.append(flag)

    # Парсим комментарии с учетом типа тарифа
    parsed = []
    for i, (comment, fio, tariff_type) in enumerate(zip(comments, processed["fio"], processed["tariff_type"])):
        parsed.append(
            parse_comment(
                comment,
                fio_list,
                single_tariff_flag=single_tariff_flags[i],
                person_fio=fio,
                tariff_type=tariff_type
            )
        )

    processed["group_hard"] = [x["hard_group"] for x in parsed]
    processed["group_soft"] = [x["soft_group"] for x in parsed]
    processed["group_avoid"] = [x["avoid_group"] for x in parsed]
    processed["room_type"] = [x["room_type"] for x in parsed]
    processed["allocation_variants"] = [x["allocation_variants"] for x in parsed]
    processed["preferred_building"] = [x["preferred_building"] for x in parsed]
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
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ФИЛЬТРАЦИИ
# =========================================================
def filter_rooms_by_floor(rooms, preferred_floor):
    """Фильтрует комнаты по желаемому этажу"""
    if preferred_floor is None:
        return rooms
    
    filtered = []
    for room in rooms:
        room_id = room.get('id', '')
        floor = get_floor_from_room_id(room_id)
        if floor == preferred_floor:
            filtered.append(room)
    
    return filtered


def filter_rooms_by_building(rooms, preferred_building):
    """Фильтрует комнаты по желаемому корпусу"""
    if preferred_building is None:
        return rooms
    
    filtered = []
    for room in rooms:
        room_id = room.get('room_id', '')
        room_str = str(room_id)
        
        if preferred_building == "yellow":
            if room_str.startswith('2-') or room_str.startswith('2'):
                filtered.append(room)
        elif preferred_building == "red":
            if room_str.startswith('1-') or room_str.startswith('1'):
                filtered.append(room)
    
    return filtered
