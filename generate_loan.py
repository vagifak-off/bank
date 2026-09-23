import math
import json
from pathlib import Path
import random

# Путь к конфигу, который лежит рядом с этим скриптом
config_path = Path(__file__).with_name("config.json")

# Читаем JSON и получаем обычный словарь Python
with config_path.open(encoding="utf-8") as file:
    config = json.load(file)

# Достаём значения по названиям ключей
number_of_banks = config["number_of_banks"]
graph_density = config["graph_density"]


# ----------------  WARN --- ПЕРЕПИСАТЬ ПОТОМ ЛОГИКУ логнормально --> ядро-переферия по статье "https://arxiv.org/html/1511.08068v3#S2"

# Настройки ЛОГНОРМАЛЬНОГО РАСПРЕДЕЛЕНИЯ — пример
n = number_of_banks
median_debt = 100.0
sigma = .8

debts = [[0.0 for _ in range(n)] for _ in range(n)]

# Все возможные направленные связи, кроме долгов самому себе
possible_edges = [
    (i, j)
    for i in range(n)
    for j in range(n)
    if i != j
]

# Плотность строго меньше graph_density
# Предполагаем n >= 2 и 0 < graph_density <= 1
edge_count = math.ceil(graph_density * len(possible_edges)) - 1

selected_edges = random.sample(possible_edges, edge_count)

for i, j in selected_edges:
    debts[i][j] = round(random.lognormvariate(  			# WARN -- ПОТОМ УБРАТЬ ROUND !!!
        math.log(median_debt),
        sigma,
    ))


print(debts)  # WARN --  убрать
