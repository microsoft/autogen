try:
    from ray.tune import (uniform, quniform, choice, randint, qrandint, randn,
                          qrandn, loguniform, qloguniform)
except ImportError:
    from .sample import (uniform, quniform, choice, randint, qrandint, randn,
                         qrandn, loguniform, qloguniform)
from .tune import run, report
