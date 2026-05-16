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
            "has_senior": False
        }

    # =========================
    # SORT PRIORITY
    # 1. seniors first
    # 2. families
    # 3. older first
    # =========================
    def priority(g):

        is_senior = 1 if g.get("status") == "professor" else 0
        family = g.get("family_id", "")
        age = g.get("age", 0)

        return (-is_senior, family, -age)

    guests_df = guests_df.sort_values(
        by="age",
        ascending=False,
        na_position="last"
    )

    # =========================
    # MAIN LOOP
    # =========================
    for _, guest in guests_df.iterrows():

        fio = guest["fio"]
        gender = guest["gender"]
        age = guest.get("age")
        city = guest.get("city", None)
        status = guest.get("status", "student")
        family = guest.get("family_id")

        allocated = False

        for room_id, room in occupancy.items():

            current = room["guests"]
            capacity = room["capacity"]

            # -------------------------
            # 1. capacity check
            # -------------------------
            if len(current) >= capacity:
                continue

            # -------------------------
            # 2. SENIOR RULE
            # -------------------------
            if status == "professor" and len(current) > 0:
                continue

            # -------------------------
            # 3. FAMILY RULE (must stay together)
            # -------------------------
            if family:
                family_in_room = any(
                    g.get("family_id") == family
                    for g in current
                )
                if family_in_room or len(current) > 0:
                    # только в ту комнату где уже семья
                    pass
                else:
                    # если комната не пустая — нельзя
                    if len(current) > 0:
                        continue

            # -------------------------
            # 4. CITY RULE
            # -------------------------
            if city:

                # если уже есть другой город → можно, но осторожно
                if len(room["cities"]) > 0 and city not in room["cities"]:
                    continue

                # конфликт: если в комнате есть senior → нельзя студенту из того же города
                if room["has_senior"] and status == "student":
                    continue

            # -------------------------
            # 5. ASSIGN
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

            if status == "professor":
                room["has_senior"] = True

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
