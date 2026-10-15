import math
import json
from pathlib import Path
import random
import numpy as np
import pandas as pd


# --- Блок генерации нетто-баланса

""" 
Если учесть, что
	- в каждой строке указан credit для банка i (сколько должен банк i другим);
	- в каждом столбце указан debit для банка j (сколько другие должны банку j);

то получается, что (сумма debit - сумма credit) = итоговому долговому обязательству/требование банка \n
(положительное число означает долговое обязательво --> другие должны банку i, 
 отрицательное число означает долговое требование  --> банк i должен другим)
"""

# --- Блок генерации матрицы долгов
# WARN --- ПЕРЕПИСАТЬ ПОТОМ ЛОГИКУ логнормально --> ядро-переферия
# по статье https://arxiv.org/html/1511.08068v3#S2

# Настройки ЛОГНОРМАЛЬНОГО РАСПРЕДЕЛЕНИЯ — пример


def generate_debt_matrix(
    number_of_banks,
    graph_density,
    median_debt=100.0,
    sigma=0.8,
):
    """
    Функция создаёт матрицу долгов между банками.

    На вход:
        number_of_banks — количество банков;
        graph_density — строгая верхняя граница плотности сети;
        median_debt — медиана распределения суммы долга;
        sigma — стандартное отклонение логарифма суммы долга.

    На выходе матрица debts:
        debts[i][j] — сколько банк i должен банку j.
    """

    # проверяем параметры генерации
    if number_of_banks < 2:
        raise ValueError("Количество банков должно быть не меньше 2")

    if not 0 < graph_density <= 1:
        raise ValueError("Необходимо: 0 < graph_density <= 1")

    if median_debt <= 0 or sigma < 0:
        raise ValueError("Необходимо: median_debt > 0 и sigma >= 0")

    n = number_of_banks

    # создаём матрицу без долгов
    debts = [[0.0 for _ in range(n)] for _ in range(n)]

    # собираем все возможные связи, кроме долгов самому себе
    possible_edges = [
        (i, j)
        for i in range(n)
        for j in range(n)
        if i != j
    ]

    # определяем количество связей для плотности строго ниже заданной
    edge_count = math.ceil(graph_density * len(possible_edges)) - 1

    # случайно выбираем связи между банками
    selected_edges = random.sample(possible_edges, edge_count)

    # для каждой выбранной связи генерируем сумму долга
    for i, j in selected_edges:
        debts[i][j] = round(
            random.lognormvariate(
                math.log(median_debt),
                sigma,
            )
        )  # WARN --> ПОТОМ УБРАТЬ ROUND

    return debts

# --- Блок расчёта характеристик сети


def calculation_network_characteristics(debts):
    """
    Функция рассчитывает характеристики связности сети.

    На вход матрица долгов.

    На выход:
        row_missing_shares — доли отсутствующих связей по строкам;
        actual_density — фактическая плотность сети.

    Диагональ матрицы в расчётах не учитывается.
    """

    n = len(debts)

    if n < 2:
        raise ValueError("Для расчёта плотности необходимо не меньше 2 банков")

    # считаем количество отсутствующих связей в каждой строке
    zero_counts = [
        sum(debts[i][j] == 0 for j in range(n) if i != j)
        for i in range(n)
    ]

    # рассчитываем долю отсутствующих связей для каждой строки
    row_missing_shares = [
        count / (n - 1)
        for count in zero_counts
    ]

    # рассчитываем долю отсутствующих связей во всей сети
    total_missing_share = sum(zero_counts) / (n * (n - 1))

    # рассчитываем долю существующих связей во всей сети
    actual_density = 1 - total_missing_share

    return row_missing_shares, actual_density

# --- Блок вывода характеристик сети


def print_network_characteristics(row_missing_shares, actual_density, graph_density):
    """
    Функция выводит рассчитанные характеристики сети.

    На вход доли отсутствующих связей по строкам и плотность сети.
    """

    # выводим долю отсутствующих связей для каждого банка
    for i, share in enumerate(row_missing_shares):
        print(
            f"Доля отсутствующих связей для строки {i}",
            "\t", round(share, 2),
        )

    print()

    # выводим фактическую плотность всей сети
    print(
        "Плотность графа (доля связей)",
        "\t", round(actual_density, 6),
    )
    if round(actual_density, 2) == graph_density:
        print("Всё корректно", "\t", round(actual_density, 2))
    else:
        print("Всё НЕ корректно", round(
            actual_density, 2), "!=", graph_density)


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


