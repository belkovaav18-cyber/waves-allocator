# config.py

# Веса для штрафов в solver
WEIGHTS = {
    "gender_conflict": 1000,  # Самый большой штраф - нельзя мужчин с женщинами
    "city_diff": 50,
    "status_diff": 100,  # Штраф за разный статус (студент vs профессор)
}

# Статусы и их приоритеты для совместимости
STATUS_HIERARCHY = {
    'student': 1,
    'postgraduate': 2,
    'assistant': 3,
    'docent': 4,
    'professor': 5,
    'academician': 5
}

# Максимальная допустимая разница в статусе для совместного проживания
MAX_STATUS_DIFFERENCE = 2

# Максимальная допустимая разница в возрасте для совместного проживания
MAX_AGE_DIFFERENCE = 10
