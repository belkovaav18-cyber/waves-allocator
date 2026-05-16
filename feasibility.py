def normalize_rooms(rooms_df):

    # DataFrame
    if hasattr(rooms_df, "to_dict"):
        return rooms_df.to_dict("records")

    # already list
    if isinstance(rooms_df, list):
        return rooms_df

    return []


# =========================================================
# MAX CAPACITY
# =========================================================
def max_room_capacity(rooms_df):

    rooms = normalize_rooms(rooms_df)

    return max(int(r.get("вместимость", 0)) for r in rooms)


# =========================================================
# CHECK IMPOSSIBLE GROUPS
# =========================================================
def find_impossible_groups(guests_df, rooms_df):

    rooms = normalize_rooms(rooms_df)
    max_cap = max(int(r.get("вместимость", 0)) for r in rooms)

    problems = []

    for g in guests_df:

        group = g.get("group_hard", [])
        total = len(group) + 1

        if total > max_cap:
            problems.append({
                "fio": g.get("fio"),
                "group_size": total,
                "max_room": max_cap
            })

    return problems


# =========================================================
# SPLIT LARGE GROUPS
# =========================================================
def split_groups(guests_df, rooms_df):

    rooms = normalize_rooms(rooms_df)
    max_cap = max(int(r.get("вместимость", 0)) for r in rooms)

    new_guests = []

    for g in guests_df:

        group = g.get("group_hard", [])
        full = [g.get("fio")] + group

        if len(full) <= max_cap:
            new_guests.append(g)
            continue

        chunks = [
            full[i:i + max_cap]
            for i in range(0, len(full), max_cap)
        ]

        for chunk in chunks:
            new_g = g.copy()
            new_g["fio"] = chunk[0]
            new_g["group_hard"] = chunk[1:]
            new_guests.append(new_g)

    return new_guests


# =========================================================
# EXPLANATION
# =========================================================
def explain_fail(guests_df, rooms_df):

    rooms = normalize_rooms(rooms_df)

    max_cap = max(int(r.get("вместимость", 0)) for r in rooms)

    reasons = []

    for g in guests_df:

        if not g.get("nights"):
            reasons.append((g.get("fio"), "нет выбранных ночей"))

        elif len(g.get("group_hard", [])) + 1 > max_cap:
            reasons.append((g.get("fio"), "группа не помещается"))

    return reasons
