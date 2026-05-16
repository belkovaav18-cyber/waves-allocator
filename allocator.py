import pandas as pd
from collections import defaultdict


# =========================================================
# penalties
# =========================================================
def gender_penalty(a, b):
    if not a or not b:
        return 0
    return 10 if a != b else 0


def group_bonus(guest_groups, room):
    """
    soft bonus: если кто-то из группы уже в комнате → поощрение
    """
    if not guest_groups:
        return 0

    occupants = room.get("occupants", set())

    if any(x in occupants for x in guest_groups):
        return -20

    return 0


# =========================================================
# check availability
# =========================================================
def is_free(room, nights):
    """
    проверка вместимости по ночам
    """
    if not nights:
        return False

    calendar = room["calendar"]
    capacity = room["capacity"]

    return all(len(calendar[n]) < capacity for n in nights)


def add(room, guest, nights):
    """
    добавление гостя в комнату
    """
    for n in nights:
        room["calendar"][n].append(guest)

    room["occupants"].add(guest.get("fio"))


# =========================================================
# MAIN
# =========================================================
def allocate_rooms(guests_df, rooms_df):

    # ----------------------------
    # normalize inputs (важно!)
    # ----------------------------
    if isinstance(guests_df, pd.DataFrame):
        guests = guests_df.to_dict("records")
    else:
        guests = list(guests_df)

    if isinstance(rooms_df, pd.DataFrame):
        rooms_raw = rooms_df.to_dict("records")
    else:
        rooms_raw = list(rooms_df)

    # ----------------------------
    # init rooms
    # ----------------------------
    rooms = {}

    for r in rooms_raw:
        rooms[r.get("room_id")] = {
            "capacity": int(r.get("вместимость", 0)),
            "calendar": defaultdict(list),
            "occupants": set(),
            "gender": None
        }

    allocations = []
    rejections = []

    # ----------------------------
    # sort guests (priority first)
    # ----------------------------
    def guest_priority(g):
        return (
            len(g.get("group_hard", [])) == 0,
            g.get("status") != "professor"
        )

    guests = sorted(guests, key=guest_priority)

    # ----------------------------
    # main loop
    # ----------------------------
    for g in guests:

        nights = g.get("nights", [])

        if not nights:
            rejections.append({
                "fio": g.get("fio"),
                "reason": "нет выбранных ночей"
            })
            continue

        best_room = None
        best_score = float("inf")

        for room_id, room in rooms.items():

            if not is_free(room, nights):
                continue

            score = 0
            score += gender_penalty(room.get("gender"), g.get("gender"))
            score += group_bonus(g.get("group_hard", []), room)

            if score < best_score:
                best_score = score
                best_room = room_id

        if best_room is None:
            rejections.append({
                "fio": g.get("fio"),
                "reason": "нет подходящей комнаты"
            })
            continue

        add(rooms[best_room], g, nights)

        allocations.append({
            "fio": g.get("fio"),
            "room": best_room,
            "nights": nights
        })

    return (
        pd.DataFrame(allocations),
        pd.DataFrame(rejections),
        rooms
    )


# =========================================================
# stats
# =========================================================
def build_room_stats(room_state):

    return pd.DataFrame([
        {
            "room_id": rid,
            "people": len(room["occupants"]),
            "capacity": room["capacity"]
        }
        for rid, room in room_state.items()
    ])
