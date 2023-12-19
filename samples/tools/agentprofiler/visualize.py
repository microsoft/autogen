import os
import json
import matplotlib.pyplot as plt
import networkx as nx


def draw_profiler_graph(assistant_msgs, title="", output_dir="", filename=""):
    state_transitions = []
    previous_annotations = {"START"}
    for msg in assistant_msgs:
        annotations = msg["codes"]
        # print(annotation), print(type(annotation))
        # annotation = annotation.replace("'", "")  # remove '
        # annotations = set(annotation.split(","))  # split by , and convert to set
        # annotations = set([ann.strip() for ann in annotations])  # remove whitespace
        for start_ann in previous_annotations:
            for ann in annotations:
                state_transitions.append((start_ann, ann))
        previous_annotations = annotations

    G = nx.DiGraph()

    # Add nodes and edges to the graph
    for start, end in state_transitions:
        if G.has_edge(start, end):
            G[start][end]["weight"] += 1
        else:
            G.add_edge(start, end, weight=1)

    # Set node positions
    pos = nx.spring_layout(G, seed=42)

    # Get the number of incoming edges for each node
    incoming_edges = {node: 0 for node in G.nodes()}
    for _, end in state_transitions:
        incoming_edges[end] += 1

    # Calculate the node sizes based on the number of incoming edges
    node_sizes = [incoming_edges[node] * 200 for node in G.nodes()]

    # Draw the graph
    plt.figure(figsize=(10, 8))
    plt.title(f"{title}", fontsize=20)
    plt.axis("off")
    node_colors = [incoming_edges[node] for node in G.nodes()]

    nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color=node_colors, cmap=plt.cm.Reds, edgecolors="black")

    nx.draw_networkx_labels(G, pos=pos, labels={node: node for node in G.nodes()}, font_size=12, font_color="black")
    nx.draw_networkx_edges(
        G, pos, edge_color="#A9A9A9", width=[G[u][v]["weight"] for u, v in G.edges()], arrows=True, arrowsize=20
    )

    # Add edge labels
    edge_labels = {(u, v): G[u][v]["weight"] for u, v in G.edges()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=12, font_color="#696969")

    # Save the graph
    if output_dir:
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, filename), bbox_inches="tight")
    else:
        plt.figure(figsize=(10, 8))
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    annotated_chat_history = json.load(open("sample_data/chat_history_annotated.json"))
    draw_profiler_graph(
        annotated_chat_history, title="ArXiv Search w/ GPT-4", output_dir="sample_data", filename="profiler_graph.png"
    )
