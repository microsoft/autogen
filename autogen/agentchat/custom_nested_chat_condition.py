import inspect
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Type, TypeVar, Union, get_type_hints


class CustomNestedChatCondition:
    def __init__(
        self,
        func: Callable[..., bool],
        state_params: Optional[dict[str, Any]] = None,
        name: Optional[str] = None,
        state_ttl_management: Literal["STATELESS", "STATE_KEPT_TILL_TRUE", "STATE_KEPT_TILL_FALSE"] = "STATELESS",
    ):
        """Class to hold a user-defined function signature and its parameters to act as conditions for nested conversations.

        Args:
            func (Callable): A callable function defined by the user.
            params (Dict): A dictionary of variables and names to act as the func's parameters.
            name (str): Optional string to name the custom condition. if none given, it will use the func.__name__ value
            state_ttl_management (str): The time-to-live for the state of the parameters needs to change or else the nested chat will forever be triggered.
                Possible values are "STATELESS", "PERSISTENT",
                (1) When "STATELESS", the state_params will be reset to an empty dict immediately after the trigger is checked, until then it will remain.
                The following 2 enum values are for scenarios where the trigger function needs to work with runtime state variables and external data that changes by itself. Should the developer need the runtime state data to work with that external data, this should provide that support
                (2) When "STATE_KEPT_TILL_TRUE", the state will be kept as-is until trigger function returns true, whereby it will be reset to None.
                (3) When "STATE_KEPT_TILL_FALSE", the state will be kept as-is until trigger function returns false, whereby it will be reset to None.

        """

        self.func = func  # Store the function itself
        self.state_params = state_params  # Store the parameter names as a dict
        if name:
            self._name = name
        else:
            self._name = func.__name__

        self.state_ttl_management = state_ttl_management

        # ennforce func is callable that returns bool
        if not callable(func):
            raise ValueError("Function must be callable type that returns bool.")
        sig = inspect.signature(func)
        type_hints = get_type_hints(self.func)
        if len(sig.parameters.items()) > 0:
            self.func_has_params = True
            # iterate over items in params and sig.parameters, ensure a 1:1 match between them based on key of params and name of sig.params and data type
            for param_name, param in sig.parameters.items():
                # Check if the parameter exists in the provided params
                if param_name not in self.state_params:
                    raise ValueError(
                        f"Parameter '{param_name}' is required by the function '{self.func.__name__}' but was not provided in params."
                    )
                # Ensure that type of func param is same as that of self.params counterpart
                expected_type = type_hints.get(param_name, Any)
                if not isinstance(self.state_params[param_name], expected_type) and expected_type is not Any:
                    raise TypeError(
                        f"Parameter '{param_name}' should be of type {expected_type}, but got {type(self.state_params[param_name])}"
                    )
        else:
            self.func_has_params = False

        try:
            # Check if func returns a boolean
            result = func(*[None] * len(sig.parameters))  # Call func with default None args for demo
            if not isinstance(result, bool):
                raise TypeError(f"The function '{func.__name__}' must return a boolean value.")
        except TypeError:
            pass  # Ignore if the function can't be called without arguments (further checking may be necessary)

    def call_function(self):
        """
        Call the function using the provided params, matching by parameter name.
        """
        # Call the function using **params to match by parameter name
        if self.func_has_params and self.state_params == None:
            raise TypeError(f"{self._name} is missing parameters")
            return False
        trigger_result = self.func(**self.state_params)

        # Handle state_params reset based on state_ttl_management
        if self.state_ttl_management == "STATELESS":
            # Reset state_params to an empty dict immediately after the trigger is checked
            self.state_params = {}
        elif self.state_ttl_management == "STATE_KEPT_TILL_TRUE":
            # Reset state_params to None if trigger function returns True
            if trigger_result is True:
                self.state_params = None
        elif self.state_ttl_management == "STATE_KEPT_TILL_FALSE":
            # Reset state_params to None if trigger function returns False
            if trigger_result is False:
                self.state_params = None
        else:
            # Default behavior: reset state_params to None
            self.state_params = None

        return trigger_result

    def update_state(self, new_state: dict):
        """
        Takes dictionary where key is variable name and value is new value. New value must be same type as original value or else error will be thrown. Unrecognised keys will be ignored
        """
        for new_param_name, new_param_value in new_state.items():
            if self.state_params.get(new_param_name, None) == None:
                # Warning of some kind
                continue
            if not isinstance(new_param_value, type(self.state_params["new_param_name"])):
                raise TypeError(
                    f"Parameter '{new_param_value}' has type of {type(new_param_value)}should be of type {type(self.state_params["new_param_name"])}"
                )
            else:
                self.state_params["new_param_name"] = new_param_value
