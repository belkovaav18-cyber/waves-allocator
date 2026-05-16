import pandas as pd
from collections import defaultdict


# -------------------------
# convert date safely
# -------------------------
def to_day(x):
    if pd.isna(x):
        return None
    if isinstance(x, pd.Timestamp):
        return x.day
    try:
        return int(x)
    except:
        return None


def allocate_rooms(guests_df, rooms_df):

    allocations = []
    rejections = []

    # -------------------------
    # rooms state
    # -------------------------
    rooms = {}

    for r in rooms_df:
        rooms[r["room_id"]] = {
            "capacity": int(r["вместимость"]),
            "calendar": defaultdict(list),
            "gender": None,
            "cities": set(),
            "families": set(),
        }

    # -------------------------
    # sort priority
    # -------------------------
    guests_df = sorted(
        guests_df,
        key=lambda g: (
            g.get("status") != "professor",
            -(g.get("age") or 0)
        )
    )

    # -------------------------
    def is_free(room, start, end):
        for d in range(start, end + 1):
            if len(room["calendar"][d]) >= room["capacity"]:
                return False
        return True

    def add(room, g, start, end):
        for d in range(start, end + 1):
            room["calendar"][d].append(g)

        room["cities"].add(g.get("city"))
        room["families"].add(g.get("family_id"))

    # -------------------------
    # main loop
    # -------------------------
    for g in guests_df:

        start = to_day(g.get("checkin"))
        end = to_day(g.get("checkout"))

        if start is None or end is None:
            rejections.append({
                "fio": g["fio"],
                "reasons": ["нет дат заезда/выезда"]
            })
            continue

        placed = False
        reasons = []

        for room_id, room in rooms.items():

            if is_free(room, start, end):

                # soft rule: gender mix penalty
                if room["gender"] and room["gender"] != g["gender"]:
                    reasons.append("разный пол в комнате")

                room["gender"] = g["gender"]

                add(room, g, start, end)

                allocations.append({
                    "fio": g["fio"],
                    "room": room_id,
                    "checkin": start,
                    "checkout": end
                })

                placed = True
                break

        if not placed:
            rejections.append({
                "fio": g["fio"],
                "reasons": ["нет свободной комнаты на даты"]
            })

            allocations.append({
                "fio": g["fio"],
                "room": "NO ROOM",
                "checkin": start,
                "checkout": end
            })

    return pd.DataFrame(allocations), pd.DataFrame(rejections), rooms


# -------------------------
# ROOM STATS
# -------------------------
def build_room_stats(room_state):

    result = []

    for room_id, room in room_state.items():

        people = set()

        for day, guests in room["calendar"].items():
            for g in guests:
                people.add(g["fio"])

        result.append({
            "room_id": room_id,
            "people_count": len(people),
            "capacity": room["capacity"]
        })

    return pd.DataFrame(result)
