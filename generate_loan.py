import math
import json
from pathlib import Path
import random
import numpy as np
import pandas as pd

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




# -----------

n = len(debts)

# Количество нулей в каждой строке без диагонали
zero_counts = [
    sum(debts[i][j] == 0 for j in range(n) if i != j)
    for i in range(n)
]

# Доля отсутствующих связей для каждой строки
row_missing_shares = [
    count / (n - 1)
    for count in zero_counts
]

# Доля отсутствующих связей во всей матрице
total_missing_share = sum(zero_counts) / (n * (n - 1))


# --- WARN -- Блок проверок (для сстрок - разные значения, для графа = graph_density)
for i in range(n):
    print(f"Доля пропусков для строки {i}",
          "\t", round(row_missing_shares[i], 2))

print("\n")

print(f"Плотность графа (доля связей)", "\t",
      round(1 - total_missing_share, 2))

if round(1 - total_missing_share, 2) == graph_density:
    print("Всё корректно", "\t", round(1 - total_missing_share, 2))
else:
    print("Всё НЕ корректно", round(
        1 - total_missing_share, 2), "!=", graph_density)


# --- Блок генерации нетто-баланса

""" 
Если учесть, что
	- в каждой строке указан credit для банка i (сколько должен банк i другим);
	- в каждом столбце указан debit для банка j (сколько другие должны банку j);

то получается, что (сумма debit - сумма credit) = итоговому долговому обязательству/требование банка \n
(положительное число означает долговое обязательво --> другие должны банку i, 
 отрицательное число означает долговое требование  --> банк i должен другим)
"""


def calculation_net_balance(debts, number_of_banks):
    """
    Функция рассчитывает нетто. То есть должен ли банк i кому то или ему должны.
    Это определется знаком, а кол-во значением.

    На вход матрица долгов и кол-во банков.
    На выходе список значений нетто для всех i-ых банков.
    """

    net_balance = []

    for i in range(number_of_banks):
        sum_credit = 0
        sum_debit = 0
        for j in range(number_of_banks):
            sum_credit += debts[i][j]  # (сколько должен банк i другим)
            # (сколько другие должны банку j) - то есть ничто иное как Актив (будет использовано для расчета Capital)
            sum_debit += debts[j][i]
        net_balance.append(sum_debit - sum_credit)

    return net_balance, sum_debit

# --- Блок генерации балансов банка


def calculation_initial_balance(net_balance, min_buffer=10.0, max_buffer=50.0):
    """
    Формирует начальные денежные средства и капитал банков.

    net_balance — список чистых межбанковских позиций.
    min_buffer, max_buffer — границы дополнительного запаса.

    Возвращает cash и capital — два списка в порядке банков.  
                1. cash - сколько свободных денег на счету у банка;  
                        (Необходим для далнейшего расчета "Коэффициент абсолютной  ликвидности". Подробнее, см. в "Пояснения_допушения.md");  
                2. capital - сумма cash и нетто-баланса  
    """
    if not 0 < min_buffer <= max_buffer:
        raise ValueError("Необходимо: 0 < min_buffer <= max_buffer")

    cash = []
    capital = []
    for balance in net_balance:
        buffer = (
            min_buffer
            + (max_buffer - min_buffer) * random.betavariate(2, 5)
        )

        bank_cash = max(0.0, -balance) + buffer
        bank_capital = bank_cash + balance

        cash.append(round(bank_cash))  			# WARN --> УБРАТЬ ROUND
        capital.append(round(bank_capital))		# WARN --> УБРАТЬ ROUND

    return cash, capital


# --- ВРЕМЕННЫЙ БЛОК --- Блок формирования Cash и capital.


net_balance = calculation_net_balance(debts, number_of_banks)[0]

cash, capital = calculation_initial_balance(
    net_balance,
    min_buffer=10.0,
    max_buffer=50.0,
)


# --- Механизм подрыва

detonation_bank_number = 1  #


def start_network_disruption(detonation_bank_number, debts, cash, capital):
    """
        функция для обнуления активов:	
                1. detonation_bank_number - номер банка который мы подрываем.
                2. debts, cash, capital - матрицы, которые предстоит обнулить для i-го банка и вернуть
    """

    # Обнуление i-го банка
    i = detonation_bank_number
    cash[i] = 0
    capital[i] = 0
    debts[i][:] = [0] * len(debts[i])  # Этот банк никому не должен
    for row in debts:  # Этому банку никто не должен
        row[i] = 0
    
    return debts, cash, capital


def network_recalculation(detonation_bank_number, number_of_banks, debts, net_balance, cash, capital):
    """
    Функция пересчитывает все матрицы сети и возвращает обновленные версии.

    WARN --> Capital обнулили и всё,  
        так как пока что не реализован механизм подсчета коротких зависимостей
    """

    debts = debts  # он без изменений (обнулили и всё)
    net_balance = calculation_net_balance(debts, number_of_banks)[0]
    cash = cash  # он без изменений (обнулили и всё)
    capital = capital  # он без изменений (обнулили и всё)

    return debts, net_balance, cash, capital


def who_is_bankrupt(capital):
    """
    Функция принимает на вход Капитал и выводит список всех банкротов после предыдущей волны банкротств.
    Т.е. получается массив с банкротами (маску), если длина массива равна нулю, сл-но каскад банкротств остановился
    """
    bankrupt_list_mask = np.array([False] * len(capital))
    for index, value in enumerate(capital):
        if value <= 0:
            bankrupt_list_mask[index] = True

    return bankrupt_list_mask


def how_many_bankruptcies(capital):
    """
    Функция принимает капитал. Возвращает флаг: 
    TRUE --> продолжаем каскад (т.е. новая волна банкротств)
    FALSE --> каскад банкротств завершен
    """
    
    bankrupt_list_mask = who_is_bankrupt(capital)
    
    cascade_extension = False
    if sum(bankrupt_list_mask) > 0:
        cascade_extension = True
    
    return cascade_extension