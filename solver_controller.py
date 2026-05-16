from solver import solve
from feasibility import find_impossible_groups, split_groups, explain_fail


def smart_solve(guests_df, rooms_df):

    debug = {}

    # force clean list of dicts
    guests_df = [g for g in guests_df if isinstance(g, dict)]

    debug["input_size"] = len(guests_df)

    problems = find_impossible_groups(guests_df, rooms_df)
    debug["impossible_groups"] = problems

    fixed = split_groups(guests_df, rooms_df)
    debug["after_split"] = len(fixed)

    result = solve(fixed, rooms_df)

    if "error" in result.columns or len(result) == 0:

        debug["mode"] = "fallback"

        for g in fixed:
            g["group_hard"] = []

        result = solve(fixed, rooms_df)

    else:
        debug["mode"] = "strict"

    debug["explanations"] = explain_fail(fixed, rooms_df)

    return result, debug
