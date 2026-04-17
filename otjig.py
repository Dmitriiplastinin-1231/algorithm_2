from graphClass import Graph
import math
import random

MAX_2OPT_INDEX_RETRIES = 50
MAX_3OPT_INDEX_RETRIES = 80
MAX_MOVE_PROPOSALS = 100
CALIBRATION_ATTEMPT_MULTIPLIER = 6
MIN_CALIBRATION_ATTEMPTS = 1000
MIN_TEMP_MULTIPLIER = 10.0
MAX_REHEAT_MULTIPLIER = 3.0


def find_initial_cycle_greedy(g):
    for start_vertex in range(g.num_nodes):
        cycle = g.find_hamiltonian_cycle(method='nearest', start_vertex=start_vertex)
        if cycle:
            return cycle
    return None


def cycle_length(g, route):
    total = 0.0
    n = len(route)
    for i in range(n):
        w = g.get_weight(route[i], route[(i + 1) % n])
        if w is None:
            return None
        total += w
    return total


def _w(g, u, v):
    w = g.get_weight(u, v)
    return None if w is None else float(w)


def random_2opt_indices(n, rng):
    if n < 4:
        return None
    for _ in range(MAX_2OPT_INDEX_RETRIES):
        i = rng.randrange(0, n - 1)
        j = rng.randrange(i + 1, n)
        if j == i + 1:
            continue
        if i == 0 and j == n - 1:
            continue
        return i, j
    return None


def delta_2opt(g, route, i, j):
    n = len(route)
    a = route[i]
    b = route[(i + 1) % n]
    c = route[j]
    d = route[(j + 1) % n]
    wab = _w(g, a, b)
    wcd = _w(g, c, d)
    wac = _w(g, a, c)
    wbd = _w(g, b, d)
    if None in (wab, wcd, wac, wbd):
        return None
    return (wac + wbd) - (wab + wcd)


def apply_2opt(route, i, j):
    route[i + 1:j + 1] = reversed(route[i + 1:j + 1])


def random_3opt_indices(n, rng):
    if n < 6:
        return None
    for _ in range(MAX_3OPT_INDEX_RETRIES):
        i = rng.randrange(0, n - 3)
        j = rng.randrange(i + 1, n - 2)
        k = rng.randrange(j + 1, n - 1)
        return i, j, k
    return None


def delta_3opt(g, route, i, j, k):
    n = len(route)
    a = route[i]
    b = route[(i + 1) % n]
    c = route[j]
    d = route[(j + 1) % n]
    e = route[k]
    f = route[(k + 1) % n]

    removed = [_w(g, a, b), _w(g, c, d), _w(g, e, f)]
    added = [_w(g, a, c), _w(g, b, e), _w(g, d, f)]
    if any(w is None for w in removed + added):
        return None
    return sum(added) - sum(removed)


def apply_3opt(route, i, j, k):
    route[i + 1:j + 1] = reversed(route[i + 1:j + 1])
    route[j + 1:k + 1] = reversed(route[j + 1:k + 1])


def propose_move(g, route, rng, p_3opt=0.35):
    use_3opt = rng.random() < p_3opt
    for _ in range(MAX_MOVE_PROPOSALS):
        if use_3opt:
            idx = random_3opt_indices(len(route), rng)
            if not idx:
                break
            i, j, k = idx
            delta = delta_3opt(g, route, i, j, k)
            if delta is not None:
                return {"type": "3opt", "idx": (i, j, k), "delta": delta}
        else:
            idx = random_2opt_indices(len(route), rng)
            if not idx:
                break
            i, j = idx
            delta = delta_2opt(g, route, i, j)
            if delta is not None:
                return {"type": "2opt", "idx": (i, j), "delta": delta}
        use_3opt = not use_3opt
    return None


def apply_move(route, move):
    if move["type"] == "2opt":
        i, j = move["idx"]
        apply_2opt(route, i, j)
    else:
        i, j, k = move["idx"]
        apply_3opt(route, i, j, k)


