"""Solve a non-symmetric TSP problem.

Triangular inequality is not required in this problem.
"""
import math
import pdb
import random
import sys
from itertools import combinations, permutations


def solve_tsp(dists: dict) -> float:
    """Solve the TSP problem

    Args:
        dists (dict): the distance matrix between each nodes. Each item in the
            dict is a pair (node A, node B) to the distance from A to B.

    Returns:
        float: the optimal cost
    """
    # Get the unique nodes from the distance matrix
    nodes = set()
    for pair in dists.keys():
        nodes.add(pair[0])
        nodes.add(pair[1])

    # Generate all possible routes (permutations of nodes)
    routes = permutations(nodes)

    # Initialize the optimal cost as infinite
    optimal_cost = float("inf")
    optimal_route = None

    # Iterate through all possible routes
    for route in routes:
        cost = 0
        # Calculate the cost of the current route
        for i in range(len(route)):
            current_node = route[i]
            next_node = route[(i + 1) % len(route)]
            cost += dists[(current_node, next_node)]

        # Update the optimal cost if the current cost is smaller
        if cost < optimal_cost:
            optimal_cost = cost
            optimal_route = route

    print("Cost:", optimal_cost, "with route", optimal_route)
    return optimal_cost


def tsp_data(n: int, seed: int = 2022) -> dict:
    """Generate some sample data for the non-symmetric TSP problem.

    Args:
        n (int): number of nodes in the problem
        seed (int): the random seed.

    Returns:
        dict: the pairwise distance matrix.
    """
    # Initialize the random seed
    random.seed(seed)

    # Initialize the distance matrix
    dist_matrix = {}

    # Generate distances for each pair of nodes
    for i in range(n):
        for j in range(n):
            if i != j:
                # Generate a random distance between nodes i and j
                distance = round(random.uniform(1, 100), 2)
                dist_matrix[(i, j)] = distance

    return dist_matrix
