import pandas as pd
from collections import defaultdict


# -------------------------
# penalties
# -------------------------
def gender_penalty(a, b):
    return 10 if a and b and a != b else 0


def group_penalty(g, room):
    if not g:
        return 0

    # если в комнате уже есть кто-то из группы → бонус
    existing = room["occupants"]

    if any(x in existing for x in g):
        return -5  # поощрение совместного заселения

    return 0


# -------------------------
# check free
# -------------------------
def is_free(room, nights):
    return all(len(room["calendar"][n]) < room["capacity"] for n in nights)


def add(room, guest, nights):
    for n in nights:
        room["calendar"][n].append(guest)

    room["occupants"].add(guest["fio"])


# -------------------------
# main allocator
# -------------------------
def allocate_rooms(guests_df, rooms_df):

    rooms = {}

    for r in rooms_df:
        rooms[r["room_id"]] = {
            "capacity": int(r["вместимость"]),
            "calendar": defaultdict(list),
            "occupants": set(),
            "gender": None
        }

    allocations = []
    rejections = []

    # сначала группы и преподаватели
    guests_df = sorted(
        guests_df,
        key=lambda g: (
            len(g.get("group", [])) == 0,
            g.get("status") != "professor"
        )
    )

    for g in guests_df:

        nights = g["nights"]

        best_room = None
        best_score = 10**9

        for room_id, room in rooms.items():

            if not is_free(room, nights):
                continue

            score = 0

            score += gender_penalty(room["gender"], g["gender"])
            score += group_penalty(g.get("group"), room)

            if score < best_score:
                best_score = score
                best_room = room_id

        if best_room is None:
            rejections.append({
                "fio": g["fio"],
                "reason": "нет подходящей комнаты"
            })
            continue

        add(rooms[best_room], g, nights)

        allocations.append({
            "fio": g["fio"],
            "room": best_room,
            "nights": nights
        })

    return pd.DataFrame(allocations), pd.DataFrame(rejections), rooms


# -------------------------
# stats
# -------------------------
def build_room_stats(room_state):

    res = []

    for room_id, room in room_state.items():
        res.append({
            "room_id": room_id,
            "people": len(room["occupants"]),
            "capacity": room["capacity"]
        })

    return pd.DataFrame(res)
