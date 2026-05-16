import pandas as pd


def allocate_rooms(guests_df, rooms_df):

    allocations = []
    occupancy = {}

    # =========================
    # INIT
    # =========================
    for _, room in rooms_df.iterrows():

        occupancy[room["room_id"]] = {
            "capacity": room["вместимость"],
            "guests": [],
            "genders": set(),
            "ages": [],
            "cities": set()
        }

    # =========================
    # SORT (VERY IMPORTANT)
    # =========================
    guests_df = guests_df.sort_values(
        by=["age"],
        ascending=False
    )

    # =========================
    # MAIN LOOP
    # =========================
    for _, g in guests_df.iterrows():

        fio = g["fio"]
        gender = g["gender"]
        age = g["age"]
        city = g.get("city", "UNKNOWN")

        allocated = False

        for room_id, room in occupancy.items():

            # -------------------------
            # CAPACITY
            # -------------------------
            if len(room["guests"]) >= room["capacity"]:
                continue

            # -------------------------
            # GENDER RULE (soft)
            # -------------------------
            if len(room["genders"]) > 1:
                continue

            if room["genders"] and gender not in room["genders"]:
                continue

            # -------------------------
            # CITY RULE (disabled if UNKNOWN)
            # -------------------------
            if city != "UNKNOWN" and room["cities"]:
                if city not in room["cities"]:
                    continue

            # -------------------------
            # ASSIGN
            # -------------------------
            room["guests"].append(fio)
            room["genders"].add(gender)
            room["cities"].add(city)
            room["ages"].append(age)

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
