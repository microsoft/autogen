'''
Copyright 2020 The Ray Authors.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

This source file is adapted here because ray does not fully support Windows.

Copyright (c) Microsoft Corporation.
'''
import copy
import logging
from collections.abc import Mapping
from typing import Any, Dict, Generator, List, Optional, Tuple

import numpy
import random

from ..tune.sample import Categorical, Domain, Function

logger = logging.getLogger(__name__)


def flatten_dict(dt, delimiter="/", prevent_delimiter=False):
    dt = copy.deepcopy(dt)
    if prevent_delimiter and any(delimiter in key for key in dt):
        # Raise if delimiter is any of the keys
        raise ValueError(
            "Found delimiter `{}` in key when trying to flatten array."
            "Please avoid using the delimiter in your specification.")
    while any(isinstance(v, dict) for v in dt.values()):
        remove = []
        add = {}
        for key, value in dt.items():
            if isinstance(value, dict):
                for subkey, v in value.items():
                    if prevent_delimiter and delimiter in subkey:
                        # Raise  if delimiter is in any of the subkeys
                        raise ValueError(
                            "Found delimiter `{}` in key when trying to "
                            "flatten array. Please avoid using the delimiter "
                            "in your specification.")
                    add[delimiter.join([key, str(subkey)])] = v
                remove.append(key)
        dt.update(add)
        for k in remove:
            del dt[k]
    return dt


def unflatten_dict(dt, delimiter="/"):
    """Unflatten dict. Does not support unflattening lists."""
    dict_type = type(dt)
    out = dict_type()
    for key, val in dt.items():
        path = key.split(delimiter)
        item = out
        for k in path[:-1]:
            item = item.setdefault(k, dict_type())
        item[path[-1]] = val
    return out


class TuneError(Exception):
    """General error class raised by ray.tune."""
    pass


def generate_variants(
        unresolved_spec: Dict) -> Generator[Tuple[Dict, Dict], None, None]:
    """Generates variants from a spec (dict) with unresolved values.
    There are two types of unresolved values:
        Grid search: These define a grid search over values. For example, the
        following grid search values in a spec will produce six distinct
        variants in combination:
            "activation": grid_search(["relu", "tanh"])
            "learning_rate": grid_search([1e-3, 1e-4, 1e-5])
        Lambda functions: These are evaluated to produce a concrete value, and
        can express dependencies or conditional distributions between values.
        They can also be used to express random search (e.g., by calling
        into the `random` or `np` module).
            "cpu": lambda spec: spec.config.num_workers
            "batch_size": lambda spec: random.uniform(1, 1000)
    Finally, to support defining specs in plain JSON / YAML, grid search
    and lambda functions can also be defined alternatively as follows:
        "activation": {"grid_search": ["relu", "tanh"]}
        "cpu": {"eval": "spec.config.num_workers"}
    Use `format_vars` to format the returned dict of hyperparameters.
    Yields:
        (Dict of resolved variables, Spec object)
    """
    for resolved_vars, spec in _generate_variants(unresolved_spec):
        assert not _unresolved_values(spec)
        yield resolved_vars, spec


def grid_search(values: List) -> Dict[str, List]:
    """Convenience method for specifying grid search over a value.
    Arguments:
        values: An iterable whose parameters will be gridded.
    """

    return {"grid_search": values}


_STANDARD_IMPORTS = {
    "random": random,
    "np": numpy,
}

_MAX_RESOLUTION_PASSES = 20


def resolve_nested_dict(nested_dict: Dict) -> Dict[Tuple, Any]:
    """Flattens a nested dict by joining keys into tuple of paths.
    Can then be passed into `format_vars`.
    """
    res = {}
    for k, v in nested_dict.items():
        if isinstance(v, dict):
            for k_, v_ in resolve_nested_dict(v).items():
                res[(k, ) + k_] = v_
        else:
            res[(k, )] = v
    return res


def format_vars(resolved_vars: Dict) -> str:
    """Formats the resolved variable dict into a single string."""
    out = []
    for path, value in sorted(resolved_vars.items()):
        if path[0] in ["run", "env", "resources_per_trial"]:
            continue  # TrialRunner already has these in the experiment_tag
        pieces = []
        last_string = True
        for k in path[::-1]:
            if isinstance(k, int):
                pieces.append(str(k))
            elif last_string:
                last_string = False
                pieces.append(k)
        pieces.reverse()
        out.append(_clean_value("_".join(pieces)) + "=" + _clean_value(value))
    return ",".join(out)


