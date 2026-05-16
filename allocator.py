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