def calibrate_initial_temperature(g, route, rng, samples=400, target_acceptance=0.8, default_temp=100.0):
    if not (0.0 < target_acceptance < 1.0):
        return default_temp

    uphill = []
    attempts = 0
    max_attempts = max(samples * CALIBRATION_ATTEMPT_MULTIPLIER, MIN_CALIBRATION_ATTEMPTS)

    while len(uphill) < samples and attempts < max_attempts:
        attempts += 1
        move = propose_move(g, route, rng)
        if not move:
            continue
        if move["delta"] > 0:
            uphill.append(move["delta"])

    if not uphill:
        return default_temp

    avg_uphill = sum(uphill) / len(uphill)
    if avg_uphill <= 0:
        return default_temp

    t0 = -avg_uphill / math.log(target_acceptance)
    if not math.isfinite(t0) or t0 <= 0:
        return default_temp
    return t0


def otjig(
    file_name,
    temp_k=0.995,
    min_temperature=0.01,
    max_iterations=200000,
    max_no_improve=25000,
    reheat_no_improve=5000,
    reheat_factor=1.5,
    seed=42,
    log_every=5000,
    initial_temperature=None,
    target_initial_acceptance=0.8,
    calibration_samples=400,
):
    rng = random.Random(seed)

    g = Graph.load_from_stp(file_name)
    cycle = find_initial_cycle_greedy(g)
    if not cycle:
        print("Цикл не найден")
        return None

    current_route = cycle[:]
    current_length = cycle_length(g, current_route)
    if current_length is None:
        print("Стартовый цикл некорректен")
        return None

    best_route = current_route[:]
    best_length = current_length

    if initial_temperature is None:
        initial_temperature = calibrate_initial_temperature(
            g,
            current_route,
            rng,
            samples=calibration_samples,
            target_acceptance=target_initial_acceptance,
            default_temp=100.0,
        )
    temperature = float(initial_temperature)
    if temperature <= min_temperature:
        temperature = min_temperature * MIN_TEMP_MULTIPLIER

    no_improve = 0
    total_accepted = 0
    iterations_done = 0

    for iteration in range(1, max_iterations + 1):
        iterations_done = iteration
        if temperature <= min_temperature:
            break
        if no_improve >= max_no_improve:
            break

        move = propose_move(g, current_route, rng)
        if move is None:
            temperature *= temp_k
            no_improve += 1
            continue

        delta = move["delta"]
        if delta <= 0:
            accept = True
        else:
            accept_prob = math.exp(-delta / temperature)
            accept = rng.random() < accept_prob

        if accept:
            apply_move(current_route, move)
            current_length += delta
            total_accepted += 1

            if current_length < best_length:
                best_length = current_length
                best_route = current_route[:]
                no_improve = 0
            else:
                no_improve += 1
        else:
            no_improve += 1

        if reheat_no_improve > 0 and no_improve > 0 and no_improve % reheat_no_improve == 0:
            temperature = max(
                temperature,
                min(initial_temperature * reheat_factor, initial_temperature * MAX_REHEAT_MULTIPLIER),
            )
            current_route = best_route[:]
            current_length = best_length

        temperature *= temp_k

        if log_every > 0 and iteration % log_every == 0:
            print(
                f"[iter={iteration}] temp={temperature:.5f}, "
                f"current={current_length:.2f}, best={best_length:.2f}, "
                f"accepted={total_accepted}, no_improve={no_improve}"
            )

    best_cycle = best_route + [best_route[0]]
    print(
        f"Done: best={best_length:.2f}, iterations={iterations_done}, "
        f"accepted={total_accepted}, final_temp={temperature:.5f}, seed={seed}"
    )
    return {
        "cycle": best_cycle,
        "length": best_length,
        "iterations": iterations_done,
        "accepted": total_accepted,
        "final_temperature": temperature,
        "seed": seed,
    }


if __name__ == "__main__":
    otjig("berlin52.stp")
