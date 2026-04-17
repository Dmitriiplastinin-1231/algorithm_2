import sys
from collections import deque
import random
import time


class Graph:
    def __init__(self, num_nodes):
        self.num_nodes = num_nodes
        self.adj = [[] for _ in range(num_nodes)]
        # Быстрый доступ к весам рёбер: weights[u][v] -> weight (O(1))
        self.weights = [dict() for _ in range(num_nodes)]

    def add_edge(self, u, v, weight):
        if u < 0 or v < 0:
            raise ValueError(f"Номер вершины должен быть от 0 до {self.num_nodes-1}")
        self.adj[u].append((v, weight))
        self.adj[v].append((u, weight))
        self.weights[u][v] = weight
        self.weights[v][u] = weight

    def get_weight(self, u, v):
        return self.weights[u].get(v)

    def neighbor(self, u):
        return list(self.weights[u].keys())

    @staticmethod
    def load_from_stp(filename):
        nodes = 0
        edges = []
        in_graph = False

        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('Section Graph'):
                    in_graph = True
                    continue
                if in_graph and line.startswith('End'):
                    break
                if in_graph:
                    if line.startswith('Nodes'):
                        nodes = int(line.split()[1])
                    elif line.startswith('Edges'):
                        pass
                    elif line.startswith('E'):
                        parts = line.split()
                        if len(parts) >= 4:
                            u = int(parts[1]) - 1   # сдвиг к 0-индексации
                            v = int(parts[2]) - 1
                            w = float(parts[3])
                            edges.append((u, v, w))

        # Создаём граф
        g = Graph(nodes)
        for u, v, w in edges:
            g.add_edge(u, v, w)
        return g


    def display(self, path=None, max_nodes=500, max_edges=5000, with_labels=False, 
            with_weights=False, figsize=(12, 8), seed=42):
        try:
            import matplotlib.pyplot as plt
            import networkx as nx
        except ImportError:
            print("Для визуализации нужны matplotlib и networkx.")
            return
    
        if self.num_nodes == 0:
            print("Граф пуст, нечего отображать.")
            return

        # Создаём граф networkx
        G_nx = nx.Graph()

        n = self.num_nodes
        m = sum(len(lst) for lst in self.adj) // 2

        # Если передан путь, убедимся, что все его вершины попадут в отображение
        forced_nodes = set(path) if path else set()

        # Сэмплирование вершин
        if n > max_nodes:
            random.seed(seed)
            # Если есть путь, добавим его вершины принудительно
            base_sample = set(random.sample(range(n), max_nodes - len(forced_nodes)))
            sampled_nodes = sorted(forced_nodes.union(base_sample))
            if len(sampled_nodes) > max_nodes:
                # Если принудительных вершин слишком много, просто берём их
                sampled_nodes = sorted(forced_nodes)
                print(f"Внимание: путь содержит {len(forced_nodes)} вершин, max_nodes={max_nodes}. Отображаются только вершины пути.")

            # Строим подграф
            sub_adj = {node: [] for node in sampled_nodes}
            for node in sampled_nodes:
                for neighbor, w in self.adj[node]:
                    if neighbor in sub_adj:
                        sub_adj[node].append((neighbor, w))
            for node in sampled_nodes:
                G_nx.add_node(node)
            for node in sampled_nodes:
                for neighbor, w in sub_adj[node]:
                    if node < neighbor:
                        G_nx.add_edge(node, neighbor, weight=w)
            print(f"Отображается подграф: {len(sampled_nodes)} вершин из {n}, "
                  f"{G_nx.number_of_edges()} рёбер из {m}")
        else:
            for u in range(self.num_nodes):
                G_nx.add_node(u)
            for u in range(self.num_nodes):
                for v, w in self.adj[u]:
                    if u < v:
                        G_nx.add_edge(u, v, weight=w)
            print(f"Отображается полный граф: {n} вершин, {m} рёбер")

        # Сэмплирование рёбер (если нужно)
        if G_nx.number_of_edges() > max_edges:
            edges = list(G_nx.edges())
            random.seed(seed)
            sampled_edges = random.sample(edges, max_edges)
            H = nx.Graph()
            H.add_nodes_from(G_nx.nodes())
            for u, v in sampled_edges:
                H.add_edge(u, v, weight=G_nx[u][v]['weight'])
            G_nx = H
            print(f"Сэмплировано рёбер до {max_edges} (было {len(edges)})")

        # Проверка пути
        path_edges = []
        if path:
            # Проверяем, что все вершины пути существуют в отображаемом графе
            missing = [v for v in path if v not in G_nx.nodes]
            if missing:
                print(f"Предупреждение: вершины {missing} отсутствуют в отображаемом подграфе. Путь не будет нарисован.")
                path_edges = []
            else:
                # Формируем рёбра пути
                for i in range(len(path)-1):
                    u, v = path[i], path[i+1]
                    if G_nx.has_edge(u, v):
                        path_edges.append((u, v))
                    else:
                        print(f"Предупреждение: ребро ({u}, {v}) отсутствует в графе. Путь обрывается.")
                        break

        # Компоновка
        if len(G_nx.nodes) < 200:
            pos = nx.spring_layout(G_nx, seed=seed, k=0.3)
        else:
            pos = nx.spring_layout(G_nx, seed=seed, k=0.1, iterations=20)

        plt.figure(figsize=figsize)

        # Рисуем все вершины
        nx.draw_networkx_nodes(G_nx, pos, node_size=50, node_color='lightblue', alpha=0.8)

        # Рисуем все рёбра (серые, тонкие)
        nx.draw_networkx_edges(G_nx, pos, alpha=0.4, edge_color='gray', width=0.8)

        # Рисуем рёбра пути (красные, жирные), если они есть
        if path_edges:
            nx.draw_networkx_edges(G_nx, pos, edgelist=path_edges, 
                                   edge_color='red', width=3, alpha=0.9)

        # Подписи вершин
        if with_labels and len(G_nx.nodes) <= 100:
            nx.draw_networkx_labels(G_nx, pos, font_size=8)

        # Подписи весов
        if with_weights and len(G_nx.edges) <= 200:
            edge_labels = {(u, v): f"{G_nx[u][v]['weight']:.1f}" for u, v in G_nx.edges}
            nx.draw_networkx_edge_labels(G_nx, pos, edge_labels=edge_labels, font_size=6)

        plt.title(f"Визуализация графа (вершин: {G_nx.number_of_nodes()}, рёбер: {G_nx.number_of_edges()})")
        plt.axis('off')
        plt.tight_layout()
        plt.show()

    def find_hamiltonian_cycle(self, max_attempts=100, timeout=5, method='random', start_vertex=0):
        if self.num_nodes == 0:
            return None
        if self.num_nodes == 1:
            # петля не поддерживается, вернём одну вершину
            return [0] if self.has_edge(0, 0) else None
        
        # Для метода 'nearest' делаем одну попытку
        if method == 'nearest':
            cycle = self._nearest_neighbor_cycle(start_vertex)
            if cycle and self.has_edge(cycle[-1], cycle[0]):
                return cycle
            return None
        
        # Для метода 'random' – несколько попыток
        start_time = time.time()
        for attempt in range(max_attempts):
            if time.time() - start_time > timeout:
                print(f"Время вышло ({timeout} сек), остановка после {attempt} попыток")
                break
            cycle = self._random_cycle(start_vertex)
            if cycle and self.has_edge(cycle[-1], cycle[0]):
                return cycle
        
        print(f"Гамильтонов цикл не найден за {max_attempts} попыток / {timeout} сек")
        return None
    
    def _random_cycle(self, start):
        """
        Строит путь, случайно выбирая следующую непосещённую вершину.
        """
        n = self.num_nodes
        visited = [False] * n
        path = [start]
        visited[start] = True
        current = start
        
        for _ in range(n - 1):
            # Получаем список непосещённых соседей
            neighbors = [v for v, _ in self.adj[current] if not visited[v]]
            if not neighbors:
                return None  # тупик
            # Случайный выбор
            next_vertex = random.choice(neighbors)
            path.append(next_vertex)
            visited[next_vertex] = True
            current = next_vertex
        
        # Проверяем, есть ли ребро из последней вершины в стартовую
        if self.has_edge(path[-1], path[0]):
            return path
        return None
    
    def _nearest_neighbor_cycle(self, start):
        """
        Жадный алгоритм: идём в ближайшего (по весу) непосещённого соседа.
        """
        n = self.num_nodes
        visited = [False] * n
        path = [start]
        visited[start] = True
        current = start
        
        for _ in range(n - 1):
            # Находим непосещённого соседа с минимальным весом
            best = None
            best_weight = float('inf')
            for v, w in self.adj[current]:
                if not visited[v] and w < best_weight:
                    best_weight = w
                    best = v
            if best is None:
                return None
            path.append(best)
            visited[best] = True
            current = best
        
        if self.has_edge(path[-1], path[0]):
            return path
        return None
    
    def has_edge(self, u, v):
        """
        Проверяет, существует ли ребро (u, v).
        """
        return v in self.weights[u]
    def verify_path(self, path):
        if not path or len(path) < 2:
            return False, "Путь должен содержать хотя бы две вершины."

        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            if not self.has_edge(u, v):
                return False, f"Ребро ({u}, {v}) отсутствует в графе."
        return True, "Путь существует."

    def verify_cycle(self, cycle):
        if not cycle:
            return False, "Цикл пуст."
        n = len(cycle)
        if n != self.num_nodes:
            return False, f"Цикл содержит {n} вершин, а в графе {self.num_nodes}."
        # Проверяем уникальность (кроме последней, которая должна совпасть с первой для цикла)
        if cycle[0] != cycle[-1]:
            # Если пользователь не повторил первую вершину в конце, проверяем все вершины на уникальность
            if len(set(cycle)) != n:
                return False, "В цикле есть повторяющиеся вершины (без учёта замыкания)."
        else:
            # Если первая и последняя совпадают, то уникальных вершин должно быть n-1
            if len(set(cycle)) != n - 1:
                return False, "Внутри цикла есть повторяющиеся вершины."
        # Проверяем рёбра
        for i in range(n - 1):
            u, v = cycle[i], cycle[i+1]
            if not self.has_edge(u, v):
                return False, f"Ребро ({u}, {v}) отсутствует в графе."
        # Проверяем замыкание (последняя -> первая)
        if not self.has_edge(cycle[-1], cycle[0]):
            return False, f"Замыкающее ребро ({cycle[-1]}, {cycle[0]}) отсутствует."
        return True, "Цикл корректен."
    def path_length(self, path, strict=True):
        """
        Вычисляет суммарный вес пути по списку вершин.
        
        Параметры:
        - path: список вершин [v1, v2, ..., vk]
        - strict: если True, то при отсутствии любого ребра возвращает None;
                если False, то пропускает отсутствующие рёбра и суммирует только существующие.
        
        Возвращает:
        - float (суммарный вес) или None, если есть пропущенные рёбра и strict=True.
        """
        if not path or len(path) < 2:
            return 0.0 if not strict else None
        
        total = 0.0
        missing = []
        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            w = self.get_weight(u, v)
            if w is None:
                if strict:
                    return None
                else:
                    missing.append((u, v))
            else:
                total += w
        if missing and not strict:
            print(f"Предупреждение: пропущены рёбра {missing}")
        return total


