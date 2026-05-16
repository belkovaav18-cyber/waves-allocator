from ortools.sat.python import cp_model


def allocate_rooms(guests, rooms):

    model = cp_model.CpModel()

    G = len(guests)
    R = len(rooms)

    x = {}

    # =========================
    # VARIABLES
    # =========================
    for g in range(G):
        for r in range(R):
            x[(g, r)] = model.NewBoolVar(f"x_{g}_{r}")

    # =========================
    # HARD CONSTRAINTS
    # =========================

    # 1. каждый гость в 1 комнате
    for g in range(G):
        model.Add(sum(x[(g, r)] for r in range(R)) == 1)

    # 2. вместимость
    for r in range(R):
        model.Add(
            sum(x[(g, r)] for g in range(G))
            <= int(rooms[r]["вместимость"])
        )

    # =========================
    # FAMILY HARD CONSTRAINT
    # =========================
    families = {}

    for i, g in enumerate(guests):
        fam = g.get("family_id")
        if fam:
            families.setdefault(fam, []).append(i)

    for fam, members in families.items():
        for r in range(R):
            for i in members:
                for j in members:
                    model.Add(x[(i, r)] == x[(j, r)])

    # =========================
    # SOFT CONSTRAINTS (objective)
    # =========================
    penalties = []

    BIG_M = 1000

    # 1. gender imbalance penalty
    for r in range(R):

        males = []
        females = []

        for g in range(G):
            if guests[g]["gender"] == "M":
                males.append(x[(g, r)])
            else:
                females.append(x[(g, r)])

        model.AddHint(sum(males), 0)
        model.AddHint(sum(females), 0)

        diff = model.NewIntVar(0, 100, f"gender_diff_{r}")

        model.AddAbsEquality(
            diff,
            sum(males) - sum(females)
        )

        penalties.append(diff * 10)

    # 2. city mixing penalty
    for r in range(R):
        for i in range(G):
            for j in range(i + 1, G):

                if guests[i].get("city") and guests[j].get("city"):

                    if guests[i]["city"] != guests[j]["city"]:
                        penalties.append(x[(i, r)] * x[(j, r)] * 5)

    # 3. unused capacity penalty
    for r in range(R):
        used = sum(x[(g, r)] for g in range(G))
        capacity = int(rooms[r]["вместимость"])

        empty = model.NewIntVar(0, capacity, f"empty_{r}")
        model.Add(empty == capacity - used)

        penalties.append(empty)

    # 4. professor preference
    for g in range(G):
        if guests[g].get("status") == "professor":
            for r in range(R):
                if int(rooms[r]["вместимость"]) > 1:
                    penalties.append(x[(g, r)] * 3)

    # =========================
    # OBJECTIVE
    # =========================
    model.Minimize(sum(penalties))

    # =========================
    # SOLVER
    # =========================
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10

    status = solver.Solve(model)

    result = []
    explanation = []

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):

        for g in range(G):
            assigned_room = None

            for r in range(R):
                if solver.Value(x[(g, r)]) == 1:
                    assigned_room = rooms[r]["room_id"]

            result.append({
                "fio": guests[g]["fio"],
                "gender": guests[g]["gender"],
                "age": guests[g].get("age"),
                "city": guests[g].get("city"),
                "room": assigned_room
            })

            if assigned_room is None:
                explanation.append((guests[g]["fio"], "NO ASSIGNMENT"))

    return result, explanation
