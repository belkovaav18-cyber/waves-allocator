import pandas as pd
import re
from rapidfuzz import fuzz
from utils.enrichment import enrich_booking_with_registration


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

def preprocess_guests(df, registration_df=None):
    """
    Препроцессинг гостей из таблицы бронирования
    с опциональным обогащением из таблицы регистрации
    """
    df = normalize_columns(df)
    df = expand_group_bookings(df)
    # ===== ДОБАВИТЬ ЭТОТ БЛОК =====
    # Удаляем дубликаты по ФИО
    df = remove_duplicates_smart(df)
    # ==============================

    processed = pd.DataFrame()

    # BASIC
    processed["fio"] = df["ФИО"]
    # ... остальной код ...
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
    
    # ДОБАВИТЬ: вариант с обратным порядком (Имя Фамилия)
    variants.append(f"{name} {surname}")
    if patronymic:
        variants.append(f"{name} {patronymic} {surname}")
        variants.append(f"{name} {surname} {patronymic}")
    
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
    
    # Создаем словарь для быстрого поиска по фамилии
    surname_map = {}
    name_map = {}
    for fio in fio_list:
        fio_norm = norm(fio)
        parts = fio_norm.split()
        if len(parts) >= 1:
            surname = parts[0]
            if surname not in surname_map:
                surname_map[surname] = []
            surname_map[surname].append(fio)
        
        if len(parts) >= 2:
            name = parts[1]
            if name not in name_map:
                name_map[name] = []
            name_map[name].append(fio)
    
    # Ищем по полному совпадению
    for fio in fio_list:
        fio_norm = norm(fio)
        if fio_norm in text:
            found.append(fio)
            continue
        
        # Ищем по фамилии + первой букве имени
        parts = fio_norm.split()
        if len(parts) >= 2:
            surname = parts[0]
            name_initial = parts[1][0] if parts[1] else ""
            pattern = rf"{surname}\s+{name_initial}[\.]?"
            if re.search(pattern, text):
                found.append(fio)
                continue
        
        # Ищем по фамилии
        if len(parts) >= 1:
            surname = parts[0]
            if surname in text and len(surname) > 3:
                # Проверяем, не перепутали ли с другой фамилией
                possible_matches = surname_map.get(surname, [])
                if len(possible_matches) == 1:
                    found.append(fio)
                    continue
    
    # ДОБАВИТЬ: поиск по измененным падежным формам
    for fio in fio_list:
        if fio in found:
            continue
        
        fio_norm = norm(fio)
        parts = fio_norm.split()
        
        if len(parts) >= 1:
            surname = parts[0]
            
            # Ищем фамилию в тексте (в любом падеже)
            surname_variants = [surname]
            
            # Варианты окончаний для фамилий
            if surname.endswith('в') or surname.endswith('н'):
                surname_variants.append(surname + 'а')
                surname_variants.append(surname + 'у')
                surname_variants.append(surname + 'ым')
                surname_variants.append(surname + 'ом')
            elif surname.endswith('й'):
                surname_variants.append(surname[:-1] + 'я')
                surname_variants.append(surname[:-1] + 'ю')
                surname_variants.append(surname[:-1] + 'ем')
            elif surname.endswith('а'):
                surname_variants.append(surname[:-1] + 'ы')
                surname_variants.append(surname[:-1] + 'е')
                surname_variants.append(surname[:-1] + 'у')
                surname_variants.append(surname[:-1] + 'ой')
            
            for surname_var in surname_variants:
                if surname_var in text:
                    # Проверяем, есть ли в тексте имя или инициал
                    if len(parts) >= 2:
                        name = parts[1]
                        name_initial = name[0]
                        # Ищем инициал
                        if name_initial in text or name in text:
                            found.append(fio)
                            break
                    else:
                        found.append(fio)
                        break
    
    # Используем fuzzy поиск для остальных
    for fio in fio_list:
        if fio in found:
            continue
        
        variants = short_versions(fio)
        for v in variants:
            if len(v) < 3:
                continue
            
            score = fuzz.partial_ratio(v, text)
            if score >= 85:
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

