import numpy as np
from flaml.automl.utils import len_labels, unique_value_first_index


def test_len_labels():
    assert len_labels([1, 2, 3]) == 3
    assert len_labels([1, 2, 3, 1, 2, 3]) == 3
    assert np.array_equal(len_labels([1, 2, 3], True)[1], [1, 2, 3])
    assert np.array_equal(len_labels([1, 2, 3, 1, 2, 3], True)[1], [1, 2, 3])


def test_unique_value_first_index():
    label_set, first_index = unique_value_first_index([1, 2, 2, 3])
    assert np.array_equal(label_set, np.array([1, 2, 3]))
    assert np.array_equal(first_index, np.array([0, 1, 3]))


if __name__ == "__main__":
    test_len_labels()
    test_unique_value_first_index()
