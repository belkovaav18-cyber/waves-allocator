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
    
    age_a = a.get("age")
    age_b = b.get("age")
    if age_a and age_b:
        age_diff = abs(age_a - age_b)
        if age_diff > 10:
            cost += 100
        elif age_diff > 5:
            cost += 50

    return cost


# =========================================================
# HELPER FUNCTIONS
# =========================================================
def get_floor_from_room_id(room_id):
    room_str = str(room_id)
    if '-' in room_str:
        after_hyphen = room_str.split('-')[1]
        if after_hyphen and after_hyphen[0].isdigit():
            return int(after_hyphen[0])
    digits = ''.join(filter(str.isdigit, room_str))
    if digits and digits[0].isdigit():
        return int(digits[0])
    return None


def get_building_from_room_id(room_id):
    room_str = str(room_id)
    if '-' in room_str:
        building = room_str.split('-')[0]
        if building.isdigit():
            return int(building)
    return None


def is_status_compatible(status1, status2):
    status_hierarchy = {
        'student': 1, 'postgraduate': 2, 'assistant': 3,
        'docent': 4, 'professor': 5, 'academician': 5
    }
    level1 = status_hierarchy.get(status1, 0)
    level2 = status_hierarchy.get(status2, 0)
    return abs(level1 - level2) <= 2