# utils/preprocess.py - добавить функцию и изменить MAIN PIPELINE

# =========================================================
# REMOVE DUPLICATES
# =========================================================
def remove_duplicates_by_fio(df):
    """
    Удаляет дубликаты по ФИО, оставляя первую запись
    и объединяя комментарии при необходимости
    """
    df = df.copy()
    
    # Нормализуем ФИО для сравнения
    df['fio_normalized'] = df['ФИО'].apply(lambda x: re.sub(r'\s+', ' ', str(x).strip().lower()))
    
    # Находим дубликаты
    duplicates = df[df.duplicated('fio_normalized', keep=False)]
    
    if len(duplicates) > 0:
        print(f"Найдено дубликатов: {len(duplicates)}")
        
        # Группируем по нормализованному ФИО
        grouped = []
        for fio_norm, group in df.groupby('fio_normalized'):
            if len(group) > 1:
                # Берем первую запись как основную
                main_row = group.iloc[0].copy()
                
                # Объединяем комментарии, если они разные
                comments = []
                for _, row in group.iterrows():
                    comment_col = None
                    for col in df.columns:
                        if 'коммент' in str(col).lower():
                            comment_col = col
                            break
                    if comment_col and pd.notna(row[comment_col]) and str(row[comment_col]).strip():
                        comments.append(str(row[comment_col]).strip())
                
                if comments and comment_col:
                    main_row[comment_col] = '; '.join(set(comments))
                
                grouped.append(main_row)
            else:
                grouped.append(group.iloc[0])
        
        result_df = pd.DataFrame(grouped)
        result_df = result_df.drop(columns=['fio_normalized'])
        print(f"После удаления дубликатов осталось: {len(result_df)} записей")
        return result_df
    else:
        df = df.drop(columns=['fio_normalized'])
        return df


# =========================================================
# NORMALIZE FIO (для поиска дубликатов с разным написанием)
# =========================================================
def normalize_fio_for_deduplication(fio):
    """
    Нормализует ФИО для поиска дубликатов с разным написанием
    Например: "Ким Пётр Николаевич" и "Ким Петр Николаевич"
    """
    if pd.isna(fio):
        return ""
    
    fio = str(fio).lower()
    
    # Заменяем ё на е
    fio = fio.replace('ё', 'е')
    
    # Убираем точки и лишние пробелы
    fio = re.sub(r'\.', '', fio)
    fio = re.sub(r'\s+', ' ', fio).strip()
    
    return fio


def remove_duplicates_smart(df):
    """
    Умное удаление дубликатов с учетом разных написаний
    (Пётр vs Петр, наличие/отсутствие отчества)
    """
    df = df.copy()
    
    # Нормализуем для поиска
    df['fio_key'] = df['ФИО'].apply(normalize_fio_for_deduplication)
    
    # Разбиваем на части
    def get_key_parts(fio_key):
        parts = fio_key.split()
        if len(parts) >= 2:
            return (parts[0], parts[1])  # Фамилия и имя как ключ
        return (fio_key,)
    
    df['fio_key_parts'] = df['fio_key'].apply(get_key_parts)
    
    # Группируем по фамилии и имени
    grouped = []
    processed_keys = set()
    
    for idx, row in df.iterrows():
        key_parts = row['fio_key_parts']
        
        if key_parts in processed_keys:
            continue
        
        # Находим все похожие записи
        similar = df[df['fio_key_parts'] == key_parts]
        
        if len(similar) > 1:
            # Берем запись с наиболее полным ФИО
            similar['name_length'] = similar['ФИО'].apply(lambda x: len(str(x).split()))
            best_idx = similar['name_length'].idxmax()
            main_row = similar.loc[best_idx].copy()
            
            # Объединяем комментарии
            comment_col = None
            for col in df.columns:
                if 'коммент' in str(col).lower():
                    comment_col = col
                    break
            
            if comment_col:
                comments = []
                for _, sim_row in similar.iterrows():
                    if pd.notna(sim_row[comment_col]) and str(sim_row[comment_col]).strip():
                        comments.append(str(sim_row[comment_col]).strip())
                if comments:
                    main_row[comment_col] = '; '.join(set(comments))
            
            grouped.append(main_row)
            processed_keys.add(key_parts)
        else:
            grouped.append(row)
            processed_keys.add(key_parts)
    
    result_df = pd.DataFrame(grouped)
    result_df = result_df.drop(columns=['fio_key', 'fio_key_parts', 'name_length'] if 'name_length' in result_df.columns else ['fio_key', 'fio_key_parts'])
    
    print(f"Умное удаление дубликатов: {len(df)} -> {len(result_df)} записей")
    return result_df


