import json
from typing import Protocol, List, Any
import pkg_resources

import matplotlib.pyplot as plt
import networkx as nx

from .profiler import MessageProfile


class ProfileVisualizer(Protocol):

    def visualize(self, profiles: List[MessageProfile], filename: str) -> bool:
        pass


class Node:
    def __init__(self, name):
        self.name = name
        self.children = []


class DAG:
    def __init__(self):
        self.nodes = {}

    def add_edge(self, source_name, dest_name):
        if source_name not in self.nodes:
            self.nodes[source_name] = Node(source_name)
        if dest_name not in self.nodes:
            self.nodes[dest_name] = Node(dest_name)
        self.nodes[source_name].children.append(self.nodes[dest_name])

    def to_json(self):
        graph = {"nodes": [], "links": []}
        node_index = {}

        for node_name, node in self.nodes.items():
            graph["nodes"].append({"name": node_name})
            node_index[node_name] = len(graph["nodes"]) - 1

        for node_name, node in self.nodes.items():
            for child in node.children:
                graph["links"].append({"source": node_index[node_name], "target": node_index[child.name]})

        return graph


class DAGVisualizer:

    def visualize(self, profiles: List[MessageProfile], filename: str) -> bool:

        dag = self._create_dag(profiles)
        self._create_d3_figure(dag, filename)

        return True

    def _create_dag(self, profiles: List[MessageProfile]) -> DAG:
        """Create a directed graph of the states that apply to a message."""

        dag = DAG()

        num_messages = len(profiles)
        for i in range(num_messages - 1):
            current = profiles[i]
            next = profiles[i + 1]
            sorted_current_states = sorted([s.name for s in current.states])
            sorted_next_states = sorted([s.name for s in next.states])
            current_states = f"[{i}]:\n" + "\n".join(sorted_current_states)
            next_states = f"[{i+1}]:\n" + "\n".join(sorted_next_states)
            dag.add_edge(current_states, next_states)

        return dag

    def _create_figure(self, dag: DAG, filename: str) -> None:

        # Create a directed graph
        G = nx.DiGraph()

        # Add nodes and edges to the graph
        for node in dag.nodes.values():
            G.add_node(node.name)
            for child in node.children:
                G.add_edge(node.name, child.name)

        pos = nx.spiral_layout(G)

        nx.draw(G, pos, with_labels=True, node_size=100, font_size=4)

        if filename is None:
            plt.show()
        else:
            # Save the figure to a file
            plt.savefig(filename, dpi=300)

    def _create_d3_figure(self, dag: DAG, filename: str) -> None:

        # save the dag to a json file
        # with open("dag.json", "w") as f:
        #     f.write(json.dumps(dag.to_json(), indent=2))

        # use the contents of index.html to create a d3 figure
        # with the dag.json file and launch a simpler server
        # to visualize the figure
        index_html_path = pkg_resources.resource_filename(__name__, "viz/d3_dag.html")

        dag_json = json.dumps(dag.to_json())

        # save this file to filename
        with open(filename, "w") as f:
            with open(index_html_path, "r") as index_html:
                html_content = index_html.read()
                # Replace the placeholder with the actual dag_json data
                html_content = html_content.replace("__DAG_DATA__", dag_json)
                f.write(html_content)

        print(f"Visualization saved to {filename}")