# =========================================================
# SOLVER
# =========================================================
def solve(guests, rooms):
    model = cp_model.CpModel()
    G = range(len(guests))
    R = range(len(rooms))
    x = {}

    # VARIABLES
    for g in G:
        for r in R:
            x[g, r] = model.NewBoolVar(f"x_{g}_{r}")

    # ONE ROOM PER GUEST
    for g in G:
        model.Add(sum(x[g, r] for r in R) == 1)

    # CAPACITY
    for r in R:
        cap = int(rooms[r]["вместимость"])
        model.Add(sum(x[g, r] for g in G) <= cap)

    objective = []

    # =====================================================
    # HARD CONSTRAINTS
    # =====================================================

    # 1. MUST BE SINGLE ROOM
    for g in G:
        if guests[g].get("must_be_single_room", False):
            for r in R:
                if int(rooms[r]["вместимость"]) != 1:
                    model.Add(x[g, r] == 0)

    # 2. FORCED YELLOW BUILDING
    for g in G:
        if guests[g].get("preferred_building") == "yellow":
            for r in R:
                building = get_building_from_room_id(rooms[r]["room_id"])
                if building != 2:
                    model.Add(x[g, r] == 0)

    # 3. TOGETHER GROUPS (HARD)
    for g in G:
        for other_fio in guests[g].get("group_hard", []):
            if other_fio in ["NO_SUBLEASE", "MUST_BE_SINGLE"]:
                continue
            for h in G:
                if guests[h]["fio"] != other_fio:
                    continue
                for r in R:
                    model.Add(x[g, r] == x[h, r])

    # 4. NO SUBLEASE
    for g in G:
        if guests[g].get("require_no_subleaser", False):
            for r in R:
                cap = int(rooms[r]["вместимость"])
                if cap == 2:
                    model.Add(sum(x[k, r] for k in G) <= 1).OnlyEnforceIf(x[g, r])

    # 5. STATUS COMPATIBILITY
    for g1 in G:
        for g2 in range(g1 + 1, len(guests)):
            if not is_status_compatible(guests[g1].get("status", "student"), 
                                       guests[g2].get("status", "student")):
                for r in R:
                    model.Add(x[g1, r] + x[g2, r] <= 1)

    # 6. GENDER SEPARATION (разнополых вместе нельзя, если не просили)
    # Создаем множество пар, которые ПРОСИЛИ жить вместе
    together_pairs = set()
    for g in G:
        for other_fio in guests[g].get("group_hard", []):
            if other_fio in ["NO_SUBLEASE", "MUST_BE_SINGLE"]:
                continue
            for h in G:
                if guests[h]["fio"] == other_fio:
                    together_pairs.add((min(g, h), max(g, h)))
                    break

    # Запрещаем разнополых в одной комнате
    for g1 in G:
        for g2 in range(g1 + 1, len(guests)):
            gender1 = guests[g1].get("gender")
            gender2 = guests[g2].get("gender")
            
            if gender1 != gender2:
                requested_together = (g1, g2) in together_pairs
                if not requested_together:
                    for r in R:
                        model.Add(x[g1, r] + x[g2, r] <= 1)

    # =====================================================
    # SOFT CONSTRAINTS
    # =====================================================

    # SOFT 1: COUPLE LOGIC
    for g in G:
        hard_group = guests[g].get("group_hard", [])
        req = guests[g].get("room_type")
        if len(hard_group) != 1 or req != 2:
            continue
        partner_fio = hard_group[0]
        for h in G:
            if guests[h]["fio"] != partner_fio:
                continue
            for r in R:
                if int(rooms[r]["вместимость"]) != 2:
                    continue
                both = model.NewBoolVar(f"couple_{g}_{h}_{r}")
                model.Add(both <= x[g, r])
                model.Add(both <= x[h, r])
                model.Add(both >= x[g, r] + x[h, r] - 1)
                model.Add(sum(x[k, r] for k in G) <= 2).OnlyEnforceIf(both)

    # SOFT 2: SOFT GROUPS
    for g in G:
        for other_fio in guests[g].get("group_soft", []):
            for h in G:
                if guests[h]["fio"] != other_fio:
                    continue
                for r in R:
                    t = model.NewBoolVar(f"soft_{g}_{h}_{r}")
                    model.Add(t <= x[g, r])
                    model.Add(t <= x[h, r])
                    model.Add(t >= x[g, r] + x[h, r] - 1)
                    objective.append(-50 * t)

    # SOFT 3: AVOID GROUPS
    for g in G:
        for other_fio in guests[g].get("group_avoid", []):
            for h in G:
                if guests[h]["fio"] != other_fio:
                    continue
                for r in R:
                    t = model.NewBoolVar(f"avoid_{g}_{h}_{r}")
                    model.Add(t <= x[g, r])
                    model.Add(t <= x[h, r])
                    model.Add(t >= x[g, r] + x[h, r] - 1)
                    objective.append(100 * t)

    # SOFT 4: RED BUILDING
    for g in G:
        if guests[g].get("preferred_building") == "red":
            for r in R:
                building = get_building_from_room_id(rooms[r]["room_id"])
                if building != 1:
                    penalty = model.NewBoolVar(f"red_building_penalty_{g}_{r}")
                    model.Add(penalty == x[g, r])
                    objective.append(40 * penalty)

    # SOFT 5: PREFERRED FLOOR
    for g in G:
        preferred_floor = guests[g].get("preferred_floor")
        if preferred_floor is not None:
            for r in R:
                room_floor = get_floor_from_room_id(rooms[r]["room_id"])
                if room_floor != preferred_floor:
                    penalty = model.NewBoolVar(f"floor_penalty_{g}_{r}")
                    model.Add(penalty == x[g, r])
                    objective.append(25 * penalty)

    # SOFT 6: AGE SIMILARITY
    for g1 in G:
        for g2 in range(g1 + 1, len(guests)):
            age1 = guests[g1].get("age")
            age2 = guests[g2].get("age")
            if age1 and age2 and abs(age1 - age2) <= 5:
                for r in R:
                    t = model.NewBoolVar(f"age_similar_{g1}_{g2}_{r}")
                    model.Add(t <= x[g1, r])
                    model.Add(t <= x[g2, r])
                    model.Add(t >= x[g1, r] + x[g2, r] - 1)
                    objective.append(-20 * t)

    # SOFT 7: STATUS SIMILARITY
    for g1 in G:
        for g2 in range(g1 + 1, len(guests)):
            status1 = guests[g1].get("status", "student")
            status2 = guests[g2].get("status", "student")
            if status1 == status2:
                for r in R:
                    t = model.NewBoolVar(f"status_similar_{g1}_{g2}_{r}")
                    model.Add(t <= x[g1, r])
                    model.Add(t <= x[g2, r])
                    model.Add(t >= x[g1, r] + x[g2, r] - 1)
                    objective.append(-15 * t)

    # SOFT 8: CONFLICTS
    for g1 in G:
        for g2 in range(g1 + 1, len(guests)):
            cost = conflict_cost(guests[g1], guests[g2])
            if cost == 0:
                continue
            for r in R:
                p = model.NewBoolVar(f"pair_{g1}_{g2}_{r}")
                model.Add(p <= x[g1, r])
                model.Add(p <= x[g2, r])
                model.Add(p >= x[g1, r] + x[g2, r] - 1)
                objective.append(cost * p)

    # SOFT 9: ROOM TYPE MISMATCH
    for g in G:
        req = guests[g].get("room_type")
        if req is None:
            continue
        for r in R:
            cap = int(rooms[r]["вместимость"])
            if cap != req:
                penalty = model.NewBoolVar(f"room_penalty_{g}_{r}")
                model.Add(penalty == x[g, r])
                objective.append(50 * penalty)

    # SOFT 10: ALTERNATIVE VARIANTS
    for g in G:
        variants = guests[g].get("allocation_variants", [])
        for variant in variants:
            room_type = variant.get("room_type")
            group_fios = variant.get("group", [])
            priority = variant.get("priority", 1)
            
            group_indices = []
            for h in G:
                if guests[h]["fio"] in group_fios:
                    group_indices.append(h)
            
            if len(group_indices) != len(group_fios):
                continue
            
            weight = -100 if priority == 1 else -50
            
            for r in R:
                cap = int(rooms[r]["вместимость"])
                if cap != room_type:
                    continue
                
                all_together = model.NewBoolVar(f"variant_{g}_{r}")
                constraints = [x[h, r] for h in group_indices]
                model.Add(sum(constraints) == len(group_indices)).OnlyEnforceIf(all_together)
                model.Add(sum(constraints) < len(group_indices)).OnlyEnforceIf(all_together.Not())
                objective.append(weight * all_together)

    # SOLVE
    model.Minimize(sum(objective))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30
    solver.parameters.log_search_progress = False
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("No solution found!")
        return pd.DataFrame([{"error": "no solution"}])

    result = []
    for g in G:
        for r in R:
            if solver.Value(x[g, r]):
                result.append({
                    "fio": guests[g]["fio"],
                    "room_id": rooms[r]["room_id"],
                    "room_capacity": rooms[r]["вместимость"],
                    "age": guests[g].get("age"),
                    "status": guests[g].get("status"),
                    "position": guests[g].get("position")
                })

    return pd.DataFrame(result)


