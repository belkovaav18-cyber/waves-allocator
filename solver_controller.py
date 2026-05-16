from solver import solve
from feasibility import find_impossible_groups, split_groups, explain_fail


def smart_solve(guests_df, rooms_df):

    debug = {}

    guests = guests_df
    rooms = rooms_df
    non_residents = [g for g in guests if not g.get("will_stay", True)]
    residents = [g for g in guests if g.get("will_stay", True)]

    debug["input_size"] = len(guests)

    problems = find_impossible_groups(guests, rooms)
    debug["impossible_groups"] = problems

    fixed = split_groups(guests, rooms)
    debug["after_split"] = len(fixed)

    result = solve(fixed, rooms)

    if "error" in result.columns or len(result) == 0:

        debug["mode"] = "fallback"

        for g in fixed:
            g["group_hard"] = []

        result = solve(fixed, rooms)

    else:
        debug["mode"] = "ok"

    debug["explanations"] = explain_fail(fixed, rooms)

    return result, debug
