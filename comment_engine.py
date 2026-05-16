import re


def normalize(t):
    return str(t).lower()


def clean_fio(fio):
    fio = fio.lower()

    fio = re.sub(r"\.", " ", fio)
    fio = re.sub(r"\s+", " ", fio).strip()

    parts = fio.split()
    if len(parts) < 2:
        return None

    return parts[0], parts[1]


def match_fio(text, fio):
    text = normalize(text)

    cleaned = clean_fio(fio)
    if not cleaned:
        return False

    surname, name = cleaned

    # LEVEL 1: фамилия + имя встречаются
    if surname in text and name in text:
        return True

    # LEVEL 2: только фамилия (очень важно для комментариев)
    if surname in text:
        return True

    return False


def find_people(text, fio_list):
    found = []

    for fio in fio_list:
        if match_fio(text, fio):
            found.append(fio)

    return list(set(found))


def detect_room_type(text):

    t = normalize(text)

    if "одномест" in t:
        return 1
    if "двухмест" in t:
        return 2
    if "трехмест" in t or "трёхмест" in t:
        return 3

    return None


def parse_comment(comment, fio_list):

    text = normalize(comment)

    hard = []
    soft = []
    avoid = []

    room_type = detect_room_type(text)

    # ---------------- HARD ----------------
    if any(x in text for x in ["посел", "совмест", "вместе", "размест"]):
        hard += find_people(text, fio_list)

    # ---------------- AVOID ----------------
    if "без подсел" in text:
        avoid += find_people(text, fio_list)

    # ---------------- SOFT ----------------
    if "если возможно" in text or "если будут места" in text:
        soft += find_people(text, fio_list)

    return {
        "hard_group": list(set(hard)),
        "soft_group": list(set(soft)),
        "avoid_group": list(set(avoid)),
        "room_type": room_type
    }
