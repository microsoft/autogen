
try:
    from ray import __version__ as ray_version
    assert ray_version >= '1.0.0'
    from ray.tune import sample
    from ray.tune.suggest.variant_generator import generate_variants
except (ImportError, AssertionError):
    from . import sample
    from ..searcher.variant_generator import generate_variants
from typing import Dict, Optional, Any, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)


def define_by_run_func(
    trial, space: Dict, path: str = ""
) -> Optional[Dict[str, Any]]:
    """Define-by-run function to create the search space.

    Returns:
        A dict with constant values.
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
                    key, domain.lower,
                    domain.upper - int(bool(not quantize)),
                    step=quantize or 1, log=True)
            elif isinstance(sampler, sample.Uniform):
                # Upper bound should be inclusive for quantization and
                # exclusive otherwise
                trial.suggest_int(
                    key, domain.lower,
                    domain.upper - int(bool(not quantize)),
                    step=quantize or 1)
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


def unflatten_hierarchical(config: Dict, space: Dict) -> Tuple[Dict, Dict]:
    '''unflatten hierarchical config'''
    hier = {}
    subspace = {}
    for key, value in config.items():
        if '/' in key:
            key = key[key.rfind('/') + 1:]
        if ':' in key:
            pos = key.rfind(':')
            true_key = key[:pos]
            choice = int(key[pos + 1:])
            hier[true_key], subspace[true_key] = unflatten_hierarchical(
                value, space[true_key][choice])
        else:
            domain = space.get(key)
            if domain is not None:
                subspace[key] = domain
                if isinstance(domain, sample.Domain):
                    sampler = domain.sampler
                    if isinstance(sampler, sample.Quantized):
                        q = sampler.q
                        sampler = sampler.sampler
                        if isinstance(sampler, sample.LogUniform):
                            value = domain.cast(np.round(value / q) * q)
            hier[key] = value
    return hier, subspace


def add_cost_to_space(space: Dict, low_cost_point: Dict, choice_cost: Dict):
    """Update the space in place by adding low_cost_point and choice_cost

    Returns:
        A dict with constant values.
    """
    config = {}
    for key in space:
        domain = space[key]
        if not isinstance(domain, sample.Domain):
            if isinstance(domain, dict):
                low_cost = low_cost_point.get(key, {})
                choice_cost_list = choice_cost.get(key, {})
                const = add_cost_to_space(
                    domain, low_cost, choice_cost_list)
                if const:
                    config[key] = const
            else:
                config[key] = domain
            continue
        low_cost = low_cost_point.get(key)
        choice_cost_list = choice_cost.get(key)
        if callable(getattr(domain, 'get_sampler', None)):
            sampler = domain.get_sampler()
            if isinstance(sampler, sample.Quantized):
                sampler = sampler.get_sampler()
            domain.bounded = str(sampler) != 'Normal'
        if isinstance(domain, sample.Categorical):
            domain.const = []
            for i, cat in enumerate(domain.categories):
                if isinstance(cat, dict):
                    if isinstance(low_cost, list):
                        low_cost_dict = low_cost[i]
                    else:
                        low_cost_dict = {}
                    if choice_cost_list:
                        choice_cost_dict = choice_cost_list[i]
                    else:
                        choice_cost_dict = {}
                    domain.const.append(add_cost_to_space(
                        cat, low_cost_dict, choice_cost_dict))
                else:
                    domain.const.append(None)
            if choice_cost_list:
                if len(choice_cost_list) == len(domain.categories):
                    domain.choice_cost = choice_cost_list
                else:
                    domain.choice_cost = choice_cost_list[-1]
                # sort the choices by cost
                cost = np.array(domain.choice_cost)
                ind = np.argsort(cost)
                domain.categories = [domain.categories[i] for i in ind]
                domain.choice_cost = cost[ind]
                domain.const = [domain.const[i] for i in ind]
                domain.ordered = True
            elif all(isinstance(x, int) or isinstance(x, float)
                     for x in domain.categories):
                # sort the choices by value
                ind = np.argsort(domain.categories)
                domain.categories = [domain.categories[i] for i in ind]
                domain.ordered = True
            else:
                domain.ordered = False
            if low_cost and low_cost not in domain.categories:
                assert isinstance(low_cost, list), \
                    f"low cost {low_cost} not in domain {domain.categories}"
                if domain.ordered:
                    sorted_points = [low_cost[i] for i in ind]
                    for i, point in enumerate(sorted_points):
                        low_cost[i] = point
                if len(low_cost) > len(domain.categories):
                    if domain.ordered:
                        low_cost[-1] = int(np.where(ind == low_cost[-1])[0])
                    domain.low_cost_point = low_cost[-1]
                return
        if low_cost:
            domain.low_cost_point = low_cost
    return config


def normalize(
    config: Dict, space: Dict, reference_config: Dict,
    normalized_reference_config: Dict, recursive: bool = False,
):
    '''normalize config in space according to reference_config.
    normalize each dimension in config to [0,1].
    '''
    config_norm = {}
    for key in config:
        value = config[key]
        domain = space.get(key)
        if domain is None:  # e.g., prune_attr
            config_norm[key] = value
            continue
        if not callable(getattr(domain, 'get_sampler', None)):
            if recursive and isinstance(domain, dict):
                config_norm[key] = normalize(
                    value, domain, reference_config[key], {})
            else:
                config_norm[key] = value
            continue
        # domain: sample.Categorical/Integer/Float/Function
        if isinstance(domain, sample.Categorical):
            norm = None
            # value is either one category, or the low_cost_point list
            if value not in domain.categories:
                # nested, low_cost_point list
                if recursive:
                    norm = []
                    for i, cat in enumerate(domain.categories):
                        norm.append(normalize(
                            value[i], cat, reference_config[key][i], {}))
                if isinstance(value, list) and len(value) > len(
                   domain.categories):
                    # low_cost_point list
                    index = value[-1]
                    config[key] = value[index]
                    value = domain.categories[index]
                else:
                    continue
            # normalize categorical
            n = len(domain.categories)
            if domain.ordered:
                normalized = (domain.categories.index(value) + 0.5) / n
            elif key in normalized_reference_config:
                normalized = normalized_reference_config[
                    key] if value == reference_config[key] else (
                        normalized_reference_config[key] + 1 / n) % 1
            else:
                normalized = 0.5
            if norm:
                norm.append(normalized)
            else:
                norm = normalized
            config_norm[key] = norm
            continue
        # Uniform/LogUniform/Normal/Base
        sampler = domain.get_sampler()
        if isinstance(sampler, sample.Quantized):
            # sampler is sample.Quantized
            quantize = sampler.q
            sampler = sampler.get_sampler()
        else:
            quantize = None
        if str(sampler) == 'LogUniform':
            upper = domain.upper - (
                isinstance(domain, sample.Integer) & (quantize is None))
            config_norm[key] = np.log(value / domain.lower) / np.log(
                upper / domain.lower)
        elif str(sampler) == 'Uniform':
            upper = domain.upper - (
                isinstance(domain, sample.Integer) & (quantize is None))
            config_norm[key] = (value - domain.lower) / (upper - domain.lower)
        elif str(sampler) == 'Normal':
            # N(mean, sd) -> N(0,1)
            config_norm[key] = (value - sampler.mean) / sampler.sd
        else:
            # TODO? elif str(sampler) == 'Base': # sample.Function._CallSampler
            # e.g., {test: sample_from(lambda spec: randn(10, 2).sample() * 0.01)}
            config_norm[key] = value
    return config_norm


def denormalize(
    config: Dict, space: Dict, reference_config: Dict,
    normalized_reference_config: Dict, random_state
):
    config_denorm = {}
    for key, value in config.items():
        if key in space:
            # domain: sample.Categorical/Integer/Float/Function
            domain = space[key]
            if not callable(getattr(domain, 'get_sampler', None)):
                config_denorm[key] = value
            else:
                if isinstance(domain, sample.Categorical):
                    # denormalize categorical
                    n = len(domain.categories)
                    if domain.ordered:
                        config_denorm[key] = domain.categories[
                            min(n - 1, int(np.floor(value * n)))]
                    else:
                        assert key in normalized_reference_config
                        if np.floor(value * n) == np.floor(
                           normalized_reference_config[key] * n):
                            config_denorm[key] = reference_config[key]
                        else:  # ****random value each time!****
                            config_denorm[key] = random_state.choice(
                                [x for x in domain.categories
                                    if x != reference_config[key]])
                    continue
                # Uniform/LogUniform/Normal/Base
                sampler = domain.get_sampler()
                if isinstance(sampler, sample.Quantized):
                    # sampler is sample.Quantized
                    quantize = sampler.q
                    sampler = sampler.get_sampler()
                else:
                    quantize = None
                # Handle Log/Uniform
                if str(sampler) == 'LogUniform':
                    upper = domain.upper - (isinstance(domain, sample.Integer)
                                            & (quantize is None))
                    config_denorm[key] = (
                        upper / domain.lower) ** value * domain.lower
                elif str(sampler) == 'Uniform':
                    upper = domain.upper - (isinstance(domain, sample.Integer)
                                            & (quantize is None))
                    config_denorm[key] = value * (
                        upper - domain.lower) + domain.lower
                elif str(sampler) == 'Normal':
                    # denormalization for 'Normal'
                    config_denorm[key] = value * sampler.sd + sampler.mean
                else:
                    config_denorm[key] = value
                # Handle quantized
                if quantize is not None:
                    config_denorm[key] = np.round(
                        np.divide(config_denorm[key], quantize)) * quantize
                # Handle int (4.6 -> 5)
                if isinstance(domain, sample.Integer):
                    config_denorm[key] = int(round(config_denorm[key]))
        else:  # prune_attr
            config_denorm[key] = value
    return config_denorm


def indexof(domain: Dict, config: Dict) -> int:
    '''find the index of config in domain.categories
    '''
    index = config.get('_choice_')
    if index is not None:
        return index
    if config in domain.categories:
        return domain.categories.index(config)
    # print(config)
    for i, cat in enumerate(domain.categories):
        # print(cat)
        if not isinstance(cat, dict):
            continue
        # print(len(cat), len(config))
        if len(cat) != len(config):
            continue
        # print(cat.keys())
        if not set(cat.keys()).issubset(set(config.keys())):
            continue
        # print(domain.const[i])
        if all(config[key] == value for key, value in domain.const[i].items()):
            # assumption: the concatenation of constants is a unique identifier
            return i
    return None


def complete_config(
    partial_config: Dict, space: Dict, flow2, disturb: bool = False,
    lower: Optional[Dict] = None, upper: Optional[Dict] = None
) -> Tuple[Dict, Dict]:
    '''Complete partial config in space

    Returns:
        config, space
    '''
    config = partial_config.copy()
    normalized = normalize(config, space, config, {})
    if disturb:
        for key in normalized:
            domain = space.get(key)
            if getattr(domain, 'ordered', True) is False:
                # don't change unordered cat choice
                continue
            if not callable(getattr(domain, 'get_sampler', None)):
                continue
            if upper and lower:
                up, low = upper[key], lower[key]
                gauss_std = up - low or flow2.STEPSIZE
                # allowed bound
                up += flow2.STEPSIZE
                low -= flow2.STEPSIZE
            elif domain.bounded:
                up, low, gauss_std = 1, 0, 1.0
            else:
                up, low, gauss_std = np.Inf, -np.Inf, 1.0
            if domain.bounded:
                up = min(up, 1)
                low = max(low, 0)
            delta = flow2.rand_vector_gaussian(1, gauss_std)[0]
            normalized[key] = max(low, min(up, normalized[key] + delta))
    config = denormalize(normalized, space, config, normalized, flow2._random)
    for key, value in space.items():
        if key not in config:
            config[key] = value
    for _, generated in generate_variants({'config': config}):
        config = generated['config']
        break
    subspace = {}
    for key, domain in space.items():
        value = config[key]
        if isinstance(value, dict):
            if isinstance(domain, sample.Categorical):
                # nested space
                index = indexof(domain, value)
                # point = partial_config.get(key)
                # if isinstance(point, list):     # low cost point list
                #     point = point[index]
                # else:
                #     point = {}
                config[key], subspace[key] = complete_config(
                    value, domain.categories[index], flow2, disturb,
                    lower and lower[key][index], upper and upper[key][index]
                )
                assert '_choice_' not in subspace[key], \
                    "_choice_ is a reserved key for hierarchical search space"
                subspace[key]['_choice_'] = index
            else:
                config[key], subspace[key] = complete_config(
                    value, space[key], flow2, disturb,
                    lower and lower[key], upper and upper[key])
            continue
        subspace[key] = domain
    return config, subspace
