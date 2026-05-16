import re
from difflib import get_close_matches


# =========================================================
# UTIL: normalize
# =========================================================
def norm(text):
    return re.sub(r"\s+", " ", str(text).lower().strip())


# =========================================================
# FUZZY MATCH FIO
# =========================================================
def match_fio(text, fio_list, cutoff=0.75):

    text = norm(text)
    matches = []

    for fio in fio_list:

        fio_n = norm(fio)

        # match by surname (first word)
        surname = fio_n.split()[0]

        if surname in text:
            matches.append(fio)
            continue

        # fuzzy fallback
        best = get_close_matches(fio_n, [text], n=1, cutoff=cutoff)

        if best:
            matches.append(fio)

    return list(set(matches))


# =========================================================
# MAIN PARSER
# =========================================================
def parse_comment(comment, fio_list):

    text = norm(comment)

    result = {
        "hard_group": [],
        "soft_group": [],
        "avoid_group": [],
        "room_type": None
    }

    # =====================================================
    # ROOM TYPE RULES
    # =====================================================
    if "одномест" in text:
        result["room_type"] = 1

    elif "двухмест" in text or "2-мест" in text:
        result["room_type"] = 2

    elif "трёхмест" in text or "3-мест" in text:
        result["room_type"] = 3

    # =====================================================
    # HARD GROUP
    # =====================================================
    if "вместе с" in text or "поселить с" in text:

        matches = match_fio(comment, fio_list)
        result["hard_group"].extend(matches)

    # =====================================================
    # SOFT GROUP
    # =====================================================
    if "желательно вместе" in text or "по возможности с" in text:

        matches = match_fio(comment, fio_list)
        result["soft_group"].extend(matches)

    # =====================================================
    # AVOID GROUP
    # =====================================================
    if "не селить с" in text or "не вместе с" in text:

        matches = match_fio(comment, fio_list)
        result["avoid_group"].extend(matches)

    return result
