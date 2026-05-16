from ortools.sat.python import cp_model
import pandas as pd
from config import WEIGHTS


def conflict_cost(g1, g2):

    cost = 0

    if g1["gender"] != g2["gender"]:
        cost += WEIGHTS["gender_conflict"]

    if g1.get("city") != g2.get("city"):
        cost += WEIGHTS["city_diff"]

    if g1.get("status") != g2.get("status"):
        cost += WEIGHTS["status_diff"]

    return cost


def solve(guests_df, rooms_df):

    model = cp_model.CpModel()

    guests = guests_df.to_dict("records")
    rooms = rooms_df.to_dict("records")

    x = {}

    # x[g,r] = 1 если гость g в комнате r
    for g in range(len(guests)):
        for r in range(len(rooms)):
            x[g, r] = model.NewBoolVar(f"x_{g}_{r}")

    # 1. каждый гость в одной комнате
    for g in range(len(guests)):
        model.Add(sum(x[g, r] for r in range(len(rooms))) == 1)

    # 2. вместимость
    for r in range(len(rooms)):
        model.Add(
            sum(x[g, r] for g in range(len(guests))) <= int(rooms[r]["вместимость"])
        )

    # 3. objective (минимизация конфликтов)
    objective_terms = []

    for g1 in range(len(guests)):
        for g2 in range(g1 + 1, len(guests)):

            base_cost = conflict_cost(guests[g1], guests[g2])

            if base_cost == 0:
                continue

            for r in range(len(rooms)):

                # если оба в одной комнате
                var = model.NewBoolVar(f"pair_{g1}_{g2}_{r}")

                model.AddBoolAnd([x[g1, r], x[g2, r]]).OnlyEnforceIf(var)
                model.AddBoolOr([x[g1, r].Not(), x[g2, r].Not()]).OnlyEnforceIf(var.Not())

                objective_terms.append(base_cost * var)

    model.Minimize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10

    status = solver.Solve(model)

    result = []

    for g in range(len(guests)):
        for r in range(len(rooms)):
            if solver.Value(x[g, r]):
                result.append({
                    "fio": guests[g]["fio"],
                    "room": rooms[r]["room_id"]
                })

    return pd.DataFrame(result)
