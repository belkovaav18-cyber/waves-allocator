import pandas as pd


def allocate_rooms(guests_df, rooms_df):

    allocations = []

    occupancy = {}

    # =========================
    # INIT ROOMS
    # =========================
    for _, room in rooms_df.iterrows():

        occupancy[room["room_id"]] = {
            "capacity": room["вместимость"],
            "guests": [],
            "gender": None,
            "cities": set(),
            "families": set(),
            "has_professor": False
        }

    # =========================
    # SORT PRIORITY
    # professors first → older → families grouped
    # =========================
    guests_df = guests_df.sort_values(
        by=["status", "age"],
        ascending=[False, False],
        na_position="last"
    )

    # =========================
    # MAIN LOOP
    # =========================
    for _, guest in guests_df.iterrows():

        fio = guest["fio"]
        gender = guest.get("gender")
        age = guest.get("age", 0)
        city = guest.get("city", "UNKNOWN")
        status = guest.get("status", "student")
        family = guest.get("family_id")

        allocated = False

        for room_id, room in occupancy.items():

            current = room["guests"]

            # -------------------------
            # 1. CAPACITY
            # -------------------------
            if len(current) >= room["capacity"]:
                continue

            # -------------------------
            # 2. PROFESSOR RULE
            # -------------------------
            if status == "professor":

                # only empty or same professor room
                if len(current) > 0 and not room["has_professor"]:
                    continue

            else:
                # students cannot go into professor-only room
                if room["has_professor"]:
                    continue

            # -------------------------
            # 3. FAMILY RULE (STRICT)
            # -------------------------
            if family:

                # if room already has different family → skip
                if room["families"] and family not in room["families"]:
                    continue

            # -------------------------
            # 4. CITY RULE (SOFT)
            # -------------------------
            if city != "UNKNOWN":

                # allow mixing ONLY if empty or same city
                if room["cities"] and city not in room["cities"]:
                    continue

            # -------------------------
            # ASSIGN
            # -------------------------
            current.append({
                "fio": fio,
                "gender": gender,
                "age": age,
                "city": city,
                "status": status,
                "family_id": family
            })

            room["cities"].add(city)

            if family:
                room["families"].add(family)

            if status == "professor":
                room["has_professor"] = True

            room["gender"] = gender

            allocations.append({
                "fio": fio,
                "gender": gender,
                "age": age,
                "city": city,
                "room": room_id
            })

            allocated = True
            break

        if not allocated:

            allocations.append({
                "fio": fio,
                "gender": gender,
                "age": age,
                "city": city,
                "room": "NO ROOM"
            })

    return pd.DataFrame(allocations)
