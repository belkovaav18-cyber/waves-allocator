import itertools


def max_room_capacity(rooms_df):
    return max(int(r["вместимость"]) for r in rooms_df.to_dict("records"))


# =========================================================
# CHECK IMPOSSIBLE GROUPS
# =========================================================
def find_impossible_groups(guests_df, rooms_df):

    max_cap = max_room_capacity(rooms_df)

    problems = []

    for g in guests_df:

        group = g.get("group_hard", [])

        total_size = len(group) + 1

        if total_size > max_cap:

            problems.append({
                "fio": g["fio"],
                "group_size": total_size,
                "max_room": max_cap
            })

    return problems


# =========================================================
# SPLIT LARGE GROUPS (SAFE VERSION)
# =========================================================
def split_groups(guests_df, rooms_df):

    max_cap = max_room_capacity(rooms_df)

    new_guests = []

    for g in guests_df:

        group = g.get("group_hard", [])

        full_group = [g["fio"]] + group

        if len(full_group) <= max_cap:
            new_guests.append(g)
            continue

        # split into chunks
        chunks = [
            full_group[i:i + max_cap]
            for i in range(0, len(full_group), max_cap)
        ]

        for chunk in chunks:

            main = chunk[0]
            rest = chunk[1:]

            new_g = g.copy()
            new_g["fio"] = main
            new_g["group_hard"] = rest

            new_guests.append(new_g)

    return new_guests


# =========================================================
# EXPLAIN WHY NOT PLACED
# =========================================================
def explain_fail(guests_df, rooms_df):

    reasons = []

    max_cap = max_room_capacity(rooms_df)

    for g in guests_df:

        if len(g.get("nights", [])) == 0:
            reasons.append((g["fio"], "нет выбранных ночей"))
            continue

        if len(g.get("group_hard", [])) + 1 > max_cap:
            reasons.append((g["fio"], "группа не помещается в комнату"))
            continue

    return reasons
