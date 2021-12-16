try:
    from ray import __version__ as ray_version

    assert ray_version >= "1.0.0"
    from ray.tune import (
        uniform,
        quniform,
        choice,
        randint,
        qrandint,
        randn,
        qrandn,
        loguniform,
        qloguniform,
        lograndint,
        qlograndint,
    )
except (ImportError, AssertionError):
    from .sample import (
        uniform,
        quniform,
        choice,
        randint,
        qrandint,
        randn,
        qrandn,
        loguniform,
        qloguniform,
        lograndint,
        qlograndint,
    )
from .tune import run, report, INCUMBENT_RESULT
from .sample import polynomial_expansion_set
from .sample import PolynomialExpansionSet, Categorical, Float
from .trial import Trial
