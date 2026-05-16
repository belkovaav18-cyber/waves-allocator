from solver import solve
from feasibility import (
    find_impossible_groups,
    split_groups,
    explain_fail
)


# =========================================================
# SMART SOLVER
# =========================================================
def smart_solve(guests_df, rooms_df):

    debug = {}

    # ============================
    # STEP 1: precheck
    # ============================
    problems = find_impossible_groups(guests_df, rooms_df)

    debug["impossible_groups"] = problems

    # ============================
    # STEP 2: auto fix
    # ============================
    fixed_guests = split_groups(guests_df, rooms_df)

    debug["after_split_count"] = len(fixed_guests)

    # ============================
    # STEP 3: try strict solve
    # ============================
    result = solve(fixed_guests, rooms_df)

    # ============================
    # STEP 4: fallback if fail
    # ============================
    if "error" in result.columns or len(result) == 0:

        debug["mode"] = "fallback"

        # relax groups by removing hard constraints
        for g in fixed_guests:
            g["group_hard"] = []

        result = solve(fixed_guests, rooms_df)

    else:
        debug["mode"] = "strict_success"

    # ============================
    # STEP 5: explanation engine
    # ============================
    debug["unplaced_reasons"] = explain_fail(fixed_guests, rooms_df)

    return result, debug
