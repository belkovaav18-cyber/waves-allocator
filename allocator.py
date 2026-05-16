from ortools.sat.python import cp_model


def optimize_allocation(guests, rooms):

    model = cp_model.CpModel()

    x = {}

    # переменные
    for g in range(len(guests)):
        for r in range(len(rooms)):
            x[(g, r)] = model.NewBoolVar(f"x_{g}_{r}")

    # 1. каждый гость в одной комнате
    for g in range(len(guests)):
        model.Add(sum(x[(g, r)] for r in range(len(rooms))) == 1)

    # 2. вместимость
    for r in range(len(rooms)):
        model.Add(
            sum(x[(g, r)] for g in range(len(guests)))
            <= rooms[r]["capacity"]
        )

    # 3. семьи вместе (упрощённо по фамилии)
    for i in range(len(guests)):
        for j in range(i + 1, len(guests)):
            if guests[i]["family_id"] == guests[j]["family_id"]:
                for r in range(len(rooms)):
                    model.Add(x[(i, r)] == x[(j, r)])

    # 🎯 цель: минимизировать пустые места
    objective_terms = []

    for r in range(len(rooms)):
        used = sum(x[(g, r)] for g in range(len(guests)))
        empty = rooms[r]["capacity"] - used
        objective_terms.append(empty)

    model.Minimize(sum(objective_terms))

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    result = []

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):

        for g in range(len(guests)):
            for r in range(len(rooms)):
                if solver.Value(x[(g, r)]) == 1:
                    result.append({
                        "fio": guests[g]["fio"],
                        "room": rooms[r]["room_id"]
                    })

    return result
