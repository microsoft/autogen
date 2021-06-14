from collections import OrderedDict
from ray.tune.schedulers import ASHAScheduler, HyperBandScheduler

SCHEDULER_MAPPING = OrderedDict(
    [
        ("None", None),
        ("asha", ASHAScheduler),
        ("hb", HyperBandScheduler),
    ]
)


class AutoScheduler:
    """
    This is a class for getting the scheduler based on the scheduler name
    (a string variable) instantiated as one of the schedulers of the library when
    created with the `~flaml.nlp.hpo.AutoScheduler.from_scheduler_name` method.

    This class cannot be instantiated directly using ``__init__()`` (throws an error).
    """

    def __init__(self):
        raise EnvironmentError(
            "AutoScheduler is designed to be instantiated "
            "using the `AutoScheduler.from_scheduler_name(cls, scheduler_name, **kwargs)` methods."
        )

    @classmethod
    def from_scheduler_name(cls, scheduler_name, **kwargs):
        """
        Instantiate one of the schedulers using the scheduler names

        Args:
            scheduler_name:
                A string variable for the scheduler name

        Example:
            >>> AutoScheduler.from_scheduler_name("asha")
        """
        if scheduler_name in SCHEDULER_MAPPING.keys():
            if SCHEDULER_MAPPING[scheduler_name] is None:
                return None
            return SCHEDULER_MAPPING[scheduler_name](**kwargs)
        raise ValueError(
            "Unrecognized scheduler {} for this kind of AutoScheduler: {}.\n"
            "Scheduler name should be one of {}.".format(
                scheduler_name, cls.__name__, ", ".join(SCHEDULER_MAPPING.keys())
            )
        )
