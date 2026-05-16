import pandas as pd


# =========================
# EXPLANATION ENGINE
# =========================
def explain_rejection(guest, room_state, room_capacity):

    reasons = []

    if len(room_state["guests"]) >= room_capacity:
        reasons.append("нет свободных мест")

    if room_state["has_professor"] and guest.get("status") == "student":
        reasons.append("в комнате уже есть профессор")

    if guest.get("status") == "professor" and len(room_state["guests"]) > 0:
        reasons.append("профессор должен жить один")

    city = guest.get("city")
    if city and room_state["cities"] and city not in room_state["cities"]:
        reasons.append("конфликт городов")

    if room_state["gender"] and room_state["gender"] != guest.get("gender"):
        reasons.append("конфликт пола")

    return reasons if reasons else ["нет подходящих условий"]


# =========================
# MAIN ALLOCATOR
# =========================
def allocate_rooms(guests_df, rooms_df):

    # 🔥 FIX TYPES (Streamlit safe)
    guests_df = list(guests_df)
    rooms_df = list(rooms_df)

    allocations = []
    rejections = []

    # rooms init
    rooms = [
        {
            "room_id": r["room_id"],
            "capacity": int(r["вместимость"])
        }
        for r in rooms_df
    ]

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

    # sorting priority
    guests_df = sorted(
        guests_df,
        key=lambda g: (
            g.get("status", "student") != "professor",
            -(g.get("age") or 0)
        )
    )

    # =========================
    # MAIN LOOP
    # =========================
    for guest in guests_df:

        best_room = None
        best_score = float("-inf")

        for room in rooms:

            state = room_state[room["room_id"]]

            # HARD CHECKS (fast skip)
            if len(state["guests"]) >= room["capacity"]:
                continue

            score = 0

            # soft logic
            if state["has_professor"] and guest.get("status") == "student":
                score -= 1000

            if state["cities"] and guest.get("city") not in state["cities"]:
                score -= 50

            if state["gender"] and state["gender"] != guest.get("gender"):
                score -= 20

            if score > best_score:
                best_score = score
                best_room = room["room_id"]

        # =========================
        # ASSIGN OR REJECT
        # =========================
        if best_room is None:
            # explanation fallback
            fallback_room = rooms[0] if rooms else None

            reasons = ["нет доступной комнаты"]

            if fallback_room:
                reasons = explain_rejection(
                    guest,
                    room_state[fallback_room["room_id"]],
                    fallback_room["capacity"]
                )

            rejections.append({
                "fio": guest.get("fio", ""),
                "age": guest.get("age"),
                "city": guest.get("city"),
                "status": guest.get("status"),
                "reasons": reasons
            })

            allocations.append({
                "fio": guest.get("fio", ""),
                "room": "NO ROOM"
            })

            continue

        # update state
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

    return pd.DataFrame(allocations), pd.DataFrame(rejections)
