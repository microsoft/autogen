from typing import Optional, Union, Tuple
import numpy as np


def len_labels(y: np.ndarray, return_labels=False) -> Union[int, Optional[np.ndarray]]:
    """Get the number of unique labels in y. The non-spark version of
    flaml.automl.spark.utils.len_labels"""
    labels = np.unique(y)
    if return_labels:
        return len(labels), labels
    return len(labels)


def unique_value_first_index(y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Get the unique values and indices of a pandas series or numpy array.
    The non-spark version of flaml.automl.spark.utils.unique_value_first_index"""
    label_set, first_index = np.unique(y, return_index=True)
    return label_set, first_index
