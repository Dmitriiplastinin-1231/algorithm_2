import queue
import random
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ant_colony import AntColonyTSP
from graphClass import Graph


def path_edges(path):
    if not path or len(path) < 2:
        return []
    return [(path[i], path[i + 1]) for i in range(len(path) - 1)]


def undirected_edges(path):
    return {tuple(sorted((u, v))) for u, v in path_edges(path)}


class AntColonyGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Муравьиный алгоритм для задачи коммивояжёра")
        self.root.geometry("1300x820")

        self.graph = None
        self.graph_nx = None
        self.pos = None
        self.result_path = None
        self.result_length = None

        self.events = queue.Queue()
        self.stop_event = threading.Event()
        self.worker = None

        self._build_ui()
        self.root.after(100, self._poll_events)

    def _build_ui(self):
        control = ttk.Frame(self.root, padding=10)
        control.pack(side=tk.TOP, fill=tk.X)

        self.file_var = tk.StringVar(value="")
        self.iter_var = tk.StringVar(value="200")
        self.ants_var = tk.StringVar(value="50")
        self.alpha_var = tk.StringVar(value="1.0")
        self.beta_var = tk.StringVar(value="3.0")
        self.evap_var = tk.StringVar(value="0.45")
        self.q_var = tk.StringVar(value="120.0")
        self.seed_var = tk.StringVar(value="42")

        ttk.Label(control, text="Файл графа (.stp):").grid(row=0, column=0, sticky="w")
        ttk.Entry(control, textvariable=self.file_var, width=45).grid(row=0, column=1, sticky="we", padx=5)
        ttk.Button(control, text="Выбрать", command=self.choose_file).grid(row=0, column=2, padx=5)
        ttk.Button(control, text="Загрузить", command=self.load_graph).grid(row=0, column=3, padx=5)

        ttk.Label(control, text="Итераций").grid(row=1, column=0, sticky="w")
        ttk.Entry(control, textvariable=self.iter_var, width=8).grid(row=1, column=1, sticky="w")

        ttk.Label(control, text="Муравьёв").grid(row=1, column=1, sticky="e", padx=(0, 90))
        ttk.Entry(control, textvariable=self.ants_var, width=8).grid(row=1, column=1, sticky="e", padx=(0, 10))

        ttk.Label(control, text="alpha").grid(row=1, column=2, sticky="w")
        ttk.Entry(control, textvariable=self.alpha_var, width=8).grid(row=1, column=2, sticky="e")

        ttk.Label(control, text="beta").grid(row=1, column=3, sticky="w")
        ttk.Entry(control, textvariable=self.beta_var, width=8).grid(row=1, column=3, sticky="e")

        ttk.Label(control, text="evap").grid(row=1, column=4, sticky="w")
        ttk.Entry(control, textvariable=self.evap_var, width=8).grid(row=1, column=4, sticky="e")

        ttk.Label(control, text="Q").grid(row=1, column=5, sticky="w")
        ttk.Entry(control, textvariable=self.q_var, width=8).grid(row=1, column=5, sticky="e")

        ttk.Label(control, text="seed").grid(row=1, column=6, sticky="w")
        ttk.Entry(control, textvariable=self.seed_var, width=8).grid(row=1, column=6, sticky="e")

        self.start_btn = ttk.Button(control, text="Запустить муравьиный алгоритм", command=self.run_solver)
        self.start_btn.grid(row=2, column=0, columnspan=3, sticky="we", pady=(8, 0))

        self.stop_btn = ttk.Button(control, text="Стоп", command=self.stop_solver, state="disabled")
        self.stop_btn.grid(row=2, column=3, sticky="we", pady=(8, 0), padx=5)

        self.status_var = tk.StringVar(value="Загрузите граф")
        ttk.Label(control, textvariable=self.status_var).grid(row=2, column=4, columnspan=3, sticky="w", padx=5)

        control.columnconfigure(1, weight=1)

        self.fig, self.ax = plt.subplots(figsize=(12, 7))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def choose_file(self):
        path = filedialog.askopenfilename(
            title="Выберите STP-файл",
            filetypes=[("STP files", "*.stp"), ("All files", "*.*")],
        )
        if path:
            self.file_var.set(path)

    def load_graph(self):
        file_name = self.file_var.get().strip()
        if not file_name:
            messagebox.showerror("Ошибка", "Укажите путь к .stp файлу.")
            return
        try:
            self.graph = Graph.load_from_stp(file_name)
            self._build_visual_graph()
            self.result_path = None
            self.result_length = None
            self.status_var.set(f"Граф загружен: {self.graph.num_nodes} вершин")
            self._draw_state()
        except Exception as exc:
            messagebox.showerror("Ошибка загрузки", str(exc))

    def _build_visual_graph(self, max_edges=5000, seed=42):
        G = nx.Graph()
        for u in range(self.graph.num_nodes):
            G.add_node(u)
        for u in range(self.graph.num_nodes):
            for v, w in self.graph.adj[u]:
                if u < v:
                    G.add_edge(u, v, weight=w)

        if G.number_of_edges() > max_edges:
            rnd = random.Random(seed)
            sampled_edges = rnd.sample(list(G.edges()), max_edges)
            H = nx.Graph()
            H.add_nodes_from(G.nodes())
            H.add_edges_from(sampled_edges)
            self.graph_nx = H
        else:
            self.graph_nx = G

        n = self.graph_nx.number_of_nodes()
        if n > 300:
            self.pos = nx.circular_layout(self.graph_nx)
        elif n > 120:
            self.pos = nx.spring_layout(self.graph_nx, seed=42, k=0.15, iterations=35)
        else:
            self.pos = nx.spring_layout(self.graph_nx, seed=42)

    def _draw_state(self, best_path=None, added=None, removed=None, iteration=None, best_length=None):
        self.ax.clear()
        if self.graph_nx is None:
            self.ax.set_title("Граф не загружен")
            self.ax.axis("off")
            self.canvas.draw_idle()
            return

        nx.draw_networkx_nodes(
            self.graph_nx,
            self.pos,
            ax=self.ax,
            node_size=15 if self.graph.num_nodes > 150 else 40,
            node_color="lightblue",
            alpha=0.9,
        )
        nx.draw_networkx_edges(
            self.graph_nx,
            self.pos,
            ax=self.ax,
            edge_color="gray",
            alpha=0.25,
            width=0.6,
        )

        if best_path:
            nx.draw_networkx_edges(
                self.graph_nx,
                self.pos,
                ax=self.ax,
                edgelist=path_edges(best_path),
                edge_color="dodgerblue",
                width=2.0,
                alpha=0.95,
            )

        if removed:
            nx.draw_networkx_edges(
                self.graph_nx,
                self.pos,
                ax=self.ax,
                edgelist=list(removed),
                edge_color="red",
                width=3.0,
                style="dashed",
                alpha=0.9,
            )

        if added:
            nx.draw_networkx_edges(
                self.graph_nx,
                self.pos,
                ax=self.ax,
                edgelist=list(added),
                edge_color="limegreen",
                width=3.0,
                alpha=0.95,
            )

        title = "Муравьиный алгоритм: визуализация"
        if iteration is not None:
            title += f" | итерация {iteration}"
        if best_length is not None and best_length != float("inf"):
            title += f" | лучшая длина {best_length:.2f}"
        self.ax.set_title(title)
        self.ax.axis("off")
        self.canvas.draw_idle()

    def run_solver(self):
        if self.worker and self.worker.is_alive():
            return
        if self.graph is None:
            self.load_graph()
            if self.graph is None:
                return

        try:
            iterations = int(self.iter_var.get())
            ants = int(self.ants_var.get())
            alpha = float(self.alpha_var.get())
            beta = float(self.beta_var.get())
            evaporation = float(self.evap_var.get())
            q = float(self.q_var.get())
            seed_text = self.seed_var.get().strip()
            seed = int(seed_text) if seed_text else None
        except ValueError:
            messagebox.showerror("Ошибка", "Проверьте числовые параметры.")
            return

        self.stop_event.clear()
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_var.set("Расчёт запущен...")

        def worker():
            start_time = time.time()
            solver = AntColonyTSP(
                self.graph,
                ants=ants,
                alpha=alpha,
                beta=beta,
                evaporation=evaporation,
                q=q,
                seed=seed,
            )

            def callback(iteration, best_path, best_length, improved, previous_best):
                if improved and best_path:
                    prev_set = undirected_edges(previous_best) if previous_best else set()
                    new_set = undirected_edges(best_path)
                    added = new_set - prev_set
                    removed = prev_set - new_set
                else:
                    added = set()
                    removed = set()

                self.events.put(
                    (
                        "progress",
                        iteration,
                        best_path,
                        best_length,
                        added,
                        removed,
                    )
                )

            result = solver.solve(
                iterations=iterations,
                callback=callback,
                stop_condition=lambda: self.stop_event.is_set(),
            )
            elapsed = time.time() - start_time
            self.events.put(("done", result, elapsed))

        self.worker = threading.Thread(target=worker, daemon=True)
        self.worker.start()

    def stop_solver(self):
        self.stop_event.set()
        self.status_var.set("Остановка...")

    def _poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "progress":
                    _, iteration, best_path, best_length, added, removed = event
                    self.result_path = best_path
                    self.result_length = best_length
                    self._draw_state(
                        best_path=best_path,
                        added=added,
                        removed=removed,
                        iteration=iteration,
                        best_length=best_length,
                    )
                elif kind == "done":
                    _, result, elapsed = event
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                    if result is None:
                        self.status_var.set(f"Завершено за {elapsed:.2f} c. Цикл не найден.")
                    else:
                        self.result_path = result.best_path
                        self.result_length = result.best_length
                        self.status_var.set(
                            f"Готово за {elapsed:.2f} c. Лучшая длина: {result.best_length:.2f}"
                        )
                        self._draw_state(
                            best_path=result.best_path,
                            iteration="final",
                            best_length=result.best_length,
                        )
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._poll_events)


def main():
    root = tk.Tk()
    AntColonyGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
