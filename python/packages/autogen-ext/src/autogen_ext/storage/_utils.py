from typing import Any, Dict, List, Optional, Tuple

from ._base import QueryResults


def filter_results_by_distance(results: QueryResults, distance_threshold: float = -1) -> QueryResults:
    """Filters results based on a distance threshold.

    Args:
        results: QueryResults | The query results. List[List[Tuple[Document, float]]]
        distance_threshold: The maximum distance allowed for results.

    Returns:
        QueryResults | A filtered results containing only distances smaller than the threshold.
    """

    if distance_threshold > 0:
        results = [[(key, value) for key, value in data if value < distance_threshold] for data in results]

    return results


def chroma_results_to_query_results(
    data_dict: Dict[str, Optional[List[List[Any]]]], special_key: str = "distances"
) -> List[List[Tuple[Dict[str, Any], float]]]:
    """Converts a dictionary with list-of-list values to a list of tuples.

    Args:
        data_dict: A dictionary where keys map to lists of lists or None.
        special_key: str | The key in the dictionary containing the special values
                     for each tuple.

    Returns:
        List[List[Tuple[Dict[str, Any], float]]] | A list of tuples, where each tuple contains
        a sub-dictionary with some keys from the original dictionary and the value from the
        special_key.

    Example:
        data_dict = {
            "key1s": [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
            "key2s": [["a", "b", "c"], ["c", "d", "e"], ["e", "f", "g"]],
            "key3s": None,
            "key4s": [["x", "y", "z"], ["1", "2", "3"], ["4", "5", "6"]],
            "distances": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]],
        }

        results = [
            [
                ({"key1": 1, "key2": "a", "key4": "x"}, 0.1),
                ({"key1": 2, "key2": "b", "key4": "y"}, 0.2),
                ({"key1": 3, "key2": "c", "key4": "z"}, 0.3),
            ],
            [
                ({"key1": 4, "key2": "c", "key4": "1"}, 0.4),
                ({"key1": 5, "key2": "d", "key4": "2"}, 0.5),
                ({"key1": 6, "key2": "e", "key4": "3"}, 0.6),
            ],
            [
                ({"key1": 7, "key2": "e", "key4": "4"}, 0.7),
                ({"key1": 8, "key2": "f", "key4": "5"}, 0.8),
                ({"key1": 9, "key2": "g", "key4": "6"}, 0.9),
            ],
        ]
    """

    if not data_dict or special_key not in data_dict or not data_dict[special_key]:
        return []

    keys: List[str] = [
        key
        for key in data_dict
        if key != special_key
        and data_dict[key] is not None
        and isinstance(data_dict[key], list)
        and len(data_dict[key]) > 0
        and isinstance(data_dict[key][0], list)
    ]
    result: List[List[Tuple[Dict[str, Any], float]]] = []
    data_special_key = data_dict[special_key]

    assert data_special_key is not None

    for i in range(len(data_special_key)):
        sub_result: List[Tuple[Dict[str, Any], float]] = []
        for j, distance in enumerate(data_special_key[i]):
            sub_dict: Dict[str, Any] = {}
            for key in keys:
                if len(data_dict[key]) > i and len(data_dict[key][i]) > j:
                    sub_dict[key[:-1]] = data_dict[key][i][j]  # remove 's' at the end from key
            sub_result.append((sub_dict, distance))
        result.append(sub_result)

    return result
