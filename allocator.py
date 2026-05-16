from ortools.sat.python import cp_model


def optimize_allocation(guests, rooms):

    model = cp_model.CpModel()

    x = {}

    G = len(guests)
    R = len(rooms)

    # =====================
    # VARIABLES
    # =====================
    for g in range(G):
        for r in range(R):
            x[(g, r)] = model.NewBoolVar(f"x_{g}_{r}")

    # =====================
    # 1. каждый гость в 1 комнате
    # =====================
    for g in range(G):
        model.Add(sum(x[(g, r)] for r in range(R)) == 1)

    # =====================
    # 2. вместимость
    # =====================
    for r in range(R):
        model.Add(
            sum(x[(g, r)] for g in range(G)) <= int(rooms[r]["capacity"])
        )

    # =====================
    # 3. семьи вместе (safe version)
    # =====================
    for i in range(G):
        for j in range(i + 1, G):

            fam_i = guests[i].get("family_id")
            fam_j = guests[j].get("family_id")

            if fam_i is not None and fam_i == fam_j:

                for r in range(R):
                    model.Add(x[(i, r)] == x[(j, r)])

    # =====================
    # 4. objective: minimize unused space (soft)
    # =====================
    unused = []

    for r in range(R):

        used = model.NewIntVar(0, G, f"used_{r}")

        model.Add(
            used == sum(x[(g, r)] for g in range(G))
        )

        capacity = int(rooms[r]["capacity"])

        slack = model.NewIntVar(0, capacity, f"slack_{r}")

        model.Add(slack == capacity - used)

        unused.append(slack)

    model.Minimize(sum(unused))

    # =====================
    # SOLVE
    # =====================
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    result = []

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):

        for g in range(G):
            for r in range(R):

                if solver.Value(x[(g, r)]) == 1:

                    result.append({
                        "fio": guests[g]["fio"],
                        "room": rooms[r]["room_id"]
                    })

    return result