def smart_solve(guests, rooms):
    """Обертка для solve с обработкой ошибок и отладкой"""
    debug = {
        "total_guests": len(guests),
        "total_rooms": len(rooms),
        "must_be_single": [],
        "yellow_building_people": [],
        "red_building_people": [],
        "no_subleaser_people": [],
        "together_requests": [],
        "tariff_stats": {"without_subleaser": 0, "with_subleaser": 0},
        "status_stats": {"student": 0, "postgraduate": 0, "professor": 0, "other": 0},
        "age_stats": {"min": None, "max": None, "avg": None}
    }
    
    ages = []
    for guest in guests:
        if guest.get("must_be_single_room"):
            debug["must_be_single"].append(guest["fio"])
        if guest.get("preferred_building") == "yellow":
            debug["yellow_building_people"].append(guest["fio"])
        elif guest.get("preferred_building") == "red":
            debug["red_building_people"].append(guest["fio"])
        if guest.get("require_no_subleaser"):
            debug["no_subleaser_people"].append(guest["fio"])
        if guest.get("group_hard"):
            for h in guest["group_hard"]:
                if h not in ["NO_SUBLEASE", "MUST_BE_SINGLE"]:
                    debug["together_requests"].append(f"{guest['fio']} с {h}")
        tariff_type = guest.get("tariff_type")
        if tariff_type == "without_subleaser":
            debug["tariff_stats"]["without_subleaser"] += 1
        elif tariff_type == "with_subleaser":
            debug["tariff_stats"]["with_subleaser"] += 1
        status = guest.get("status", "other")
        debug["status_stats"][status] = debug["status_stats"].get(status, 0) + 1
        age = guest.get("age")
        if age:
            ages.append(age)
    
    if ages:
        debug["age_stats"]["min"] = min(ages)
        debug["age_stats"]["max"] = max(ages)
        debug["age_stats"]["avg"] = sum(ages) / len(ages)
    
    print("\n" + "="*50)
    print("DEBUG INFO")
    print("="*50)
    print(f"Total guests: {debug['total_guests']}")
    print(f"Must be single: {len(debug['must_be_single'])}")
    print(f"Yellow building forced: {len(debug['yellow_building_people'])}")
    print(f"No sublease required: {len(debug['no_subleaser_people'])}")
    print(f"Together requests: {len(debug['together_requests'])}")
    print(f"Tariff stats: {debug['tariff_stats']}")
    print(f"Status stats: {debug['status_stats']}")
    print(f"Age stats: {debug['age_stats']}")
    print("="*50 + "\n")
    
    result_df = solve(guests, rooms)
    return result_df, debug
