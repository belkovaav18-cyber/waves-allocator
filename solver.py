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

    model = cp_model.CpModel()

    G = range(len(guests))
    R = range(len(rooms))

    x = {}

    # decision vars
    for g in G:
        for r in R:
            x[g, r] = model.NewBoolVar(f"x_{g}_{r}")

    # one room per guest
    for g in G:
        model.Add(sum(x[g, r] for r in R) == 1)

    # capacity
    for r in R:
        cap = int(rooms[r]["вместимость"])
        model.Add(sum(x[g, r] for g in G) <= cap)

    objective = []

    # =====================================================
    # ROOM TYPE CONSTRAINT
    # =====================================================
    for g in G:
        req = guests[g].get("room_type")

        if req:
            for r in R:
                cap = int(rooms[r]["вместимость"])
                if cap != req:
                    model.Add(x[g, r] == 0)

    # =====================================================
    # HARD CONFLICTS
    # =====================================================
    for g1 in G:
        for g2 in range(g1 + 1, len(guests)):

            cost = conflict_cost(guests[g1], guests[g2])
            if cost == 0:
                continue

            for r in R:
                p = model.NewBoolVar(f"p_{g1}_{g2}_{r}")

                model.Add(p <= x[g1, r])
                model.Add(p <= x[g2, r])
                model.Add(p >= x[g1, r] + x[g2, r] - 1)

                objective.append(cost * p)

    # =====================================================
    # SOFT BONUS
    # =====================================================
    for g in G:
        for other in guests[g].get("group_soft", []):

            if other not in [x["fio"] for x in guests]:
                continue

            j = next(i for i in G if guests[i]["fio"] == other)

            if g >= j:
                continue

            for r in R:
                t = model.NewBoolVar(f"soft_{g}_{j}_{r}")

                model.Add(t <= x[g, r])
                model.Add(t <= x[j, r])
                model.Add(t >= x[g, r] + x[j, r] - 1)

                objective.append(-30 * t)

    # =====================================================
    # AVOID PENALTY
    # =====================================================
    for g in G:
        for other in guests[g].get("group_avoid", []):

            if other not in [x["fio"] for x in guests]:
                continue

            j = next(i for i in G if guests[i]["fio"] == other)

            for r in R:
                t = model.NewBoolVar(f"avoid_{g}_{j}_{r}")

                model.Add(t <= x[g, r])
                model.Add(t <= x[j, r])
                model.Add(t >= x[g, r] + x[j, r] - 1)

                objective.append(100 * t)

    model.Minimize(sum(objective))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10

    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return pd.DataFrame([{"error": "no solution"}])

    result = []

    for g in G:
        for r in R:
            if solver.Value(x[g, r]):
                result.append({
                    "fio": guests[g]["fio"],
                    "room_id": rooms[r]["room_id"]
                })

    # non-residents
    for g in guests:
        if not g.get("resident", True):
            result.append({
                "fio": g["fio"],
                "room_id": "не проживает"
            })

    return pd.DataFrame(result)
