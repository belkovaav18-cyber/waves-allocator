from ortools.sat.python import cp_model
import pandas as pd
from config import WEIGHTS


# =========================================================
# COST
# =========================================================
def conflict_cost(a, b):
    """
    Рассчитывает штраф за совместное проживание
    """
    cost = 0

    # Гендерный конфликт (самый большой штраф)
    if a["gender"] != b["gender"]:
        cost += WEIGHTS["gender_conflict"]

    # Разные города
    if a.get("city") != b.get("city"):
        cost += WEIGHTS["city_diff"]

    # Разный статус (студент/аспирант/профессор)
    if a.get("status") != b.get("status"):
        cost += WEIGHTS["status_diff"]
    
    # Штраф за большую разницу в возрасте
    age_a = a.get("age")
    age_b = b.get("age")
    if age_a and age_b:
        age_diff = abs(age_a - age_b)
        if age_diff > 10:
            cost += 100  # Большая разница в возрасте
        elif age_diff > 5:
            cost += 50   # Средняя разница

    return cost


# =========================================================
# HELPER: GET FLOOR FROM ROOM ID
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


# =========================================================
# HELPER: GET BUILDING FROM ROOM ID
# =========================================================
def get_building_from_room_id(room_id):
    room_str = str(room_id)
    
    if '-' in room_str:
        building = room_str.split('-')[0]
        if building.isdigit():
            return int(building)
    
    return None


# =========================================================
# HELPER: CHECK STATUS COMPATIBILITY
# =========================================================
def is_status_compatible(status1, status2):
    """
    Проверяет совместимость статусов для проживания
    Нельзя селить вместе: профессора со студентом, профессора с аспирантом
    """
    # Определяем иерархию статусов
    status_hierarchy = {
        'student': 1,
        'postgraduate': 2,
        'assistant': 3,
        'docent': 4,
        'professor': 5,
        'academician': 5
    }
    
    level1 = status_hierarchy.get(status1, 0)
    level2 = status_hierarchy.get(status2, 0)
    
    # Разница в статусе не должна быть больше 2 уровней
    return abs(level1 - level2) <= 2


