from typing import Sequence

try:
    from ray import __version__ as ray_version

    assert ray_version >= "1.10.0"
    if ray_version.startswith("1."):
        from ray.tune import sample
    else:
        from ray.tune.search import sample
except (ImportError, AssertionError):
    from . import sample


def choice(categories: Sequence, order=None):
    """Sample a categorical value.
    Sampling from ``tune.choice([1, 2])`` is equivalent to sampling from
    ``np.random.choice([1, 2])``

    Args:
        categories (Sequence): Sequence of categories to sample from.
        order (bool): Whether the categories have an order. If None, will be decided autoamtically:
            Numerical categories have an order, while string categories do not.
    """
    domain = sample.Categorical(categories).uniform()
    domain.ordered = order if order is not None else all(isinstance(x, (int, float)) for x in categories)
    return domain
