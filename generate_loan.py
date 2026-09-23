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
