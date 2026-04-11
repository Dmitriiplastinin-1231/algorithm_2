#!/usr/bin/env python3
"""
Viewer for STP graph files (SteinLib / TSP-like format).
Parses a file with structure:
    33d32945 STP File, STP Format Version  1.00
    Section Comment
    ...
    Section Graph
    Nodes N
    Edges M
    E u v w
    ...
    End
Prints graph statistics and optionally visualizes a subgraph.
"""

import sys
import networkx as nx
import matplotlib.pyplot as plt

def parse_stp_graph(filename):
    """Parse the Graph section of an STP file and return a networkx Graph."""
    G = nx.Graph()
    in_graph = False
    nodes_expected = None
    edges_expected = None
    nodes_found = 0
    edges_found = 0

    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Detect start of Graph section
            if line.startswith('Section Graph'):
                in_graph = True
                continue

            # Detect end of Graph section
            if in_graph and line.startswith('End'):
                break

            if in_graph:
                # Read number of nodes
                if line.startswith('Nodes'):
                    try:
                        nodes_expected = int(line.split()[1])
                    except:
                        pass
                # Read number of edges
                elif line.startswith('Edges'):
                    try:
                        edges_expected = int(line.split()[1])
                    except:
                        pass
                # Edge lines: E u v w
                elif line.startswith('E'):
                    parts = line.split()
                    if len(parts) >= 4:
                        try:
                            u = int(parts[1])
                            v = int(parts[2])
                            w = float(parts[3])
                            G.add_edge(u, v, weight=w)
                            edges_found += 1
                        except ValueError:
                            print(f"Warning: could not parse edge line: {line}")
                # Ignore other lines (e.g., Coord, etc.)

    # After parsing, set node count if not all nodes appear in edges
    if nodes_expected is not None:
        # Ensure all nodes up to nodes_expected exist (even isolated)
        for i in range(1, nodes_expected + 1):
            if i not in G:
                G.add_node(i)
        nodes_found = G.number_of_nodes()
    else:
        nodes_found = G.number_of_nodes()

    print(f"Parsed graph: {nodes_found} nodes, {edges_found} edges")
    if nodes_expected is not None and nodes_found != nodes_expected:
        print(f"Warning: expected {nodes_expected} nodes, got {nodes_found}")
    if edges_expected is not None and edges_found != edges_expected:
        print(f"Warning: expected {edges_expected} edges, got {edges_found}")

    return G

def print_stats(G):
    """Print basic statistics of the graph."""
    print("\nGraph Statistics:")
    print(f"  Number of nodes: {G.number_of_nodes()}")
    print(f"  Number of edges: {G.number_of_edges()}")
    if G.number_of_nodes() > 0:
        degrees = [d for _, d in G.degree()]
        print(f"  Degree: min={min(degrees)}, max={max(degrees)}, avg={sum(degrees)/G.number_of_nodes():.2f}")
    if G.number_of_edges() > 0:
        weights = [d['weight'] for _, _, d in G.edges(data=True)]
        print(f"  Edge weights: min={min(weights):.2f}, max={max(weights):.2f}, avg={sum(weights)/len(weights):.2f}")

def visualize_graph(G, max_nodes=500, sample_edges=5000):
    """
    Visualize a subset of the graph to avoid overcrowding.
    - If number of nodes > max_nodes, take a random sample.
    - If number of edges > sample_edges, only show a random sample.
    """
    n = G.number_of_nodes()
    m = G.number_of_edges()

    if n > max_nodes or m > sample_edges:
        print(f"\nGraph is large ({n} nodes, {m} edges). Sampling for visualization.")
        # Sample nodes
        sampled_nodes = set(list(G.nodes())[:max_nodes]) if n > max_nodes else set(G.nodes())
        H = G.subgraph(sampled_nodes).copy()
        # Sample edges if still too many
        if H.number_of_edges() > sample_edges:
            import random
            edges = list(H.edges())
            sampled_edges = random.sample(edges, sample_edges)
            H = nx.Graph()
            H.add_nodes_from(sampled_nodes)
            H.add_edges_from(sampled_edges)
            for u,v in sampled_edges:
                H[u][v]['weight'] = G[u][v]['weight']
        print(f"  Visualizing subgraph with {H.number_of_nodes()} nodes, {H.number_of_edges()} edges")
        G = H

    # Choose layout
    if G.number_of_nodes() < 200:
        pos = nx.spring_layout(G, seed=42)
    else:
        pos = nx.spring_layout(G, k=0.1, iterations=20, seed=42)

    plt.figure(figsize=(12, 8))
    nx.draw_networkx_nodes(G, pos, node_size=30, node_color='lightblue')
    nx.draw_networkx_edges(G, pos, alpha=0.5, edge_color='gray')
    # Optionally add node labels for small graphs
    if G.number_of_nodes() <= 100:
        nx.draw_networkx_labels(G, pos, font_size=8)
    plt.title("STP Graph Visualization")
    plt.axis('off')
    plt.tight_layout()
    plt.show()

def main():
    if len(sys.argv) != 2:
        print("Usage: python view_stp_graph.py <file.stp>")
        sys.exit(1)

    filename = sys.argv[1]
    try:
        G = parse_stp_graph(filename)
        print_stats(G)

        # Ask user if they want to visualize
        answer = input("\nVisualize graph? (y/n): ").strip().lower()
        if answer == 'y':
            visualize_graph(G)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
