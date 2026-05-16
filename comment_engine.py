import re


def normalize(text):
    return str(text).lower()


# -----------------------------
# FIND PEOPLE BY FUZZY MATCH (простая версия)
# -----------------------------
def find_people(text, fio_list):

    text = normalize(text)

    found = []

    for fio in fio_list:
        parts = fio.lower().split()

        if len(parts) < 2:
            continue

        key = parts[0] + " " + parts[1]

        if key in text:
            found.append(fio)

    return found


# -----------------------------
# ROOM TYPE DETECTION
# -----------------------------
def detect_room_type(text):

    t = normalize(text)

    if "одномест" in t:
        return 1
    if "двухмест" in t:
        return 2
    if "трехмест" in t or "трёхмест" in t:
        return 3

    return None


# -----------------------------
# MAIN PARSER
# -----------------------------
def parse_comment(comment, fio_list):

    text = normalize(comment)

    hard = []
    soft = []
    avoid = []

    # ROOM TYPE
    room_type = detect_room_type(text)

    # ---------------- HARD SIGNALS ----------------
    if any(x in text for x in ["посел", "размест", "совмест", "вместе"]):
        hard += find_people(text, fio_list)

    # ---------------- AVOID SIGNALS ----------------
    if "без подсел" in text or "не с " in text:
        avoid += find_people(text, fio_list)

    # ---------------- SOFT SIGNALS ----------------
    if "если возможно" in text or "если будут места" in text:
        soft += find_people(text, fio_list)

    # cleanup
    hard = list(set(hard))
    soft = list(set(soft))
    avoid = list(set(avoid))

    return {
        "hard_group": hard,
        "soft_group": soft,
        "avoid_group": avoid,
        "room_type": room_type
    }
