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
# HELPER: GET FLOOR FROM ROOM ID
# =========================================================
def get_floor_from_room_id(room_id):
    """
    Извлекает номер этажа из ID комнаты.
    Примеры:
    - "1-101" -> 1 (первая цифра после дефиса)
    - "101" -> 1 (первая цифра номера)
    - "2-215" -> 2
    """
    room_str = str(room_id)
    
    if '-' in room_str:
        after_hyphen = room_str.split('-')[1]
        if after_hyphen and after_hyphen[0].isdigit():
            return int(after_hyphen[0])
    
    digits = ''.join(filter(str.isdigit, room_str))
    if digits and digits[0].isdigit():
        return int(digits[0])
    
    return None


# =========================================================
# HELPER: GET BUILDING FROM ROOM ID
# =========================================================
def get_building_from_room_id(room_id):
    """
    Извлекает номер корпуса из ID комнаты.
    Примеры:
    - "1-101" -> 1 (красный корпус)
    - "2-215" -> 2 (желтый корпус)
    - "101" -> None (неопределен)
    """
    room_str = str(room_id)
    
    if '-' in room_str:
        building = room_str.split('-')[0]
        if building.isdigit():
            return int(building)
    
    return None


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
    # COUPLE / DOUBLE BED LOGIC
    # =====================================================
    for g in G:
    
        hard_group = guests[g].get("group_hard", [])
        req = guests[g].get("room_type")
    
        if len(hard_group) != 1:
            continue
    
        if req != 2:
            continue
    
        partner_fio = hard_group[0]
    
        for h in G:
    
            if guests[h]["fio"] != partner_fio:
                continue
    
            for r in R:
    
                cap = int(rooms[r]["вместимость"])
    
                if cap != 2:
                    continue
    
                both = model.NewBoolVar(
                    f"couple_{g}_{h}_{r}"
                )
    
                model.Add(both <= x[g, r])
                model.Add(both <= x[h, r])
    
                model.Add(
                    both >= x[g, r] + x[h, r] - 1
                )
    
                model.Add(
                    sum(x[k, r] for k in G)
                    <= 2
                ).OnlyEnforceIf(both)

    # =====================================================
    # HARD: NO SUBLEASE (одноместный тариф)
    # =====================================================
    for g in G:
        if guests[g].get("require_no_subleaser", False):
            for r in R:
                cap = int(rooms[r]["вместимость"])
                # Если комната на 2 места, то нельзя подселять других
                if cap == 2:
                    model.Add(
                        sum(x[k, r] for k in G) <= 1
                    ).OnlyEnforceIf(x[g, r])

    # =====================================================
    # HARD: MUST BE SINGLE ROOM (спецсписок)
    # =====================================================
    for g in G:
        if guests[g].get("must_be_single_room", False):
            for r in R:
                cap = int(rooms[r]["вместимость"])
                if cap != 1:
                    model.Add(x[g, r] == 0)

    # =====================================================
    # SOFT: PREFERRED BUILDING (ЖЕЛАТЕЛЬНЫЙ КОРПУС)
    # =====================================================
    for g in G:
        preferred_building = guests[g].get("preferred_building")
        if preferred_building:
            building_num = 1 if preferred_building == "red" else 2
            for r in R:
                room_building = get_building_from_room_id(rooms[r]["room_id"])
                if room_building != building_num:
                    penalty = model.NewBoolVar(f"building_penalty_{g}_{r}")
                    model.Add(penalty == x[g, r])
                    objective.append(40 * penalty)  # штраф за нежелательный корпус

    # =====================================================
    # SOFT: PREFERRED FLOOR (ЖЕЛАТЕЛЬНЫЙ ЭТАЖ)
    # =====================================================
    for g in G:
        preferred_floor = guests[g].get("preferred_floor")
        if preferred_floor is not None:
            for r in R:
                room_floor = get_floor_from_room_id(rooms[r]["room_id"])
                if room_floor != preferred_floor:
                    penalty = model.NewBoolVar(f"floor_penalty_{g}_{r}")
                    model.Add(penalty == x[g, r])
                    objective.append(25 * penalty)  # штраф за нежелательный этаж

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
