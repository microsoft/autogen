"""Utilities for client classes"""

import warnings
from typing import Any, Dict, List, Optional, Tuple


def validate_parameter(
    params: Dict[str, Any],
    param_name: str,
    allowed_types: Tuple,
    allow_None: bool,
    default_value: Any,
    numerical_bound: Tuple,
    allowed_values: list,
) -> Any:
    """Validates a given config parameter, checking its type, values, and setting defaults"""

    if allowed_values is not None and not isinstance(allowed_values, list):
        raise TypeError(f"allowed_values should be a list or None, got {type(allowed_values).__name__}")

    param_value = params.get(param_name, default_value)
    warning = ""

    if param_value is None and allow_None:
        pass
    elif param_value is None and not allow_None:
        warning = "cannot be None"
    elif not isinstance(param_value, allowed_types):
        # Check types and list possible types if invalid
        if isinstance(allowed_types, tuple):
            formatted_types = "(" + ", ".join(f"{t.__name__}" for t in allowed_types) + ")"
        else:
            formatted_types = f"{allowed_types.__name__}"
        warning = f"must be of type {formatted_types}{' or None' if allow_None else ''}"
    elif numerical_bound:
        # Check the value fits in possible bounds
        lower_bound, upper_bound = numerical_bound
        if (lower_bound is not None and param_value < lower_bound) or (
            upper_bound is not None and param_value > upper_bound
        ):
            warning = f"has numerical bounds, {'>= ' + str(lower_bound) if lower_bound is not None else ''}{' and ' if lower_bound is not None and upper_bound is not None else ''}{'<= ' + str(upper_bound) if upper_bound is not None else ''}{', or can be None' if allow_None else ''}"
    elif allowed_values:
        # Check if the value matches any allowed values
        if not (allow_None and param_value is None):
            if param_value not in allowed_values:
                warning = f"must be one of these values [{allowed_values}]{', or can be None' if allow_None else ''}"

    # If we failed any checks, warn and set to default value
    if warning:
        warnings.warn(
            f"Config error - {param_name} {warning}, defaulting to {default_value}.",
            UserWarning,
        )
        param_value = default_value

    return param_value
