from ortools.sat.python import cp_model
import pandas as pd
from config import WEIGHTS


# =========================================================
# COST
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
# SOLVER
# =========================================================
def solve(guests_df, rooms_df):

    model = cp_model.CpModel()

    # ❗ теперь уже ДАННЫЕ приходят как list[dict]
    guests = guests_df
    rooms = rooms_df

    G = range(len(guests))
    R = range(len(rooms))

    x = {}

    for g in G:
        for r in R:
            x[g, r] = model.NewBoolVar(f"x_{g}_{r}")

    # one room per guest
    for g in G:
        model.Add(sum(x[g, r] for r in R) == 1)

    # capacity
    for r in R:
        model.Add(
            sum(x[g, r] for g in G)
            <= int(rooms[r]["вместимость"])
        )

    objective = []

    # conflicts
    for g1 in G:
        for g2 in range(g1 + 1, len(guests)):

            cost = conflict_cost(guests[g1], guests[g2])

            if cost == 0:
                continue

            for r in R:

                pair = model.NewBoolVar(f"p_{g1}_{g2}_{r}")

                model.Add(pair <= x[g1, r])
                model.Add(pair <= x[g2, r])
                model.Add(pair >= x[g1, r] + x[g2, r] - 1)

                objective.append(cost * pair)

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

    return pd.DataFrame(result)
   
