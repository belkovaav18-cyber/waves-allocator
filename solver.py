from ortools.sat.python import cp_model
import pandas as pd
from config import WEIGHTS


# =========================================================
# COST FUNCTION
# =========================================================
def conflict_cost(a, b):
    cost = 0

    if a["gender"] != b["gender"]:
        cost += WEIGHTS["gender_conflict"]

    if a.get("city") != b.get("city"):
        cost += WEIGHTS["city_diff"]

    if a.get("status") != b.get("status"):
        cost += WEIGHTS["status_diff"]

    return cost


# =========================================================
# SAFE GET ROOM CAP
# =========================================================
def get_capacity(room):
    try:
        return int(room.get("вместимость", 0))
    except:
        return 0


# =========================================================
# SOLVER
# =========================================================
def solve(guests, rooms):

    # =====================================================
    # SPLIT
    # =====================================================
    residents = [g for g in guests if g.get("resident", True)]
    non_residents = [g for g in guests if not g.get("resident", True)]

    # =====================================================
    # EDGE CASE
    # =====================================================
    if len(residents) == 0:
        return pd.DataFrame([{
            "fio": g["fio"],
            "room_id": "—",
            "status": "не проживает"
        } for g in non_residents])

    model = cp_model.CpModel()

    G = range(len(residents))
    R = range(len(rooms))

    # =====================================================
    # VARIABLES
    # =====================================================
    x = {}

    for g in G:
        for r in R:
            x[g, r] = model.NewBoolVar(f"x_{g}_{r}")

    # =====================================================
    # each guest -> one room
    # =====================================================
    for g in G:
        model.Add(sum(x[g, r] for r in R) == 1)

    # =====================================================
    # capacity constraint
    # =====================================================
    for r in R:
        cap = get_capacity(rooms[r])

        model.Add(
            sum(x[g, r] for g in G) <= cap
        )

    # =====================================================
    # ROOM TYPE CONSTRAINT (NEW)
    # =====================================================
    for g in G:

        req = residents[g].get("room_type")

        if req is None or (isinstance(req, float) and pd.isna(req)):
            continue

        try:
            req = int(req)
        except:
            continue

        for r in R:
            cap = get_capacity(rooms[r])

            if cap != req:
                model.Add(x[g, r] == 0)

    # =====================================================
    # OBJECTIVE (conflicts)
    # =====================================================
    objective = []

    for g1 in G:
        for g2 in range(g1 + 1, len(residents)):

            cost = conflict_cost(residents[g1], residents[g2])

            if cost == 0:
                continue

            for r in R:

                p = model.NewBoolVar(f"p_{g1}_{g2}_{r}")

                model.Add(p <= x[g1, r])
                model.Add(p <= x[g2, r])
                model.Add(p >= x[g1, r] + x[g2, r] - 1)

                objective.append(cost * p)

    model.Minimize(sum(objective))

    # =====================================================
    # SOLVE
    # =====================================================
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10

    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return pd.DataFrame([{"error": "no solution"}])

    # =====================================================
    # RESULT (residents)
    # =====================================================
    result = []

    for g in G:
        for r in R:
            if solver.Value(x[g, r]):
                result.append({
                    "fio": residents[g]["fio"],
                    "room_id": rooms[r]["room_id"]
                })

    # =====================================================
    # ADD NON-RESIDENTS
    # =====================================================
    for g in non_residents:
        result.append({
            "fio": g["fio"],
            "room_id": "—",
            "status": "не проживает"
        })

    return pd.DataFrame(result)
