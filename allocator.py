import pandas as pd
from collections import defaultdict


# =========================================================
# penalties
# =========================================================
def gender_penalty(a, b):
    return 10 if a and b and a != b else 0


def group_bonus(guest_groups, room):
    if not guest_groups:
        return 0

    if any(x in room["occupants"] for x in guest_groups):
        return -20

    return 0


# =========================================================
# check availability
# =========================================================
def is_free(room, nights):
    return all(
        len(room["calendar"][n]) < room["capacity"]
        for n in nights
    )


def add(room, guest, nights):

    for n in nights:
        room["calendar"][n].append(guest)

    room["occupants"].add(guest["fio"])


# =========================================================
# MAIN
# =========================================================
def allocate_rooms(guests_df, rooms_df):

    rooms = {}

    for r in rooms_df.to_dict("records"):
        rooms[r["room_id"]] = {
            "capacity": int(r["вместимость"]),
            "calendar": defaultdict(list),
            "occupants": set(),
            "gender": None
        }

    allocations = []
    rejections = []

    # сначала важные
    guests_df = sorted(
        guests_df,
        key=lambda g: (
            len(g.get("group_hard", [])) == 0,
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
            score += group_bonus(g.get("group_hard"), room)

            if score < best_score:
                best_score = score
                best_room = room_id

        if best_room is None:
            rejections.append({
                "fio": g["fio"],
                "reason": "нет комнаты"
            })
            continue

        add(rooms[best_room], g, nights)

        allocations.append({
            "fio": g["fio"],
            "room": best_room,
            "nights": g["nights"]
        })

    return pd.DataFrame(allocations), pd.DataFrame(rejections), rooms


def build_room_stats(room_state):

    return pd.DataFrame([
        {
            "room_id": rid,
            "people": len(room["occupants"]),
            "capacity": room["capacity"]
        }
        for rid, room in room_state.items()
    ])
