import pandas as pd
from collections import defaultdict
def allocate_rooms(guests_df, rooms_df):

    # =========================
    # FIX INPUT TYPES (CRITICAL)
    # =========================
    if isinstance(guests_df, pd.DataFrame):
        guests_df = guests_df.to_dict("records")

    if isinstance(rooms_df, pd.DataFrame):
        rooms_df = rooms_df.to_dict("records")

def age_distance(a, b):
    if a is None or b is None:
        return 10
    return abs(a - b)


def score_room(guest, room, room_state):

    score = 0

    # --------------------
    # HARD CONSTRAINTS
    # --------------------

    # capacity
    if len(room_state["guests"]) >= room["capacity"]:
        return -10**9

    # professor/student conflict
    if room_state["has_professor"] and guest["status"] == "student":
        return -10**6

    if guest["status"] == "professor" and len(room_state["guests"]) > 0:
        return -10**6

    # family must stay together
    family = guest.get("family_id")
    if family:
        families_in_room = room_state["families"]
        if families_in_room and family not in families_in_room:
            return -10**6

    # --------------------
    # SOFT CONSTRAINTS
    # --------------------

    # student preference
    if guest["status"] == "student":
        if room_state["has_professor"]:
            score -= 1000

    # age compatibility
    for g in room_state["guests"]:
        score -= age_distance(guest.get("age"), g.get("age"))

    # city penalty
    city = guest.get("city")
    if city:
        if room_state["cities"] and city not in room_state["cities"]:
            score -= 50
        else:
            score += 10

    # same gender soft bonus
    if room_state["gender"] and room_state["gender"] != guest["gender"]:
        score -= 20

    return score


def allocate_rooms(guests_df, rooms_df):

    allocations = []

    rooms = []

    for _, r in rooms_df.iterrows():
        rooms.append({
            "room_id": r["room_id"],
            "capacity": int(r["вместимость"])
        })

    # sort: seniors / professors first, then older
    guests_df = sorted(
    list(guests_df),
    key=lambda g: (
        g.get("status") != "professor",
        -(g.get("age") or 0)
    )
)

    room_state = {
        r["room_id"]: {
            "guests": [],
            "cities": set(),
            "families": set(),
            "has_professor": False,
            "gender": None
        }
        for r in rooms
    }

    for guest in guests_df:

        best_room = None
        best_score = float("-inf")

        for room in rooms:

            state = room_state[room["room_id"]]

            s = score_room(guest, room, state)

            if s > best_score:
                best_score = s
                best_room = room["room_id"]

        # assign
        if best_room is None or best_score < -10**8:
            allocations.append({
                "fio": guest["fio"],
                "room": "NO ROOM"
            })
            continue

        state = room_state[best_room]

        state["guests"].append(guest)
        state["cities"].add(guest.get("city"))
        if not state["gender"]:
            state["gender"] = guest["gender"]

        if guest.get("family_id"):
            state["families"].add(guest["family_id"])

        if guest.get("status") == "professor":
            state["has_professor"] = True

        allocations.append({
            "fio": guest["fio"],
            "room": best_room
        })

    return pd.DataFrame(allocations)
