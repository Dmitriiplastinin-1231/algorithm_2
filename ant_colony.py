import random
from dataclasses import dataclass


@dataclass
class AntColonyResult:
    best_path: list
    best_length: float


class AntColonyTSP:
    MIN_PHEROMONE = 1e-12

    def __init__(
        self,
        graph,
        ants=40,
        alpha=1.0,
        beta=3.0,
        evaporation=0.5,
        q=100.0,
        seed=None,
    ):
        self.graph = graph
        self.ants = max(1, int(ants))
        self.alpha = float(alpha)
        self.beta = float(beta)
        # Ограничиваем испарение в диапазоне [0.0, 0.999], чтобы феромон не обнулялся полностью за шаг.
        self.evaporation = min(max(float(evaporation), 0.0), 0.999)
        self.q = float(q)
        self.random = random.Random(seed)
        self.pheromone = {}
        self._init_pheromone()

    def _init_pheromone(self, value=1.0):
        self.pheromone.clear()
        for u in range(self.graph.num_nodes):
            for v, _ in self.graph.adj[u]:
                if u < v:
                    self.pheromone[(u, v)] = float(value)

    @staticmethod
    def _edge_key(u, v):
        return (u, v) if u < v else (v, u)

    def _choose_next(self, current, unvisited):
        candidates = []
        weights = []

        for nxt, w in self.graph.adj[current]:
            if nxt not in unvisited:
                continue
            edge_key = self._edge_key(current, nxt)
            tau = self.pheromone.get(edge_key, AntColonyTSP.MIN_PHEROMONE) ** self.alpha
            eta = (1.0 / w) ** self.beta if w > 0 else 0.0
            p = tau * eta
            if p > 0:
                candidates.append(nxt)
                weights.append(p)

        if not candidates:
            return None

        total = sum(weights)
        if total <= 0:
            return self.random.choice(candidates)

        r = self.random.uniform(0.0, total)
        acc = 0.0
        for node, w in zip(candidates, weights):
            acc += w
            if acc >= r:
                return node
        return candidates[-1]

    def _build_tour(self, start):
        n = self.graph.num_nodes
        path = [start]
        unvisited = set(range(n))
        unvisited.remove(start)
        current = start

        while unvisited:
            nxt = self._choose_next(current, unvisited)
            if nxt is None:
                return None
            path.append(nxt)
            unvisited.remove(nxt)
            current = nxt

        if not self.graph.has_edge(path[-1], path[0]):
            return None

        cycle = path + [path[0]]
        length = self.graph.path_length(cycle, strict=True)
        if length is None:
            return None
        return cycle, float(length)

    def _evaporate(self):
        k = 1.0 - self.evaporation
        for edge in self.pheromone:
            self.pheromone[edge] = max(AntColonyTSP.MIN_PHEROMONE, self.pheromone[edge] * k)

    def _deposit(self, tour, length):
        if not tour or length <= 0:
            return
        delta = self.q / length
        for i in range(len(tour) - 1):
            edge = self._edge_key(tour[i], tour[i + 1])
            self.pheromone[edge] = self.pheromone.get(edge, AntColonyTSP.MIN_PHEROMONE) + delta

    def solve(self, iterations=200, callback=None, stop_condition=None):
        best_path = None
        best_length = float("inf")

        for iteration in range(1, int(iterations) + 1):
            if stop_condition and stop_condition():
                break

            ant_tours = []
            for _ in range(self.ants):
                start = self.random.randrange(self.graph.num_nodes)
                tour_data = self._build_tour(start)
                if tour_data is not None:
                    ant_tours.append(tour_data)

            self._evaporate()

            iteration_best = None
            iteration_best_len = float("inf")
            for tour, length in ant_tours:
                self._deposit(tour, length)
                if length < iteration_best_len:
                    iteration_best_len = length
                    iteration_best = tour

            prev_best = best_path[:] if best_path else None
            improved = False
            if iteration_best is not None and iteration_best_len < best_length:
                best_path = iteration_best[:]
                best_length = iteration_best_len
                improved = True
                self._deposit(best_path, best_length)

            if callback:
                callback(
                    iteration=iteration,
                    best_path=best_path[:] if best_path else None,
                    best_length=best_length,
                    improved=improved,
                    previous_best=prev_best,
                )

        if best_path is None:
            return None
        return AntColonyResult(best_path=best_path, best_length=best_length)
