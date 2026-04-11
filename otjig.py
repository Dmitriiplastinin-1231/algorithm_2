from graphClass import Graph
import math
import random

g = Graph.load_from_stp("berlin52.stp")

# Ищем гамильтонов цикл (случайный поиск, 100 попыток, таймаут 5 секунд)
cycle = g.find_hamiltonian_cycle(max_attempts=10000, timeout=5, method='random')
if cycle:
    print(f"Найден цикл из {len(cycle)} вершин: {cycle[:10]}...")
    # Отображаем граф с выделенным циклом
    cycle.append(cycle[0])
    print(g.path_length(cycle))
    g.display(path=cycle, max_nodes=1000, with_labels=False)
else:
    print("Цикл не найден")





def otjig(file_name, temp_k=0.98):
    temperature = 100
    
    
    g = Graph.load_from_stp(file_name)
    cycle = g.find_hamiltonian_cycle(max_attempts=10000, timeout=5, method='random')
    if not cycle:
        print("Цикл не найден")
        return None
        

    # print(f"Найден цикл из {len(cycle)} вершин: {cycle[:10]}...")
    # g.display(path=cycle, max_nodes=1000, with_labels=False)
    
    
    cycle.append(cycle[0])
    cycle_full_weight = g.path_length(cycle)
    print(cycle_full_weight)

    while temperature > 0.1:
        ind = 0
        ind = 0
        while True:
            ind1 = random.randint(0, g.num_nodes - 2)
            ind2 = random.randint(0, g.num_nodes - 2)
            print(ind1, ind2)

            cycle[ind1], cycle[ind2] = cycle[ind2], cycle[ind1]
            if g.verify_path(cycle): break

            cycle[ind1], cycle[ind2] = cycle[ind2], cycle[ind1]


        newWeight = g.path_length(cycle)
        p = 100 * math.exp((cycle_full_weight-newWeight) / temperature)


        k = random.randint(0, 100)
        print(k, p, cycle_full_weight, newWeight)
        if (k > p):
            cycle[ind1], cycle[ind2] = cycle[ind2], cycle[ind1]
        else:
            cycle_full_weight = newWeight

        temperature = temperature*temp_k





otjig("berlin52.stp")