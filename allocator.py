import pandas as pd


def allocate_rooms(guests_df, rooms_df):

    allocations = []

    occupancy = {}

    for _, room in rooms_df.iterrows():

        room_id = room["room_id"]

        occupancy[room_id] = {
            "capacity": room["вместимость"],
            "guests": [],
            "gender": None
        }

    guests_df = guests_df.sort_values(
        by="age",
        ascending=False,
        na_position="last"
    )

    for _, guest in guests_df.iterrows():

        guest_gender = guest["gender"]

        allocated = False

        for room_id, room_data in occupancy.items():

            current_guests = room_data["guests"]

            capacity = room_data["capacity"]

            room_gender = room_data["gender"]

            if len(current_guests) >= capacity:
                continue

            if room_gender is not None:
                if room_gender != guest_gender:
                    continue

            current_guests.append(
                guest["fio"]
            )

            room_data["gender"] = guest_gender

            allocations.append({
                "fio": guest["fio"],
                "gender": guest_gender,
                "room": room_id
            })

            allocated = True

            break

        if not allocated:

            allocations.append({
                "fio": guest["fio"],
                "gender": guest_gender,
                "room": "NO ROOM"
            })

    return pd.DataFrame(allocations)
