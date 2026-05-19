import pandas as pd
from solver_debug import solve_simple as solve
from feasibility import find_impossible_groups, split_groups


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
    
    try:
        result = solve(guests, rooms)
        
        if "error" in result.columns or len(result) == 0:
            debug["error"] = "No feasible solution"
            return result, debug
        
        return result, debug
        
    except Exception as e:
        print(f"Error in solver: {e}")
        debug["error"] = str(e)
        return pd.DataFrame([{"error": str(e)}]), debug
