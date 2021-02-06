try:
    from ray.tune import (uniform, quniform, choice, randint, qrandint, randn,
 qrandn, loguniform, qloguniform)
except:
    from .sample import (uniform, quniform, choice, randint, qrandint, randn,
 qrandn, loguniform, qloguniform)
from .tune import run, report