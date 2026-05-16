from ortools.sat.python import cp_model
from ortools.sat.python.cp_model import OPTIMAL, FEASIBLE

import pandas as pd
from config import WEIGHTS


# =========================================================
# COST
# =========================================================
def conflict_cost(g1, g2):

    cost = 0

    if g1["gender"] != g2["gender"]:
        cost += WEIGHTS["gender_conflict"]

    if g1.get("city") != g2.get("city"):
        cost += WEIGHTS["city_diff"]

    if g1.get("status") != g2.get("status"):
        cost += WEIGHTS["status_diff"]

    return cost


# =========================================================
# SOLVER
# =========================================================
def solve(guests_df, rooms_df):

    model = cp_model.CpModel()

    guests = guests_df.to_dict("records")
    rooms = rooms_df.to_dict("records")

    G = range(len(guests))
    R = range(len(rooms))

    # =====================================================
    # VARIABLES
    # =====================================================
    x = {}

    for g in G:
        for r in R:
            x[g, r] = model.NewBoolVar(f"x_{g}_{r}")

    # =====================================================
    # each guest -> 1 room
    # =====================================================
    for g in G:
        model.Add(sum(x[g, r] for r in R) == 1)

    # =====================================================
    # CAPACITY
    # =====================================================
    for r in R:

        capacity = int(rooms[r]["вместимость"])

        model.Add(
            sum(x[g, r] for g in G) <= capacity
        )

    # =====================================================
    # HARD GROUPS
    # =====================================================
    for g in G:

        for group in guests[g].get("group_hard", []):

            for other in G:

                if other == g:
                    continue

                if any(name in guests[other]["fio"].lower()
                       for name in group):

                    for r in R:
                        model.Add(x[g, r] == x[other, r])

    # =====================================================
    # OBJECTIVE
    # =====================================================
    objective_terms = []

    for g1 in G:
        for g2 in range(g1 + 1, len(guests)):

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

                model.Add(pair <= x[g1, r])
                model.Add(pair <= x[g2, r])
                model.Add(pair >= x[g1, r] + x[g2, r] - 1)

                objective_terms.append(
                    base_cost * pair
                )

    # =====================================================
    # SOFT GROUP BONUS
    # =====================================================
    for g in G:

        for other in G:

            if g >= other:
                continue

            if "soft_link" in guests[g].get("group_soft", []):

                for r in R:

                    together = model.NewBoolVar(
                        f"soft_{g}_{other}_{r}"
                    )

                    model.Add(together <= x[g, r])
                    model.Add(together <= x[other, r])
                    model.Add(
                        together >= x[g, r] + x[other, r] - 1
                    )

                    # reward (negative cost)
                    objective_terms.append(-50 * together)

    model.Minimize(sum(objective_terms))

    # =====================================================
    # SOLVE
    # =====================================================
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 20

    status = solver.Solve(model)

    if status not in [OPTIMAL, FEASIBLE]:
        return pd.DataFrame([{
            "error": f"No solution. Status={status}"
        }])

    # =====================================================
    # RESULT
    # =====================================================
    result = []

    for g in G:
        for r in R:

            if solver.Value(x[g, r]):

                result.append({
                    "fio": guests[g]["fio"],
                    "room_id": rooms[r]["room_id"],
                    "building": rooms[r]["корпус"],
                    "room_number": rooms[r]["номер комнаты"],
                    "floor": rooms[r]["этаж"]
                })

    return pd.DataFrame(result)
   