# =========================================================
# MAIN PIPELINE
# =========================================================
def preprocess_guests(df, registration_df=None):
    """
    Препроцессинг гостей из таблицы бронирования
    с опциональным обогащением из таблицы регистрации
    """
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

    # ОБОГАЩЕНИЕ ДАННЫМИ ИЗ РЕГИСТРАЦИИ
    if registration_df is not None and not registration_df.empty:
        processed = enrich_booking_with_registration(processed, registration_df)
        print("Данные обогащены из таблицы регистрации")

    return processed

# =========================================================
# SPLIT GROUP BOOKINGS (разбиение групповых бронирований)
# =========================================================

def split_group_booking(fio_string):
    """
    Разбивает строку с несколькими ФИО на отдельные записи.
    Например: "Вьюгинова А.А., Новик А.А., Вьюгинов С.Н." -> список ФИО
    """
    if pd.isna(fio_string):
        return [fio_string]
    
    fio_str = str(fio_string)
    
    # Разделители: запятая, "и", перевод строки
    separators = [',', 'и,', 'и', '\n', ';', '/']
    
    # Проверяем наличие разделителей
    has_separator = any(sep in fio_str for sep in separators)
    
    if not has_separator:
        # Проверяем наличие нескольких людей в формате "ФИО1 (роль), ФИО2 (роль)"
        if '),' in fio_str or ') ,' in fio_str:
            has_separator = True
    
    if has_separator:
        # Разбиваем по запятым
        parts = re.split(r'[,;]|\s+и\s+', fio_str)
        result = []
        for part in parts:
            part = part.strip()
            # Убираем роли в скобках
            part = re.sub(r'\s*\([^)]*\)', '', part)
            # Убираем лишние пробелы
            part = re.sub(r'\s+', ' ', part)
            if part and len(part) > 5:  # Минимальная длина ФИО
                result.append(part)
        
        if len(result) > 1:
            return result
    
    return [fio_string]


def expand_group_bookings(df):
    """
    Разворачивает групповые бронирования в отдельные строки.
    Каждый человек получает свою копию строки с тем же комментарием и тарифом.
    """
    expanded_rows = []
    
    for idx, row in df.iterrows():
        fio = row.get('ФИО', '')
        if pd.isna(fio):
            continue
        
        # Разбиваем групповую запись
        individuals = split_group_booking(fio)
        
        if len(individuals) > 1:
            # Для каждого человека создаем отдельную строку
            for individual in individuals:
                new_row = row.copy()
                new_row['ФИО'] = individual
                expanded_rows.append(new_row)
            
            print(f"Разбита групповая запись '{fio}' на {len(individuals)} человек: {individuals}")
        else:
            # Обычная запись
            expanded_rows.append(row)
    
    result_df = pd.DataFrame(expanded_rows)
    print(f"Развернуто групповых бронирований: {len(df)} -> {len(result_df)} записей")
    return result_df
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
