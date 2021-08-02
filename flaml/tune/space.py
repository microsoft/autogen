
try:
    from ray.tune import sample
except ImportError:
    from . import sample
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


def define_by_run_func(
    trial, space: Dict, path: str = ""
) -> Optional[Dict[str, Any]]:
    """Define-by-run function to create the search space.

    Returns:
        None or a dict with constant values.
    """
    config = {}
    for key, domain in space.items():
        if path:
            key = path + '/' + key
        if not isinstance(domain, sample.Domain):
            config[key] = domain
            continue
        sampler = domain.get_sampler()
        quantize = None
        if isinstance(sampler, sample.Quantized):
            quantize = sampler.q
            sampler = sampler.sampler
            if isinstance(sampler, sample.LogUniform):
                logger.warning(
                    "Optuna does not handle quantization in loguniform "
                    "sampling. The parameter will be passed but it will "
                    "probably be ignored.")
        if isinstance(domain, sample.Float):
            if isinstance(sampler, sample.LogUniform):
                if quantize:
                    logger.warning(
                        "Optuna does not support both quantization and "
                        "sampling from LogUniform. Dropped quantization.")
                trial.suggest_float(
                    key, domain.lower, domain.upper, log=True)
            elif isinstance(sampler, sample.Uniform):
                if quantize:
                    trial.suggest_float(
                        key, domain.lower, domain.upper, step=quantize)
                trial.suggest_float(key, domain.lower, domain.upper)
        elif isinstance(domain, sample.Integer):
            if isinstance(sampler, sample.LogUniform):
                trial.suggest_int(
                    key, domain.lower, domain.upper, step=quantize or 1, log=True)
            elif isinstance(sampler, sample.Uniform):
                # Upper bound should be inclusive for quantization and
                # exclusive otherwise
                trial.suggest_int(
                    key, domain.lower, domain.upper, step=quantize or 1)
        elif isinstance(domain, sample.Categorical):
            if isinstance(sampler, sample.Uniform):
                if not hasattr(domain, 'choices'):
                    domain.choices = list(range(len(domain.categories)))
                choices = domain.choices
                # This choice needs to be removed from the final config
                index = trial.suggest_categorical(key + '_choice_', choices)
                choice = domain.categories[index]
                if isinstance(choice, dict):
                    key += f":{index}"
                    # the suffix needs to be removed from the final config
                    config[key] = define_by_run_func(trial, choice, key)
        else:
            raise ValueError(
                "Optuna search does not support parameters of type "
                "`{}` with samplers of type `{}`".format(
                    type(domain).__name__,
                    type(domain.sampler).__name__))
    # Return all constants in a dictionary.
    return config
