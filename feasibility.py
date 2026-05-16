import itertools


def max_room_capacity(rooms_df):
    return max(int(r["вместимость"]) for r in rooms_df.to_dict("records"))


# =========================================================
# CHECK IMPOSSIBLE GROUPS
# =========================================================
def ensure_dict(g):
    return isinstance(g, dict)


def max_room_capacity(rooms_df):
    return max(int(r["вместимость"]) for r in rooms_df.to_dict("records"))


def find_impossible_groups(guests_df, rooms_df):

    max_cap = max_room_capacity(rooms_df)

    problems = []

    for g in guests_df:

        if not ensure_dict(g):
            continue

        group = g.get("group_hard", [])

        if not isinstance(group, list):
            group = []

        total = len(group) + 1

        if total > max_cap:

            problems.append({
                "fio": g.get("fio"),
                "group_size": total,
                "max_room": max_cap
            })

    return problems


def split_groups(guests_df, rooms_df):

    max_cap = max_room_capacity(rooms_df)

    new_guests = []

    for g in guests_df:

        if not isinstance(g, dict):
            continue

        group = g.get("group_hard", [])

        if not isinstance(group, list):
            group = []

        full = [g.get("fio")] + group

        if len(full) <= max_cap:
            new_guests.append(g)
            continue

        chunks = [full[i:i + max_cap] for i in range(0, len(full), max_cap)]

        for chunk in chunks:

            new_g = dict(g)
            new_g["fio"] = chunk[0]
            new_g["group_hard"] = chunk[1:]

            new_guests.append(new_g)

    return new_guests


def explain_fail(guests_df, rooms_df):

    reasons = []

    max_cap = max_room_capacity(rooms_df)

    for g in guests_df:

        if not isinstance(g, dict):
            continue

        nights = g.get("nights", [])

        if not nights:
            reasons.append((g.get("fio"), "нет ночей"))
            continue

        if len(g.get("group_hard", [])) + 1 > max_cap:
            reasons.append((g.get("fio"), "группа не помещается"))
            continue

    return reasons
