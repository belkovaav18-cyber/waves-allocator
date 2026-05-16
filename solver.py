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
def solve(guests, rooms):

    model = cp_model.CpModel()

    G = range(len(guests))
    R = range(len(rooms))

    x = {}

    # =====================================================
    # VARIABLES
    # =====================================================
    for g in G:
        for r in R:
            x[g, r] = model.NewBoolVar(f"x_{g}_{r}")

    # =====================================================
    # ONE ROOM
    # =====================================================
    for g in G:
        model.Add(
            sum(x[g, r] for r in R) == 1
        )

    # =====================================================
    # CAPACITY
    # =====================================================
    for r in R:

        cap = int(rooms[r]["вместимость"])

        model.Add(
            sum(x[g, r] for g in G)
            <= cap
        )

    objective = []

    # =====================================================
    # HARD GROUPS
    # =====================================================
    for g in G:

        for other_fio in guests[g].get(
            "group_hard",
            []
        ):

            for h in G:

                if guests[h]["fio"] != other_fio:
                    continue

                for r in R:
                    model.Add(
                        x[g, r] == x[h, r]
                    )

    # =====================================================
    # CONFLICTS
    # =====================================================
    for g1 in G:

        for g2 in range(g1 + 1, len(guests)):

            cost = conflict_cost(
                guests[g1],
                guests[g2]
            )

            if cost == 0:
                continue

            for r in R:

                p = model.NewBoolVar(
                    f"pair_{g1}_{g2}_{r}"
                )

                model.Add(
                    p <= x[g1, r]
                )

                model.Add(
                    p <= x[g2, r]
                )

                model.Add(
                    p >= x[g1, r]
                    + x[g2, r]
                    - 1
                )

                objective.append(
                    cost * p
                )

    # =====================================================
    # SOFT GROUPS
    # =====================================================
    for g in G:

        for other_fio in guests[g].get(
            "group_soft",
            []
        ):

            for h in G:

                if guests[h]["fio"] != other_fio:
                    continue

                for r in R:

                    t = model.NewBoolVar(
                        f"soft_{g}_{h}_{r}"
                    )

                    model.Add(
                        t <= x[g, r]
                    )

                    model.Add(
                        t <= x[h, r]
                    )

                    model.Add(
                        t >= x[g, r]
                        + x[h, r]
                        - 1
                    )

                    objective.append(-30 * t)

    # =====================================================
    # AVOID
    # =====================================================
    for g in G:

        for other_fio in guests[g].get(
            "group_avoid",
            []
        ):

            for h in G:

                if guests[h]["fio"] != other_fio:
                    continue

                for r in R:

                    t = model.NewBoolVar(
                        f"avoid_{g}_{h}_{r}"
                    )

                    model.Add(
                        t <= x[g, r]
                    )

                    model.Add(
                        t <= x[h, r]
                    )

                    model.Add(
                        t >= x[g, r]
                        + x[h, r]
                        - 1
                    )

                    objective.append(100 * t)

    # =====================================================
    # ROOM TYPE (SOFT)
    # =====================================================
    for g in G:

        req = guests[g].get("room_type")

        if req is None:
            continue

        for r in R:

            cap = int(
                rooms[r]["вместимость"]
            )

            if cap != req:

                penalty = model.NewBoolVar(
                    f"room_penalty_{g}_{r}"
                )

                model.Add(
                    penalty == x[g, r]
                )

                objective.append(
                    50 * penalty
                )

    # =====================================================
    # SOLVE
    # =====================================================
    model.Minimize(sum(objective))

    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = 20

    status = solver.Solve(model)

    # =====================================================
    # NO SOLUTION
    # =====================================================
    if status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE
    ):

        return pd.DataFrame([
            {"error": "no solution"}
        ])

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
                    "room_capacity": rooms[r]["вместимость"]
                })

    return pd.DataFrame(result)
