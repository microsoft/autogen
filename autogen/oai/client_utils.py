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
    """
    Validates a given config parameter, checking its type, values, and setting defaults
    Parameters:
        params (Dict[str, Any]): Dictionary containing parameters to validate.
        param_name (str): The name of the parameter to validate.
        allowed_types (Tuple): Tuple of acceptable types for the parameter.
        allow_None (bool): Whether the parameter can be `None`.
        default_value (Any): The default value to use if the parameter is invalid or missing.
        numerical_bound (Optional[Tuple[Optional[float], Optional[float]]]):
            A tuple specifying the lower and upper bounds for numerical parameters.
            Each bound can be `None` if not applicable.
        allowed_values (Optional[List[Any]]): A list of acceptable values for the parameter.
            Can be `None` if no specific values are required.

    Returns:
        Any: The validated parameter value or the default value if validation fails.

    Raises:
        TypeError: If `allowed_values` is provided but is not a list.

    Example Usage:
    ```python
        # Validating a numerical parameter within specific bounds
        params = {"temperature": 0.5, "safety_model": "Meta-Llama/Llama-Guard-7b"}
        temperature = validate_parameter(params, "temperature", (int, float), True, 0.7, (0, 1), None)
        # Result: 0.5

        # Validating a parameter that can be one of a list of allowed values
        model = validate_parameter(
        params, "safety_model", str, True, None, None, ["Meta-Llama/Llama-Guard-7b", "Meta-Llama/Llama-Guard-13b"]
        )
        # If "safety_model" is missing or invalid in params, defaults to "default"
    ```
    """

    if allowed_values is not None and not isinstance(allowed_values, list):
        raise TypeError(f"allowed_values should be a list or None, got {type(allowed_values).__name__}")

    param_value = params.get(param_name, default_value)
    warning = ""

    if param_value is None and allow_None:
        pass
    elif param_value is None:
        if not allow_None:
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
            warning = "has numerical bounds"
            if lower_bound is not None:
                warning += f", >= {str(lower_bound)}"
            if upper_bound is not None:
                if lower_bound is not None:
                    warning += " and"
                warning += f" <= {str(upper_bound)}"
            if allow_None:
                warning += ", or can be None"

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


def should_hide_tools(messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], hide_tools_param: str) -> bool:
    """
    Determines if tools should be hidden. This function is used to hide tools when they have been run, minimising the chance of the LLM choosing them when they shouldn't.
    Parameters:
        messages (List[Dict[str, Any]]): List of messages
        tools (List[Dict[str, Any]]): List of tools
        hide_tools_param (str): "hide_tools" parameter value. Can be "if_all_run" (hide tools if all tools have been run), "if_any_run" (hide tools if any of the tools have been run), "never" (never hide tools). Default is "never".

    Returns:
        bool: Indicates whether the tools should be excluded from the response create request

    Example Usage:
    ```python
        # Validating a numerical parameter within specific bounds
        messages = params.get("messages", [])
        tools = params.get("tools", None)
        hide_tools = should_hide_tools(messages, tools, params["hide_tools"])
    """

    if hide_tools_param == "never" or tools is None or len(tools) == 0:
        return False
    elif hide_tools_param == "if_any_run":
        # Return True if any tool_call_id exists, indicating a tool call has been executed. False otherwise.
        return any(["tool_call_id" in dictionary for dictionary in messages])
    elif hide_tools_param == "if_all_run":
        # Return True if all tools have been executed at least once. False otherwise.

        # Get the list of tool names
        check_tool_names = [item["function"]["name"] for item in tools]

        # Prepare a list of tool call ids and related function names
        tool_call_ids = {}

        # Loop through the messages and check if the tools have been run, removing them as we go
        for message in messages:
            if "tool_calls" in message:
                # Register the tool id and the name
                tool_call_ids[message["tool_calls"][0]["id"]] = message["tool_calls"][0]["function"]["name"]
            elif "tool_call_id" in message:
                # Tool called, get the name of the function based on the id
                tool_name_called = tool_call_ids[message["tool_call_id"]]

                # If we had not yet called the tool, check and remove it to indicate we have
                if tool_name_called in check_tool_names:
                    check_tool_names.remove(tool_name_called)

        # Return True if all tools have been called at least once (accounted for)
        return len(check_tool_names) == 0
    else:
        raise TypeError(
            f"hide_tools_param is not a valid value ['if_all_run','if_any_run','never'], got '{hide_tools_param}'"
        )
