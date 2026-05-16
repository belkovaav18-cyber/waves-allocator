from ortools.sat.python import cp_model
from ortools.sat.python.cp_model import OPTIMAL, FEASIBLE

import pandas as pd

from config import WEIGHTS


# =========================================================
# CONFLICT COST
# =========================================================
def conflict_cost(g1, g2):

    cost = 0

    # -------------------------------------------------
    # gender conflict
    # -------------------------------------------------
    if g1["gender"] != g2["gender"]:
        cost += WEIGHTS["gender_conflict"]

    # -------------------------------------------------
    # city conflict
    # -------------------------------------------------
    if g1.get("city") != g2.get("city"):
        cost += WEIGHTS["city_diff"]

    # -------------------------------------------------
    # status conflict
    # -------------------------------------------------
    if g1.get("status") != g2.get("status"):
        cost += WEIGHTS["status_diff"]

    return cost


# =========================================================
# NIGHT OVERLAP
# =========================================================
def overlap(n1, n2):
    return bool(set(n1) & set(n2))


# =========================================================
# MAIN SOLVER
# =========================================================
def solve(guests_df, rooms_df):

    model = cp_model.CpModel()

    guests = guests_df.to_dict("records")
    rooms = rooms_df.to_dict("records")

    G = range(len(guests))
    R = range(len(rooms))

    # =====================================================
    # VARIABLES
    # x[g,r] = guest g assigned to room r
    # =====================================================
    x = {}

    for g in G:
        for r in R:
            x[g, r] = model.NewBoolVar(f"x_{g}_{r}")

    # =====================================================
    # EVERY GUEST EXACTLY ONE ROOM
    # =====================================================
    for g in G:
        model.Add(
            sum(x[g, r] for r in R) == 1
        )

    # =====================================================
    # ALL NIGHTS
    # =====================================================
    all_nights = set()

    for guest in guests:
        all_nights.update(guest["nights"])

    # =====================================================
    # ROOM CAPACITY BY NIGHT
    # =====================================================
    for r in R:

        room = rooms[r]

        room_status = str(
            room.get("статус", "")
        ).lower()

        # ---------------------------------------------
        # skip blocked rooms
        # ---------------------------------------------
        if room_status in ["blocked", "closed"]:
            continue

        capacity = int(room["вместимость"])

        for night in all_nights:

            guests_this_night = []

            for g in G:

                if night in guests[g]["nights"]:
                    guests_this_night.append(x[g, r])

            model.Add(
                sum(guests_this_night) <= capacity
            )

    # =====================================================
    # HARD GROUP CONSTRAINTS
    # =====================================================
    fio_to_idx = {
        guests[g]["fio"]: g
        for g in G
    }

    for g in G:

        group = guests[g].get("group", [])

        if not group:
            continue

        for member in group:

            member = member.lower()

            for other_fio, other_idx in fio_to_idx.items():

                if member in other_fio.lower():

                    # must be same room
                    for r in R:
                        model.Add(
                            x[g, r] == x[other_idx, r]
                        )

    # =====================================================
    # OBJECTIVE
    # =====================================================
    objective_terms = []

    for g1 in G:

        for g2 in range(g1 + 1, len(guests)):

            # ---------------------------------------------
            # no overlap -> no conflict possible
            # ---------------------------------------------
            if not overlap(
                guests[g1]["nights"],
                guests[g2]["nights"]
            ):
                continue

            base_cost = conflict_cost(
                guests[g1],
                guests[g2]
            )

            if base_cost == 0:
                continue

            for r in R:

                pair = model.NewBoolVar(
                    f"pair_{g1}_{g2}_{r}"
                )

                # pair == 1 iff both in same room
                model.Add(
                    pair <= x[g1, r]
                )

                model.Add(
                    pair <= x[g2, r]
                )

                model.Add(
                    pair >= x[g1, r] + x[g2, r] - 1
                )

                objective_terms.append(
                    base_cost * pair
                )

    # =====================================================
    # MINIMIZE CONFLICTS
    # =====================================================
    model.Minimize(
        sum(objective_terms)
    )

    # =====================================================
    # SOLVER
    # =====================================================
    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = 20

    status = solver.Solve(model)

    # =====================================================
    # NO SOLUTION
    # =====================================================
    if status not in [OPTIMAL, FEASIBLE]:

        return pd.DataFrame([
            {
                "error": f"No solution found. Status={status}"
            }
        ])

    # =====================================================
    # RESULT
    # =====================================================
    result = []

    for g in G:

        for r in R:

            if solver.Value(x[g, r]):

                room = rooms[r]

                result.append({

                    "fio": guests[g]["fio"],

                    "room_id": room["room_id"],

                    "building": room["корпус"],

                    "room_number": room["номер комнаты"],

                    "floor": room["этаж"],

                    "capacity": room["вместимость"],

                    "nights": ", ".join(
                        map(str, guests[g]["nights"])
                    ),

                    "gender": guests[g]["gender"],

                    "status": guests[g]["status"],

                    "group": ", ".join(
                        guests[g].get("group", [])
                    )
                })

    result_df = pd.DataFrame(result)

    # =====================================================
    # SORT
    # =====================================================
    if not result_df.empty:

        result_df = result_df.sort_values(
            by=[
                "building",
                "floor",
                "room_number"
            ]
        )

    return result_df

   
