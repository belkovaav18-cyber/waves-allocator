import pandas as pd
from collections import defaultdict


# ----------------------------
# PENALTIES (soft constraints)
# ----------------------------

def age_penalty(a, b):
    if not a or not b:
        return 0
    diff = abs(a - b)
    if diff > 30:
        return 2
    if diff > 20:
        return 1
    return 0


def status_penalty(a, b):
    if a == b:
        return 0
    if "professor" in (a, b):
        return 1
    return 1


def city_penalty(a, b):
    if not a or not b:
        return 0
    return 0 if a == b else 1


def gender_penalty(room_gender, guest_gender):
    if room_gender and room_gender != guest_gender:
        return 10
    return 0


# ----------------------------
# CHECK ROOM FREE
# ----------------------------

def is_free(room, nights, guest_id):
    for n in nights:
        if len(room["calendar"][n]) >= room["capacity"]:
            return False
    return True


def add_guest(room, guest, nights):
    for n in nights:
        room["calendar"][n].append(guest)

    room["occupants"].add(guest["fio"])

    if room["gender"] is None:
        room["gender"] = guest["gender"]


# ----------------------------
# MAIN ALLOCATOR
# ----------------------------

def allocate_rooms(guests_df, rooms_df):

    rooms = {}

    for r in rooms_df:
        rooms[r["room_id"]] = {
            "capacity": int(r["вместимость"]),
            "calendar": defaultdict(list),
            "gender": None,
            "occupants": set(),
        }

    # сортировка: сначала преподаватели, потом старшие (если есть возраст)
    guests_df = sorted(
        guests_df,
        key=lambda g: (
            g.get("status") != "professor"
        )
    )

    allocations = []
    rejections = []

    for g in guests_df:

        nights = g["nights"]

        best_room = None
        best_score = float("inf")

        for room_id, room in rooms.items():

            if not is_free(room, nights, g["id"]):
                continue

            score = 0

            # сильный штраф за пол
            score += gender_penalty(room["gender"], g["gender"])

            # мягкие конфликты с текущими жильцами
            for occupant in room["occupants"]:

                # (упрощённо — без age lookup, можно расширить позже)
                score += city_penalty(g["city"], g["city"])

            if score < best_score:
                best_score = score
                best_room = room_id

        if best_room is None:
            rejections.append({
                "fio": g["fio"],
                "reasons": ["нет подходящей комнаты"]
            })
            continue

        add_guest(rooms[best_room], g, nights)

        allocations.append({
            "fio": g["fio"],
            "room": best_room,
            "nights": nights
        })

    return pd.DataFrame(allocations), pd.DataFrame(rejections), rooms


# ----------------------------
# STATS
# ----------------------------

def build_room_stats(room_state):

    res = []

    for room_id, room in room_state.items():

        people = set(room["occupants"])

        res.append({
            "room_id": room_id,
            "people_count": len(people),
            "capacity": room["capacity"]
        })

    return pd.DataFrame(res)
