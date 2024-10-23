from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Type, TypeVar, Union, get_type_hints
import inspect
class CustomNestedChatCondition():
    def __init__(self,
                 func: Callable[..., bool],
                 state_params: Optional[dict[str, Any]]=None,
                 name: Optional[str] = None):
        """Class to hold a user-defined function signature and its parameters to act as conditions for nested conversations.
        
        Args:
            func: A callable function defined by the user.
            params: A dictionary of variables and names to act as the func's parameters.
        """
        # ennforce func is callable that returns bool
        if not callable(func):
            raise ValueError("Function must be callable type that returns bool.")
        sig = inspect.signature(func)
        try:
            # Check if func can be called without arguments, and test if it returns a boolean
            result = func(*[None] * len(sig.parameters))  # Call func with default None args for demo
            if not isinstance(result, bool):
                raise TypeError(f"The function '{func.__name__}' must return a boolean value.")
        except TypeError:
            pass  # Ignore if the function can't be called without arguments (further checking may be necessary)
        
        self.func = func           # Store the function itself
        self.state_params = state_params       # Store the parameter names as a list
        if name:
            self._name = name
        else:
            self._name = func.__name__
        
        # iterate over items in params and sig.parameters, ensure a 1:1 match between them based on key of params and name of sig.params and data type
        type_hints = get_type_hints(self.func)
        for param_name, param in sig.parameters.items():
            # Check if the parameter exists in the provided params
            if param_name not in self.state_params:
                raise ValueError(f"Parameter '{param_name}' is required by the function '{self.func.__name__}' but was not provided in params.")
            # Ensure that type of func param is same as that of self.params counterpart
            expected_type = type_hints.get(param_name, Any)
            if not isinstance(self.state_params[param_name], expected_type) and expected_type is not Any:
                raise TypeError(f"Parameter '{param_name}' should be of type {expected_type}, but got {type(self.state_params[param_name])}")
            
    def call_function(self):
        """
        Call the function using the provided params, matching by parameter name.
        """
        # Call the function using **params to match by parameter name
        return self.func(**self.state_params)
            
    def update_state(self, new_state: dict):
        """
        Takes dictionary where key is variable name and value is new value. New value must be same type as original value or else error will be thrown. Unrecognised keys will be ignored
        """
        for new_param_name, new_param_value in new_state.items():
            if self.state_params.get(new_param_name, None) == None:
                # Warning of some kind
                continue
            if not isinstance(new_param_value, type(self.state_params["new_param_name"])):
                raise TypeError(f"Parameter '{new_param_value}' has type of {type(new_param_value)}should be of type {type(self.state_params["new_param_name"])}")
            else:
                self.state_params["new_param_name"] = new_param_value



        