# --- БЛОК подрыва


def start_network_disruption(detonation_bank_number, capital):
    """
    Функция обнуляет капитал выбранного банка.

    На вход:
        detonation_bank_number — индекс банка, начиная с нуля;
        capital — начальные капиталы банков.

    На выходе новый список капиталов после первоначального подрыва.
    """

    # проверяем, существует ли банк с таким индексом
    if not 0 <= detonation_bank_number < len(capital):
        raise ValueError("Номер банка выходит за границы списка")

    # создаём отдельный список капиталов после подрыва
    capital_after_shock = capital.copy()

    # обнуляем капитал выбранного банка
    capital_after_shock[detonation_bank_number] = 0.0

    return capital_after_shock


def network_recalculation(debts, capital_after_shock, bankrupt_list_mask):
    """
    Функция рассчитывает потери от известных банкротов
    и пересчитывает капитал каждого банка.

    На вход:
        debts — исходная матрица долгов;
        capital_after_shock — капитал после первоначального шока;
        bankrupt_list_mask — маска всех уже известных банкротов.

    На выход:
        capital — капитал после учёта потерь;
        losses — суммарные потери каждого банка от этих банкротов.
    """

    n = len(debts)

    # создаём список потерь для всех банков
    losses = [0.0] * n

    # перебираем банки-должники
    for j in range(n):

        # проверяем, обанкротился ли должник
        if bankrupt_list_mask[j]:

            # добавляем каждому кредитору потерю его требования
            for i in range(n):
                losses[i] += debts[j][i]

    # вычитаем потери из капитала после первоначального шока
    capital = [
        capital_after_shock[i] - losses[i]
        for i in range(n)
    ]

    return capital, losses


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


def how_many_bankruptcies(new_bankrupt_mask):
    """
    Функция определяет, нужна ли следующая волна.

    На вход маска новых банкротов.

    На выход:
        True — появились новые банкроты;
        False — новых банкротов нет.
    """

    # проверяем, появился ли хотя бы один новый банкрот
    return bool(np.any(new_bankrupt_mask))


# --- Основной сценарий программы


def main():
    # Путь к конфигу, который лежит рядом с этим скриптом
    config_path = Path(__file__).with_name("config.json")

    # Читаем JSON и получаем обычный словарь Python
    with config_path.open(encoding="utf-8") as file:
        config = json.load(file)

    # Достаём значения по названиям ключей
    number_of_banks = config["number_of_banks"]
    graph_density = config["graph_density"]

    # --- Блок генерации матрицы долгов
    debts = generate_debt_matrix(
        number_of_banks=config["number_of_banks"],
        graph_density=config["graph_density"],
        median_debt=100.0,
        sigma=0.8,
    )

    # --- Блок расчёта характеристик сети

    # рассчитываем связность сети
    row_missing_shares, actual_density = (
        calculation_network_characteristics(debts)
    )

    # --- Блок проверок (для строк - разные значения, для графа = graph_density) -- WARN --
    # выводим характеристики сети
    print_network_characteristics(
        row_missing_shares,
        actual_density,
        graph_density
    )

    # --- Блок формирования нетто-баланса, cash и capital

    net_balance = calculation_net_balance(debts, number_of_banks)[0]

    cash, capital = calculation_initial_balance(
        net_balance,
        min_buffer=10.0,
        max_buffer=50.0,
    )

    # --- Блок первого подрыва 
    
    # выбираем банк для первоначального подрыва
    detonation_bank_number = 0

    # применяем первоначальный шок
    capital_after_shock = start_network_disruption(
        detonation_bank_number,
        capital,
    )
    
    # сравниваем капитал до и после шока
    print("Капитал до шока:", capital)
    print("Капитал после шока:", capital_after_shock)
    
    # определяем банкротов после первоначального шока
    bankrupt_list_mask = who_is_bankrupt(capital_after_shock)

    # рассчитываем потери и обновляем капитал
    capital, losses = network_recalculation(
        debts,
        capital_after_shock,
        bankrupt_list_mask,
    )
    
    # выводим результат первого пересчёта
    print("Банкроты до пересчёта:", bankrupt_list_mask)
    print("Потери банков:", losses)
    print("Капитал после пересчёта:", capital)

if __name__ == "__main__":
    main()
