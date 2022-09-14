try:
    from ray import __version__ as ray_version

    assert ray_version >= "1.10.0"
    from ray.tune import (
        uniform,
        quniform,
        randint,
        qrandint,
        randn,
        qrandn,
        loguniform,
        qloguniform,
        lograndint,
        qlograndint,
    )

    if ray_version.startswith("1."):
        from ray.tune import sample
    else:
        from ray.tune.search import sample
except (ImportError, AssertionError):
    from .sample import (
        uniform,
        quniform,
        randint,
        qrandint,
        randn,
        qrandn,
        loguniform,
        qloguniform,
        lograndint,
        qlograndint,
    )
    from . import sample
from .tune import run, report, INCUMBENT_RESULT
from .sample import polynomial_expansion_set
from .sample import PolynomialExpansionSet, Categorical, Float
from .trial import Trial
from .utils import choice
