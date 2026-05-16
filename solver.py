from ortools.sat.python import cp_model
import pandas as pd
from config import WEIGHTS


# =========================================================
# NORMALIZATION
# =========================================================
def normalize_records(data):

    if data is None:
        return []

    if isinstance(data, pd.DataFrame):
        return data.to_dict("records")

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        return [data]

    if hasattr(data, "to_dict"):
        try:
            return data.to_dict("records")
        except:
            return [data.to_dict()]

    raise TypeError(f"Unsupported data type: {type(data)}")


def clean_rooms(rooms_df):

    rooms_df = normalize_records(rooms_df)

    cleaned = []

    for r in rooms_df:
        cleaned.append({
            "room_id": r.get("room_id"),
            "capacity": int(r.get("вместимость", 0)),
            "building": r.get("корпус"),
            "number": r.get("номер комнаты"),
            "floor": r.get("этаж")
        })

    return cleaned


# =========================================================
# COST FUNCTION
# =========================================================
def conflict_cost(a, b):

    cost = 0

    if a.get("gender") != b.get("gender"):
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

    # -------------------------
    # NORMALIZE INPUTS (ВАЖНО)
    # -------------------------
    guests = normalize_records(guests_df)
    rooms = clean_rooms(rooms_df)

    G = range(len(guests))
    R = range(len(rooms))

    # -------------------------
    # VARIABLES
    # -------------------------
    x = {}

    for g in G:
        for r in R:
            x[g, r] = model.NewBoolVar(f"x_{g}_{r}")

    # -------------------------
    # 1. each guest → 1 room
    # -------------------------
    for g in G:
        model.Add(sum(x[g, r] for r in R) == 1)

    # -------------------------
    # 2. capacity constraint
    # -------------------------
    for r in R:
        model.Add(
            sum(x[g, r] for g in G)
            <= rooms[r]["capacity"]
        )

    # -------------------------
    # OBJECTIVE
    # -------------------------
    objective = []

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

    # -------------------------
    # SOLVE
    # -------------------------
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10

    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return pd.DataFrame([{"error": "no solution"}])

    # -------------------------
    # RESULT
    # -------------------------
    result = []

    for g in G:
        for r in R:

            if solver.Value(x[g, r]):

                result.append({
                    "fio": guests[g]["fio"],
                    "room_id": rooms[r]["room_id"],
                    "building": rooms[r].get("building"),
                    "room_number": rooms[r].get("number"),
                    "floor": rooms[r].get("floor")
                })

    return pd.DataFrame(result)
