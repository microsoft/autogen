from .tsp import tsp_data


def change_dist(dist: dict, i: int, j: int, new_cost: float) -> float:
    """Change the distance between two points.

    Args:
        dist (dict): distance matrix, where the key is a pair and value is
            the cost (aka, distance).
        i (int): the source node
        j (int): the destination node
        new_cost (float): the new cost for the distance

    Returns:
        float: the previous cost
    """
    prev_cost = dist[i, j]
    dist[i, j] = new_cost
    return prev_cost


def compare_costs(prev_cost, new_cost) -> float:
    """Compare the previous cost and the new cost.

    Args:
        prev_cost (float): the previous cost
        new_cost (float): the updated cost

    Returns:
        float: the ratio between these two costs
    """
    return (new_cost - prev_cost) / prev_cost


dists = tsp_data(5, seed=1)