def flatten_resolved_vars(resolved_vars: Dict) -> Dict:
    """Formats the resolved variable dict into a mapping of (str -> value)."""
    flattened_resolved_vars_dict = {}
    for pieces, value in resolved_vars.items():
        if pieces[0] == "config":
            pieces = pieces[1:]
        pieces = [str(piece) for piece in pieces]
        flattened_resolved_vars_dict["/".join(pieces)] = value
    return flattened_resolved_vars_dict


def _clean_value(value: Any) -> str:
    if isinstance(value, float):
        return "{:.5}".format(value)
    else:
        return str(value).replace("/", "_")


def parse_spec_vars(spec: Dict) -> Tuple[List[Tuple[Tuple, Any]], List[Tuple[
        Tuple, Any]], List[Tuple[Tuple, Any]]]:
    resolved, unresolved = _split_resolved_unresolved_values(spec)
    resolved_vars = list(resolved.items())

    if not unresolved:
        return resolved_vars, [], []

    grid_vars = []
    domain_vars = []
    for path, value in unresolved.items():
        if value.is_grid():
            grid_vars.append((path, value))
        else:
            domain_vars.append((path, value))
    grid_vars.sort()

    return resolved_vars, domain_vars, grid_vars


def count_variants(spec: Dict, presets: Optional[List[Dict]] = None) -> int:
    # Helper function: Deep update dictionary
    def deep_update(d, u):
        for k, v in u.items():
            if isinstance(v, Mapping):
                d[k] = deep_update(d.get(k, {}), v)
            else:
                d[k] = v
        return d

    # Count samples for a specific spec
    def spec_samples(spec, num_samples=1):
        _, domain_vars, grid_vars = parse_spec_vars(spec)
        grid_count = 1
        for path, domain in grid_vars:
            grid_count *= len(domain.categories)
        return num_samples * grid_count

    total_samples = 0
    total_num_samples = spec.get("num_samples", 1)
    # For each preset, overwrite the spec and count the samples generated
    # for this preset
    for preset in presets:
        preset_spec = copy.deepcopy(spec)
        deep_update(preset_spec["config"], preset)
        total_samples += spec_samples(preset_spec, 1)
        total_num_samples -= 1

    # Add the remaining samples
    if total_num_samples > 0:
        total_samples += spec_samples(spec, total_num_samples)
    return total_samples


def _generate_variants(spec: Dict) -> Tuple[Dict, Dict]:
    spec = copy.deepcopy(spec)
    _, domain_vars, grid_vars = parse_spec_vars(spec)

    if not domain_vars and not grid_vars:
        yield {}, spec
        return

    grid_search = _grid_search_generator(spec, grid_vars)
    for resolved_spec in grid_search:
        resolved_vars = _resolve_domain_vars(resolved_spec, domain_vars)
        for resolved, spec in _generate_variants(resolved_spec):
            for path, value in grid_vars:
                resolved_vars[path] = _get_value(spec, path)
            for k, v in resolved.items():
                if (k in resolved_vars and v != resolved_vars[k]
                        and _is_resolved(resolved_vars[k])):
                    raise ValueError(
                        "The variable `{}` could not be unambiguously "
                        "resolved to a single value. Consider simplifying "
                        "your configuration.".format(k))
                resolved_vars[k] = v
            yield resolved_vars, spec


def get_preset_variants(spec: Dict, config: Dict):
    """Get variants according to a spec, initialized with a config.
    Variables from the spec are overwritten by the variables in the config.
    Thus, we may end up with less sampled parameters.
    This function also checks if values used to overwrite search space
    parameters are valid, and logs a warning if not.
    """
    spec = copy.deepcopy(spec)

    resolved, _, _ = parse_spec_vars(config)

    for path, val in resolved:
        try:
            domain = _get_value(spec["config"], path)
            if isinstance(domain, dict):
                if "grid_search" in domain:
                    domain = Categorical(domain["grid_search"])
                else:
                    # If users want to overwrite an entire subdict,
                    # let them do it.
                    domain = None
        except IndexError as exc:
            raise ValueError(
                f"Pre-set config key `{'/'.join(path)}` does not correspond "
                f"to a valid key in the search space definition. Please add "
                f"this path to the `config` variable passed to `tune.run()`."
            ) from exc

        if domain and not domain.is_valid(val):
            logger.warning(
                f"Pre-set value `{val}` is not within valid values of "
                f"parameter `{'/'.join(path)}`: {domain.domain_str}")
        assign_value(spec["config"], path, val)

    return _generate_variants(spec)


