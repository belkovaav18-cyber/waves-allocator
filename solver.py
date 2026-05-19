# solver_debug.py - временный файл для отладки

from ortools.sat.python import cp_model
import pandas as pd


def solve_simple(guests, rooms):
    """Упрощенная версия солвера для отладки"""
    
    model = cp_model.CpModel()
    
    G = range(len(guests))
    R = range(len(rooms))
    
    x = {}
    
    # Переменные
    for g in G:
        for r in R:
            x[g, r] = model.NewBoolVar(f"x_{g}_{r}")
    
    # Один гость - одна комната
    for g in G:
        model.Add(sum(x[g, r] for r in R) == 1)
    
    # Вместимость
    for r in R:
        cap = int(rooms[r]["вместимость"])
        model.Add(sum(x[g, r] for g in G) <= cap)
    
    objective = []
    
    # Только самые важные ограничения
    
    # 1. MUST_BE_SINGLE
    for g in G:
        if guests[g].get("must_be_single_room", False):
            for r in R:
                if int(rooms[r]["вместимость"]) != 1:
                    model.Add(x[g, r] == 0)
    
    # 2. FORCED YELLOW
    def get_building(room_id):
        room_str = str(room_id)
        if '-' in room_str:
            building = room_str.split('-')[0]
            if building.isdigit():
                return int(building)
        return None
    
    for g in G:
        if guests[g].get("preferred_building") == "yellow":
            for r in R:
                building = get_building(rooms[r]["room_id"])
                if building != 2:
                    model.Add(x[g, r] == 0)
    
    # 3. TOGETHER GROUPS (только самые важные)
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
    
    # Минимизируем
    model.Minimize(sum(objective))
    
    # Решаем
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30
    status = solver.Solve(model)
    
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("No solution found!")
        # Выводим информацию о невозможности
        print("\nTrying to find which constraint is impossible...")
        
        # Проверяем по отдельности
        total_guests = len(guests)
        yellow_forced = sum(1 for g in guests if g.get("preferred_building") == "yellow")
        single_required = sum(1 for g in guests if g.get("must_be_single_room", False))
        no_subleaser = sum(1 for g in guests if g.get("require_no_subleaser", False))
        
        yellow_rooms = sum(1 for r in rooms if str(r.get("room_id", "")).startswith(('2-', '2')))
        single_rooms = sum(1 for r in rooms if int(r.get("вместимость", 1)) == 1)
        
        print(f"Yellow forced guests: {yellow_forced}, Yellow rooms: {yellow_rooms}")
        print(f"Single required guests: {single_required}, Single rooms: {single_rooms}")
        print(f"No sublease guests: {no_subleaser}")
        
        return pd.DataFrame([{"error": f"No solution: yellow={yellow_forced}>{yellow_rooms} or single={single_required}>{single_rooms}"}])
    
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
