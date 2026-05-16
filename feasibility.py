def max_room_capacity(rooms):
    return max(int(r["вместимость"]) for r in rooms)


def find_impossible_groups(guests, rooms):

    max_cap = max_room_capacity(rooms)
    problems = []

    for g in guests:
        group = g.get("group_hard", [])
        size = len(group) + 1

        if size > max_cap:
            problems.append({
                "fio": g["fio"],
                "group_size": size,
                "max_room": max_cap
            })

    return problems


def split_groups(guests, rooms):

    max_cap = max_room_capacity(rooms)
    result = []

    for g in guests:

        group = g.get("group_hard", [])
        full = [g["fio"]] + group

        if len(full) <= max_cap:
            result.append(g)
            continue

        chunks = [
            full[i:i + max_cap]
            for i in range(0, len(full), max_cap)
        ]

        for c in chunks:
            new_g = g.copy()
            new_g["fio"] = c[0]
            new_g["group_hard"] = c[1:]
            result.append(new_g)

    return result


def explain_fail(guests, rooms):

    max_cap = max_room_capacity(rooms)
    reasons = []

    for g in guests:
        if len(g.get("nights", [])) == 0:
            reasons.append((g["fio"], "нет выбранных ночей"))
            continue

        if len(g.get("group_hard", [])) + 1 > max_cap:
            reasons.append((g["fio"], "группа не помещается"))
            continue

    return reasons
