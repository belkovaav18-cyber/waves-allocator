import pandas as pd
def explain_rejection(guest, room_state, room, capacity):
    reasons = []

    if len(room_state["guests"]) >= capacity:
        reasons.append("нет свободных мест")

    if room_state["has_professor"] and guest.get("status") == "student":
        reasons.append("в комнате есть профессор (студентам нельзя)")

    if guest.get("status") == "professor" and len(room_state["guests"]) > 0:
        reasons.append("профессор должен жить один")

    city = guest.get("city")
    if city and room_state["cities"] and city not in room_state["cities"]:
        reasons.append("конфликт городов")

    if room_state["gender"] and room_state["gender"] != guest.get("gender"):
        reasons.append("конфликт пола")

    return reasons if reasons else ["не найдено подходящей комнаты"]
def allocate_rooms(guests_df, rooms_df):

    guests_df = list(guests_df)
    rooms_df = list(rooms_df)

    allocations = []

    rooms = [
        {
            "room_id": r["room_id"],
            "capacity": int(r["вместимость"])
        }
        for r in rooms_df
    ]

    guests_df = sorted(
        guests_df,
        key=lambda g: (
            g.get("status", "student") != "professor",
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

            if len(state["guests"]) >= room["capacity"]:
                continue

            score = 0

            # мягкая логика
            if state["has_professor"] and guest.get("status") == "student":
                score -= 1000

            if state["cities"] and guest.get("city") not in state["cities"]:
                score -= 50

            if state["gender"] and state["gender"] != guest.get("gender"):
                score -= 20

            if score > best_score:
                best_score = score
                best_room = room["room_id"]

        if best_room is None:
            allocations.append({
                "fio": guest.get("fio", ""),
                "room": "NO ROOM"
            })
            continue

        state = room_state[best_room]

        state["guests"].append(guest)
        state["cities"].add(guest.get("city"))
        state["gender"] = guest.get("gender")

        if guest.get("status") == "professor":
            state["has_professor"] = True

        allocations.append({
            "fio": guest.get("fio", ""),
            "room": best_room
        })

    return pd.DataFrame(allocations)