# =========================================================
# SOLVER WITH HIERARCHY
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
    # ONE ROOM (каждый гость в одной комнате)
    # =====================================================
    for g in G:
        model.Add(
            sum(x[g, r] for r in R) == 1
        )

    # =====================================================
    # CAPACITY (вместимость комнат)
    # =====================================================
    for r in R:
        cap = int(rooms[r]["вместимость"])
        model.Add(
            sum(x[g, r] for g in G) <= cap
        )

    objective = []

    # =====================================================
    # 1. HARD: MUST BE SINGLE ROOM (спецсписок - только одноместные)
    # =====================================================
    for g in G:
        if guests[g].get("must_be_single_room", False):
            for r in R:
                cap = int(rooms[r]["вместимость"])
                if cap != 1:
                    model.Add(x[g, r] == 0)

    # =====================================================
    # 2. HARD: FORCED YELLOW BUILDING (спецсписок - желтый корпус)
    # =====================================================
    for g in G:
        if guests[g].get("preferred_building") == "yellow":
            for r in R:
                room_building = get_building_from_room_id(rooms[r]["room_id"])
                if room_building != 2:
                    model.Add(x[g, r] == 0)

    # =====================================================
    # 3. HARD: TOGETHER GROUPS (комментарий: "поселить с")
    # =====================================================
    for g in G:
        for other_fio in guests[g].get("group_hard", []):
            # Пропускаем NO_SUBLEASE и MUST_BE_SINGLE (это флаги, не люди)
            if other_fio in ["NO_SUBLEASE", "MUST_BE_SINGLE"]:
                continue
            for h in G:
                if guests[h]["fio"] != other_fio:
                    continue
                for r in R:
                    model.Add(x[g, r] == x[h, r])

    # =====================================================
    # 4. HARD: NO SUBLEASE (тариф без подселения)
    # =====================================================
    for g in G:
        if guests[g].get("require_no_subleaser", False):
            for r in R:
                cap = int(rooms[r]["вместимость"])
                # В двуместную комнату нельзя подселять других
                if cap == 2:
                    model.Add(
                        sum(x[k, r] for k in G) <= 1
                    ).OnlyEnforceIf(x[g, r])

    # =====================================================
    # 5. HARD: STATUS COMPATIBILITY (студентов с профессорами нельзя)
    # =====================================================
    for g1 in G:
        for g2 in range(g1 + 1, len(guests)):
            if not is_status_compatible(guests[g1].get("status", "student"), 
                                       guests[g2].get("status", "student")):
                for r in R:
                    # Запрещаем селить вместе
                    model.Add(x[g1, r] + x[g2, r] <= 1)

    # =====================================================
    # SOFT 1: COUPLE LOGIC (пары в двуместные комнаты)
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
    
                both = model.NewBoolVar(f"couple_{g}_{h}_{r}")
                model.Add(both <= x[g, r])
                model.Add(both <= x[h, r])
                model.Add(both >= x[g, r] + x[h, r] - 1)
                model.Add(sum(x[k, r] for k in G) <= 2).OnlyEnforceIf(both)

    # =====================================================
    # SOFT 2: SOFT GROUPS (желательно вместе)
    # =====================================================
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
                    objective.append(-50 * t)  # Поощрение

    # =====================================================
    # SOFT 3: AVOID GROUPS (не селить вместе)
    # =====================================================
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
                    objective.append(100 * t)  # Штраф

    # =====================================================
    # SOFT 4: RED BUILDING (предпочтение красного корпуса)
    # =====================================================
    for g in G:
        if guests[g].get("preferred_building") == "red":
            for r in R:
                room_building = get_building_from_room_id(rooms[r]["room_id"])
                if room_building != 1:
                    penalty = model.NewBoolVar(f"red_building_penalty_{g}_{r}")
                    model.Add(penalty == x[g, r])
                    objective.append(40 * penalty)

    # =====================================================
    # SOFT 5: PREFERRED FLOOR
    # =====================================================
    for g in G:
        preferred_floor = guests[g].get("preferred_floor")
        if preferred_floor is not None:
            for r in R:
                room_floor = get_floor_from_room_id(rooms[r]["room_id"])
                if room_floor != preferred_floor:
                    penalty = model.NewBoolVar(f"floor_penalty_{g}_{r}")
                    model.Add(penalty == x[g, r])
                    objective.append(25 * penalty)

    # =====================================================
    # SOFT 6: AGE SIMILARITY (поощряем близкий возраст)
    # =====================================================
    for g1 in G:
        for g2 in range(g1 + 1, G):
            age1 = guests[g1].get("age")
            age2 = guests[g2].get("age")
            if age1 and age2 and abs(age1 - age2) <= 5:
                for r in R:
                    t = model.NewBoolVar(f"age_similar_{g1}_{g2}_{r}")
                    model.Add(t <= x[g1, r])
                    model.Add(t <= x[g2, r])
                    model.Add(t >= x[g1, r] + x[g2, r] - 1)
                    objective.append(-20 * t)  # Поощрение за близкий возраст

    # =====================================================
    # SOFT 7: STATUS SIMILARITY (поощряем одинаковый статус)
    # =====================================================
    for g1 in G:
        for g2 in range(g1 + 1, G):
            status1 = guests[g1].get("status", "student")
            status2 = guests[g2].get("status", "student")
            if status1 == status2:
                for r in R:
                    t = model.NewBoolVar(f"status_similar_{g1}_{g2}_{r}")
                    model.Add(t <= x[g1, r])
                    model.Add(t <= x[g2, r])
                    model.Add(t >= x[g1, r] + x[g2, r] - 1)
                    objective.append(-15 * t)  # Поощрение за одинаковый статус

    # =====================================================
    # SOFT 8: CONFLICTS (штраф за неподходящих соседей)
    # =====================================================
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

    # =====================================================
    # SOFT 9: ROOM TYPE MISMATCH
    # =====================================================
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

    # =====================================================
    # SOLVE
    # =====================================================
    model.Minimize(sum(objective))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30
    solver.parameters.log_search_progress = False
    status = solver.Solve(model)

    # =====================================================
    # NO SOLUTION
    # =====================================================
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("No solution found!")
        return pd.DataFrame([{"error": "no solution"}])

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
                    "room_capacity": rooms[r]["вместимость"],
                    "age": guests[g].get("age"),
                    "status": guests[g].get("status"),
                    "position": guests[g].get("position")
                })

    return pd.DataFrame(result)


# =====================================================
# SMART SOLVE
# =====================================================
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
        if status in debug["status_stats"]:
            debug["status_stats"][status] += 1
        else:
            debug["status_stats"]["other"] += 1
        
        age = guest.get("age")
        if age:
            ages.append(age)
    
    if ages:
        debug["age_stats"]["min"] = min(ages)
        debug["age_stats"]["max"] = max(ages)
        debug["age_stats"]["avg"] = sum(ages) / len(ages)
    
    # Печатаем отладку
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
