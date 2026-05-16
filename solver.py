from ortools.sat.python import cp_model
import pandas as pd
from config import WEIGHTS


def conflict_cost(a, b):
    cost = 0

    if a["gender"] != b["gender"]:
        cost += WEIGHTS["gender_conflict"]

    if a.get("city") != b.get("city"):
        cost += WEIGHTS["city_diff"]

    if a.get("status") != b.get("status"):
        cost += WEIGHTS["status_diff"]

    return cost


def solve(guests, rooms):

    # =====================================================
    # 1. SPLIT RESIDENTS / NON-RESIDENTS
    # =====================================================
    residents = [g for g in guests if g.get("will_stay", True)]
    non_residents = [g for g in guests if not g.get("will_stay", True)]

    # =====================================================
    # EDGE CASE: нет проживающих
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

    x = {}

    for g in G:
        for r in R:
            x[g, r] = model.NewBoolVar(f"x_{g}_{r}")

    # =====================================================
    # one room per resident
    # =====================================================
    for g in G:
        model.Add(sum(x[g, r] for r in R) == 1)

    # =====================================================
    # capacity
    # =====================================================
    for r in R:
        cap = int(rooms[r]["вместимость"])
        model.Add(sum(x[g, r] for g in G) <= cap)

    # =====================================================
    # objective (conflicts)
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

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10

    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return pd.DataFrame([{"error": "no solution"}])

    # =====================================================
    # RESULT for residents
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
