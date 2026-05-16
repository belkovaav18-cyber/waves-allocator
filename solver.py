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

    residents = [g for g in guests if g.get("resident", True)]
    non_residents = [g for g in guests if not g.get("resident", True)]

    if len(residents) == 0:
        return pd.DataFrame([{
            "fio": g["fio"],
            "room_id": "не проживает"
        } for g in non_residents])

    model = cp_model.CpModel()

    G = range(len(residents))
    R = range(len(rooms))

    x = {(g, r): model.NewBoolVar(f"x_{g}_{r}") for g in G for r in R}

    # one room
    for g in G:
        model.Add(sum(x[g, r] for r in R) == 1)

    # capacity
    for r in R:
        cap = int(rooms[r]["вместимость"])
        model.Add(sum(x[g, r] for g in G) <= cap)

    objective = []

    # conflicts
    for g1 in G:
        for g2 in range(g1 + 1, len(residents)):

            cost = conflict_cost(residents[g1], residents[g2])
            if cost == 0:
                continue

            for r in R:
                t = model.NewBoolVar(f"c_{g1}_{g2}_{r}")

                model.Add(t <= x[g1, r])
                model.Add(t <= x[g2, r])
                model.Add(t >= x[g1, r] + x[g2, r] - 1)

                objective.append(cost * t)

    # soft
    for g in G:
        for other in residents[g].get("group_soft", []):

            for r in R:
                t = model.NewBoolVar(f"s_{g}_{other}_{r}")

                model.Add(t <= x[g, r])
                model.Add(t <= x[other, r])
                model.Add(t >= x[g, r] + x[other, r] - 1)

                objective.append(-30 * t)

    # avoid
    for g in G:
        for other in residents[g].get("group_avoid", []):

            for r in R:
                t = model.NewBoolVar(f"a_{g}_{other}_{r}")

                model.Add(t <= x[g, r])
                model.Add(t <= x[other, r])
                model.Add(t >= x[g, r] + x[other, r] - 1)

                objective.append(100 * t)

    # room type constraint
    for g in G:
        req = residents[g].get("room_type")
        if req is not None:
            for r in R:
                if int(rooms[r]["вместимость"]) != req:
                    model.Add(x[g, r] == 0)

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
                    "fio": residents[g]["fio"],
                    "room_id": rooms[r]["room_id"]
                })

    for g in non_residents:
        result.append({
            "fio": g["fio"],
            "room_id": "не проживает"
        })

    return pd.DataFrame(result)
