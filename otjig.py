import argparse
import math
import random
import time

from graphClass import Graph


def cycle_length(graph, tour):
    total = 0.0
    n = len(tour)
    for i in range(n):
        total += graph.get_weight(tour[i], tour[(i + 1) % n])
    return total


def nearest_neighbor_tour(graph, start):
    n = graph.num_nodes
    unvisited = set(range(n))
    unvisited.remove(start)
    tour = [start]
    current = start

    while unvisited:
        nxt = min(unvisited, key=lambda v: graph.get_weight(current, v))
        tour.append(nxt)
        unvisited.remove(nxt)
        current = nxt
    return tour


def initial_hamiltonian_tour(graph, start_vertex):
    cycle = graph.find_hamiltonian_cycle(
        max_attempts=10000, timeout=5, method="random", start_vertex=start_vertex
    )
    if cycle is not None:
        return cycle
    return nearest_neighbor_tour(graph, start_vertex)


def two_opt_delta(graph, tour, i, k):
    n = len(tour)
    a = tour[(i - 1) % n]
    b = tour[i]
    c = tour[k]
    d = tour[(k + 1) % n]
    return (
        graph.get_weight(a, c)
        + graph.get_weight(b, d)
        - graph.get_weight(a, b)
        - graph.get_weight(c, d)
    )


def random_two_opt_indices(n):
    i, k = sorted(random.sample(range(n), 2))
    if i == 0 and k == n - 1:
        return None
    return i, k


def simulated_annealing(graph, restarts=8, steps_per_restart=None, seed=42):
    if seed is not None:
        random.seed(seed)

    n = graph.num_nodes
    if n < 3:
        return list(range(n)), 0.0

    if steps_per_restart is None:
        steps_per_restart = max(5000, n * 200)

    best_tour = None
    best_length = float("inf")
    initial_candidates = min(8, n)
    starts = random.sample(range(n), initial_candidates)

    for restart in range(restarts):
        start_vertex = starts[restart % len(starts)]
        tour = initial_hamiltonian_tour(graph, start_vertex)
        current_length = cycle_length(graph, tour)

        current_tour = tour[:]
        current_best_tour = tour[:]
        current_best_length = current_length

        temperature = current_length / n
        min_temperature = 1e-4
        alpha = (min_temperature / temperature) ** (1.0 / max(1, steps_per_restart - 1))

        for _ in range(steps_per_restart):
            pair = random_two_opt_indices(n)
            if pair is None:
                continue
            i, k = pair
            delta = two_opt_delta(graph, current_tour, i, k)

            if delta < 0 or random.random() < math.exp(-delta / temperature):
                current_tour[i : k + 1] = reversed(current_tour[i : k + 1])
                current_length += delta

                if current_length < current_best_length:
                    current_best_length = current_length
                    current_best_tour = current_tour[:]

            temperature *= alpha

        if current_best_length < best_length:
            best_length = current_best_length
            best_tour = current_best_tour

    return best_tour, best_length


def solve(file_name, restarts=8, steps_per_restart=None, seed=42):
    graph = Graph.load_from_stp(file_name)
    started = time.time()

    baseline_tour = initial_hamiltonian_tour(graph, 0)
    baseline_length = cycle_length(graph, baseline_tour)
    best_tour, best_length = simulated_annealing(
        graph, restarts=restarts, steps_per_restart=steps_per_restart, seed=seed
    )

    elapsed = time.time() - started
    print(f"Файл: {file_name}")
    print(f"Базовый гамильтонов цикл: {baseline_length:.2f}")
    print(f"После отжига:            {best_length:.2f}")
    print(f"Улучшение:               {baseline_length - best_length:.2f}")
    print(f"Время:                   {elapsed:.3f} сек")
    return best_tour, best_length


def main():
    parser = argparse.ArgumentParser(description="Быстрый и точный simulated annealing для TSP/STP.")
    parser.add_argument("file", nargs="?", default="berlin52.stp", help="Путь к .stp файлу")
    parser.add_argument("--restarts", type=int, default=8, help="Количество рестартов")
    parser.add_argument(
        "--steps-per-restart",
        type=int,
        default=None,
        help="Итераций отжига на один рестарт (по умолчанию зависит от n)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Seed для воспроизводимости")
    args = parser.parse_args()
    solve(args.file, restarts=args.restarts, steps_per_restart=args.steps_per_restart, seed=args.seed)


if __name__ == "__main__":
    main()