def assign_value(spec: Dict, path: Tuple, value: Any):
    for k in path[:-1]:
        spec = spec[k]
    spec[path[-1]] = value


def _get_value(spec: Dict, path: Tuple) -> Any:
    for k in path:
        spec = spec[k]
    return spec


def _resolve_domain_vars(spec: Dict,
                         domain_vars: List[Tuple[Tuple, Domain]]) -> Dict:
    resolved = {}
    error = True
    num_passes = 0
    while error and num_passes < _MAX_RESOLUTION_PASSES:
        num_passes += 1
        error = False
        for path, domain in domain_vars:
            if path in resolved:
                continue
            try:
                value = domain.sample(_UnresolvedAccessGuard(spec))
            except RecursiveDependencyError as e:
                error = e
            except Exception:
                raise ValueError(
                    "Failed to evaluate expression: {}: {}".format(
                        path, domain))
            else:
                assign_value(spec, path, value)
                resolved[path] = value
    if error:
        raise error
    return resolved


def _grid_search_generator(unresolved_spec: Dict,
                           grid_vars: List) -> Generator[Dict, None, None]:
    value_indices = [0] * len(grid_vars)

    def increment(i):
        value_indices[i] += 1
        if value_indices[i] >= len(grid_vars[i][1]):
            value_indices[i] = 0
            if i + 1 < len(value_indices):
                return increment(i + 1)
            else:
                return True
        return False

    if not grid_vars:
        yield unresolved_spec
        return

    while value_indices[-1] < len(grid_vars[-1][1]):
        spec = copy.deepcopy(unresolved_spec)
        for i, (path, values) in enumerate(grid_vars):
            assign_value(spec, path, values[value_indices[i]])
        yield spec
        if grid_vars:
            done = increment(0)
            if done:
                break


def _is_resolved(v) -> bool:
    resolved, _ = _try_resolve(v)
    return resolved


def _try_resolve(v) -> Tuple[bool, Any]:
    if isinstance(v, Domain):
        # Domain to sample from
        return False, v
    elif isinstance(v, dict) and len(v) == 1 and "eval" in v:
        # Lambda function in eval syntax
        return False, Function(
            lambda spec: eval(v["eval"], _STANDARD_IMPORTS, {"spec": spec}))
    elif isinstance(v, dict) and len(v) == 1 and "grid_search" in v:
        # Grid search values
        grid_values = v["grid_search"]
        if not isinstance(grid_values, list):
            raise TuneError(
                "Grid search expected list of values, got: {}".format(
                    grid_values))
        return False, Categorical(grid_values).grid()
    return True, v


def _split_resolved_unresolved_values(
        spec: Dict) -> Tuple[Dict[Tuple, Any], Dict[Tuple, Any]]:
    resolved_vars = {}
    unresolved_vars = {}
    for k, v in spec.items():
        resolved, v = _try_resolve(v)
        if not resolved:
            unresolved_vars[(k, )] = v
        elif isinstance(v, dict):
            # Recurse into a dict
            _resolved_children, _unresolved_children = \
                _split_resolved_unresolved_values(v)
            for (path, value) in _resolved_children.items():
                resolved_vars[(k, ) + path] = value
            for (path, value) in _unresolved_children.items():
                unresolved_vars[(k, ) + path] = value
        elif isinstance(v, list):
            # Recurse into a list
            for i, elem in enumerate(v):
                _resolved_children, _unresolved_children = \
                    _split_resolved_unresolved_values({i: elem})
                for (path, value) in _resolved_children.items():
                    resolved_vars[(k, ) + path] = value
                for (path, value) in _unresolved_children.items():
                    unresolved_vars[(k, ) + path] = value
        else:
            resolved_vars[(k, )] = v
    return resolved_vars, unresolved_vars


def _unresolved_values(spec: Dict) -> Dict[Tuple, Any]:
    return _split_resolved_unresolved_values(spec)[1]


def has_unresolved_values(spec: Dict) -> bool:
    return True if _unresolved_values(spec) else False


class _UnresolvedAccessGuard(dict):
    def __init__(self, *args, **kwds):
        super(_UnresolvedAccessGuard, self).__init__(*args, **kwds)
        self.__dict__ = self

    def __getattribute__(self, item):
        value = dict.__getattribute__(self, item)
        if not _is_resolved(value):
            raise RecursiveDependencyError(
                "`{}` recursively depends on {}".format(item, value))
        elif isinstance(value, dict):
            return _UnresolvedAccessGuard(value)
        else:
            return value


class RecursiveDependencyError(Exception):
    def __init__(self, msg: str):
        Exception.__init__(self, msg)
