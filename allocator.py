import pandas as pd
from collections import defaultdict


def allocate_rooms(guests_df, rooms_df):

    allocations = []
    reasons = []

    # -------------------------
    # rooms
    # -------------------------
    rooms = {}
    for _, r in rooms_df.iterrows():
        rooms[r["room_id"]] = {
            "capacity": int(r["вместимость"]),
            "calendar": defaultdict(list),  # day -> guests
        }

    # -------------------------
    # sort by priority
    # -------------------------
    guests_df = sorted(
        guests_df,
        key=lambda g: (
            g.get("status") != "professor",
            -(g.get("age") or 0)
        )
    )

    # -------------------------
    # helper: check availability
    # -------------------------
    def is_free(room, start, end):
        for d in range(start, end + 1):
            if len(room["calendar"][d]) >= room["capacity"]:
                return False
        return True

    def add_guest(room, guest, start, end):
        for d in range(start, end + 1):
            room["calendar"][d].append(guest)

    # -------------------------
    # main loop
    # -------------------------
    for g in guests_df:

        start = int(g.get("checkin"))
        end = int(g.get("checkout"))

        placed = False

        for room_id, room in rooms.items():

            if is_free(room, start, end):

                add_guest(room, g, start, end)

                allocations.append({
                    "fio": g["fio"],
                    "room": room_id,
                    "checkin": start,
                    "checkout": end
                })

                placed = True
                break

        if not placed:

            allocations.append({
                "fio": g["fio"],
                "room": "NO ROOM",
                "checkin": start,
                "checkout": end
            })

            reasons.append({
                "fio": g["fio"],
                "reason": "нет свободной комнаты в даты проживания"
            })

    return pd.DataFrame(allocations), pd.DataFrame(reasons), rooms


# =========================
# ROOM STATS (ВАЖНО: ВНЕ ФУНКЦИИ allocate_rooms)
# =========================
def build_room_stats(room_state):

    result = []

    for room_id, room in room_state.items():

        total_people = set()

        for day, guests in room["calendar"].items():
            for g in guests:
                total_people.add(g["fio"])

        result.append({
            "room_id": room_id,
            "people_count": len(total_people)
        })

    return pd.DataFrame(result)
